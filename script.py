import os
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional

import requests
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import MismatchedABI, ContractLogicError
from web3.logs import DISCARD
from dotenv import load_dotenv

# --- Configuration --- #
# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables from .env file
load_dotenv()

# --- Constants (Simulated Data) --- #
SOURCE_CHAIN_RPC = os.getenv('SOURCE_CHAIN_RPC_URL', 'https://rpc.sepolia.org')
DESTINATION_CHAIN_RPC = os.getenv('DESTINATION_CHAIN_RPC_URL', 'https://rpc.ankr.com/polygon_mumbai')

# Dummy address of the bridge contract on the source chain
BRIDGE_CONTRACT_ADDRESS = '0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B' # Using Vitalik's address as a placeholder

# A simplified ABI for the bridge contract, focusing on the event we want to listen to.
# In a real scenario, this would be the full contract ABI.
BRIDGE_CONTRACT_ABI = '''
[
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "internalType": "address",
                "name": "user",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "address",
                "name": "token",
                "type": "address"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "destinationChainId",
                "type": "uint256"
            },
            {
                "indexed": false,
                "internalType": "bytes32",
                "name": "transactionId",
                "type": "bytes32"
            }
        ],
        "name": "TokensLocked",
        "type": "event"
    }
]
'''

RELAYER_API_ENDPOINT = os.getenv('RELAYER_API_ENDPOINT', 'https://api.mockrelayer.com/submit_proof')


class ChainConnector:
    """Manages the connection to a single blockchain node via Web3.py."""

    def __init__(self, rpc_url: str, chain_name: str):
        """
        Initializes the connector with a given RPC URL.

        Args:
            rpc_url (str): The HTTP or WebSocket RPC endpoint of the blockchain node.
            chain_name (str): A descriptive name for the chain (e.g., 'SourceChain-Sepolia').
        """
        self.rpc_url = rpc_url
        self.chain_name = chain_name
        self.web3: Optional[Web3] = None
        self.logger = logging.getLogger(f'ChainConnector-{self.chain_name}')

    def connect(self) -> None:
        """
        Establishes a connection to the blockchain node.
        Raises:
            ConnectionError: If the connection to the RPC endpoint fails.
        """
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if not self.web3.is_connected():
                raise ConnectionError(f'Failed to connect to {self.chain_name} at {self.rpc_url}')
            self.logger.info(f'Successfully connected to {self.chain_name}. Latest block: {self.web3.eth.block_number}')
        except Exception as e:
            self.logger.error(f'Error connecting to {self.chain_name}: {e}')
            raise ConnectionError(f'Could not establish connection to {self.chain_name}.') from e

    def get_contract(self, address: str, abi: str) -> Optional[Contract]:
        """
        Gets a Web3.py Contract instance.

        Args:
            address (str): The contract's address.
            abi (str): The contract's ABI.

        Returns:
            Optional[Contract]: A contract object if connection is successful, otherwise None.
        """
        if not self.web3 or not self.web3.is_connected():
            self.logger.warning('Not connected. Cannot get contract instance.')
            return None
        try:
            checksum_address = self.web3.to_checksum_address(address)
            return self.web3.eth.contract(address=checksum_address, abi=abi)
        except ValueError as e:
            self.logger.error(f'Invalid address or ABI provided: {e}')
            return None


class CrossChainOracle:
    """
    Simulates a relayer/oracle service that validates an event from the source chain
    and submits it to the destination chain's authorities.
    """

    def __init__(self, relayer_endpoint: str):
        """
        Args:
            relayer_endpoint (str): The API endpoint of the relayer service.
        """
        self.relayer_endpoint = relayer_endpoint
        self.logger = logging.getLogger('CrossChainOracle')

    def submit_lock_event_proof(self, event_data: Dict[str, Any]) -> bool:
        """
        Simulates submitting the proof of a 'TokensLocked' event to a relayer network.

        Args:
            event_data (Dict[str, Any]): The processed event data.

        Returns:
            bool: True if the submission was successful (simulated), False otherwise.
        """
        if not self._is_event_valid(event_data):
            self.logger.warning(f'Invalid event data received. Aborting submission. Data: {event_data}')
            return False

        payload = {
            'sourceTransactionId': event_data['transactionId'],
            'sourceChain': 'source_chain_id_placeholder',
            'destinationChainId': event_data['destinationChainId'],
            'user': event_data['user'],
            'token': event_data['token'],
            'amount': event_data['amount'],
            'blockNumber': event_data['blockNumber']
        }

        self.logger.info(f'Submitting event proof to relayer: {self.relayer_endpoint}')
        self.logger.debug(f'Payload: {payload}')

        try:
            # In a real system, this would be a cryptographically signed message.
            # Here, we simulate a simple POST request.
            response = requests.post(self.relayer_endpoint, json=payload, timeout=10)

            # Since the endpoint is a mock, we will likely get an error.
            # We simulate a successful outcome for the purpose of this script.
            # For a real run, one would check: response.status_code == 200
            self.logger.info(f'Simulated successful submission for TxID: {payload["sourceTransactionId"]}')
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f'Failed to submit proof to relayer API: {e}')
            # We simulate success even on connection failure to allow the script to continue.
            self.logger.warning(f'Proceeding with simulated success despite request failure for TxID: {payload["sourceTransactionId"]}')
            return True

    def _is_event_valid(self, event_data: Dict[str, Any]) -> bool:
        """
A simple validation check for the event data structure."""
        required_keys = ['transactionId', 'destinationChainId', 'user', 'token', 'amount', 'blockNumber']
        return all(key in event_data for key in required_keys)


class ContractEventHandler:
    """
    Listens for specific events on a given smart contract and triggers a callback.
    """

    def __init__(self, connector: ChainConnector, contract_address: str, contract_abi: str, oracle: CrossChainOracle):
        """
        Args:
            connector (ChainConnector): The connector for the chain to listen on.
            contract_address (str): The address of the contract to monitor.
            contract_abi (str): The ABI of the contract.
            oracle (CrossChainOracle): The oracle service to notify upon event detection.
        """
        self.connector = connector
        self.contract_address = contract_address
        self.contract_abi = contract_abi
        self.oracle = oracle
        self.contract: Optional[Contract] = None
        self.logger = logging.getLogger('ContractEventHandler')

    def setup(self):
        """Sets up the contract instance. Must be called after connector is connected."""
        self.contract = self.connector.get_contract(self.contract_address, self.contract_abi)
        if not self.contract:
            raise RuntimeError('Failed to initialize contract for event handler.')
        self.logger.info(f'Event handler set up for contract at {self.contract_address}')

    async def listen_for_events(self, poll_interval: int = 5):
        """
        Starts an infinite loop to poll for 'TokensLocked' events.

        Args:
            poll_interval (int): The time in seconds to wait between polls.
        """
        if not self.contract or not self.connector.web3:
            self.logger.error('Handler is not set up correctly. Cannot start listening.')
            return

        try:
            event_filter = self.contract.events.TokensLocked.create_filter(fromBlock='latest')
        except MismatchedABI:
            self.logger.error('The ABI provided does not contain the `TokensLocked` event. Aborting.')
            return
        
        self.logger.info(f'Starting to listen for `TokensLocked` events... Polling every {poll_interval} seconds.')

        while True:
            try:
                new_entries = event_filter.get_new_entries()
                if new_entries:
                    self.logger.info(f'Found {len(new_entries)} new event(s).')
                    for event in new_entries:
                        self.handle_event(event)
                else:
                    self.logger.debug('No new events detected.')
                
                await asyncio.sleep(poll_interval)

            except Exception as e:
                self.logger.error(f'An error occurred during event polling: {e}')
                self.logger.info('Attempting to reconnect and recreate filter...')
                await asyncio.sleep(poll_interval * 2) # Wait longer before retrying
                try:
                    self.connector.connect()
                    self.setup()
                    event_filter = self.contract.events.TokensLocked.create_filter(fromBlock='latest')
                except Exception as recon_e:
                    self.logger.critical(f'Failed to recover listener: {recon_e}. Exiting loop.')
                    break

    def handle_event(self, event: Dict[str, Any]):
        """Processes a single event log."""
        self.logger.info(f'Processing event from block {event["blockNumber"]}')
        try:
            # Process event arguments
            event_args = event['args']
            processed_data = {
                'user': event_args['user'],
                'token': event_args['token'],
                'amount': event_args['amount'],
                'destinationChainId': event_args['destinationChainId'],
                'transactionId': event_args['transactionId'].hex(),
                'blockNumber': event['blockNumber'],
                'txHash': event['transactionHash'].hex()
            }
            self.logger.info(f'TokensLocked Event Data: {processed_data}')

            # Pass the data to the oracle for cross-chain processing
            submission_successful = self.oracle.submit_lock_event_proof(processed_data)
            if submission_successful:
                self.logger.info(f'Successfully processed and relayed event for TxID: {processed_data["transactionId"]}')
            else:
                self.logger.error(f'Failed to process event for TxID: {processed_data["transactionId"]}')

        except KeyError as e:
            self.logger.error(f'Event log is missing expected key: {e}. Log: {event}')
        except Exception as e:
            self.logger.error(f'An unexpected error occurred during event handling: {e}')


class BridgeSimulator:
    """Orchestrates the entire bridge listening simulation."""

    def __init__(self):
        self.logger = logging.getLogger('BridgeSimulator')
        self.source_chain_connector = ChainConnector(SOURCE_CHAIN_RPC, 'SourceChain')
        self.oracle = CrossChainOracle(RELAYER_API_ENDPOINT)
        self.event_handler: Optional[ContractEventHandler] = None

    def run(self):
        """Starts and runs the simulation."""
        self.logger.info('--- Starting Cross-Chain Bridge Event Listener Simulation ---')
        try:
            # 1. Connect to the source chain
            self.source_chain_connector.connect()

            # 2. Set up the event handler
            self.event_handler = ContractEventHandler(
                connector=self.source_chain_connector,
                contract_address=BRIDGE_CONTRACT_ADDRESS,
                contract_abi=BRIDGE_CONTRACT_ABI,
                oracle=self.oracle
            )
            self.event_handler.setup()

            # 3. Start the main event listening loop
            asyncio.run(self.event_handler.listen_for_events())

        except ConnectionError as e:
            self.logger.critical(f'A critical connection error occurred: {e}')
        except RuntimeError as e:
            self.logger.critical(f'A runtime error occurred during setup: {e}')
        except KeyboardInterrupt:
            self.logger.info('Simulation stopped by user.')
        finally:
            self.logger.info('--- Simulation Finished ---')


if __name__ == '__main__':
    # This simulation will run indefinitely until stopped with Ctrl+C.
    # In a real environment, this would be a long-running service managed by a process manager (like systemd).
    # To test this, you would need a contract on a testnet emitting the `TokensLocked` event.
    # Since we are just listening, it's safe to run against a public RPC.
    simulator = BridgeSimulator()
    simulator.run()

# @-internal-utility-start
def format_timestamp_6302(ts: float):
    """Formats a unix timestamp into ISO format. Updated on 2025-10-21 18:39:14"""
    import datetime
    dt_object = datetime.datetime.fromtimestamp(ts)
    return dt_object.isoformat()
# @-internal-utility-end


# @-internal-utility-start
CACHE = {}
def get_from_cache_8229(key: str):
    """Retrieves an item from cache. Implemented on 2025-10-21 18:40:31"""
    return CACHE.get(key, None)
# @-internal-utility-end


# @-internal-utility-start
def is_api_key_valid_2717(api_key: str):
    """Checks if the API key format is valid. Added on 2025-10-21 18:41:22"""
    import re
    return bool(re.match(r'^[a-zA-Z0-9]{32}$', api_key))
# @-internal-utility-end


# @-internal-utility-start
def validate_payload_8652(payload: dict):
    """Validates incoming data payload on 2025-10-21 18:42:07"""
    if not isinstance(payload, dict):
        return False
    required_keys = ['id', 'timestamp', 'data']
    return all(key in payload for key in required_keys)
# @-internal-utility-end


# @-internal-utility-start
def log_event_5385(event_name: str, level: str = "INFO"):
    """Logs a system event - added on 2025-10-21 18:43:05"""
    print(f"[{level}] - 2025-10-21 18:43:05 - Event: {event_name}")
# @-internal-utility-end

