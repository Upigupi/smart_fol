# smart_fol: Cross-Chain Bridge Event Listener Simulation

This repository contains a Python-based simulation of a critical component for a cross-chain bridge: an event listener. This script is designed to monitor a smart contract on a source blockchain (e.g., Ethereum) for specific events (`TokensLocked`), and upon detection, it simulates the process of relaying this information to a destination chain via an oracle/relayer service.

This project is an architectural demonstration, showcasing a robust, modular, and scalable design for building real-world blockchain infrastructure components.

## Concept

Cross-chain bridges allow users to transfer assets or data from one blockchain to another. A common mechanism is the "lock-and-mint" model:

1.  **Lock**: A user locks their assets (e.g., ERC20 tokens) in a smart contract on the source chain.
2.  **Event Emission**: The smart contract emits an event (`TokensLocked`) containing details of the lock-up (user, token, amount, destination chain).
3.  **Listen & Verify**: Off-chain services, often called relayers or oracles, listen for this event. They wait for a certain number of block confirmations to ensure the transaction is final.
4.  **Relay**: The relayer submits a cryptographically signed proof of the event to a contract on the destination chain.
5.  **Mint**: The destination chain contract verifies the proof and mints a corresponding wrapped or synthetic asset for the user.

This script simulates **Step 3 and Step 4**, acting as the off-chain listener and relayer.

## Code Architecture

The script is designed with a clear separation of concerns, using several classes to handle different parts of the process:

-   `ChainConnector`: 
    -   **Responsibility**: Manages the connection to a blockchain via a JSON-RPC endpoint using `web3.py`.
    -   **Features**: Handles connection setup, status checking, and provides a `web3` instance and a method to get a contract object.

-   `ContractEventHandler`:
    -   **Responsibility**: The core logic for monitoring a specific contract for a specific event.
    -   **Features**: It creates an event filter, polls for new event logs in an asynchronous loop, and processes each event by passing it to a handler (the oracle).
    -   **Resilience**: Includes basic error handling to attempt reconnection if the RPC connection is lost during polling.

-   `CrossChainOracle`:
    -   **Responsibility**: Simulates the relayer or oracle network.
    -   **Features**: Receives processed event data, performs basic validation, and simulates submitting this data to a relayer network's API endpoint using the `requests` library. In a real-world scenario, this class would handle cryptographic signing and more complex validation logic.

-   `BridgeSimulator`:
    -   **Responsibility**: The main orchestrator class.
    -   **Features**: Initializes and wires together all the other components (`ChainConnector`, `CrossChainOracle`, `ContractEventHandler`) and starts the main execution loop.

### Data Flow Diagram

```
+-----------------------+      +--------------------------+      +------------------------+
| Source Chain Node     | <--- |   ChainConnector         |      |                        |
| (e.g., Sepolia RPC)   |      |   (web3.py)              |      |                        |
+-----------------------+      +-------------+------------+      |                        |
           ^                                 |                   |   CrossChainOracle     |
           | (Polls for Events)              | (Provides web3    |   (Relayer Simulation) |
           |                                 |  instance)         |                        |
+----------+----------------+                |                   +------------+-----------+
|  ContractEventHandler     | ---------------/                   (Notifies   |           ^
| (Listens for `TokensLocked`) |  (Processes & passes event data) -> Oracle) |           |
+---------------------------+                                                | (Submits Proof via HTTP)
                                                                             |           |
                                                                             v           |
                                                                     +-------+----------------+
                                                                     | Relayer Network API    |
                                                                     | (e.g., mockrelayer.com)|
                                                                     +------------------------+
```

## How it Works

1.  **Initialization**: The `BridgeSimulator` is instantiated. It reads configuration like RPC URLs from a `.env` file.
2.  **Connection**: The `ChainConnector` establishes a connection to the source chain's RPC endpoint.
3.  **Setup**: The `ContractEventHandler` is set up with the source chain connection, the bridge contract's address and ABI, and an instance of the `CrossChainOracle`.
4.  **Listening Loop**: The `listen_for_events` method is called. It creates a `web3.py` event filter that watches for new `TokensLocked` events from the latest block onwards.
5.  **Event Detection**: The script enters an `asyncio` loop, polling for new events every few seconds (e.g., 5 seconds).
6.  **Event Handling**: When one or more events are detected, the `handle_event` method is triggered for each.
7.  **Data Processing**: The event log is parsed to extract key information like the user's address, token address, amount, and the unique transaction ID.
8.  **Relaying**: The processed data is passed to the `CrossChainOracle`. The oracle formats this data into a JSON payload and simulates a `POST` request to a relayer API endpoint. This simulates the action of informing the destination chain about the locked funds.
9.  **Logging**: The entire process is logged to the console, providing a clear view of the listener's status, detected events, and actions taken.

## Usage Example

### 1. Prerequisites

-   Python 3.8+
-   An RPC URL for an Ethereum-compatible network (e.g., from Infura, Alchemy, or a public endpoint). This script is read-only, so a public endpoint for a testnet like Sepolia is sufficient.

### 2. Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/your-username/smart_fol.git
cd smart_fol
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root of the project directory and add your source chain's RPC URL. The other values are placeholders and do not need to be changed for the simulation to run.

```.env
# .env file
SOURCE_CHAIN_RPC_URL="https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"

# Optional: You can override the other defaults if needed
# DESTINATION_CHAIN_RPC_URL="..."
# RELAYER_API_ENDPOINT="..."
```

### 4. Running the Script

Execute the main Python script from your terminal:

```bash
python bridge_event_listener.py
```

### 5. Expected Output

The script will start and begin polling for events. Since the configured contract address is just a placeholder, it is unlikely to find any real `TokensLocked` events. However, the output will show that the listener is active and working.

```
2023-10-27 15:30:00 - INFO - [BridgeSimulator] - --- Starting Cross-Chain Bridge Event Listener Simulation ---
2023-10-27 15:30:02 - INFO - [ChainConnector-SourceChain] - Successfully connected to SourceChain. Latest block: 4512345
2023-10-27 15:30:02 - INFO - [ContractEventHandler] - Event handler set up for contract at 0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B
2023-10-27 15:30:02 - INFO - [ContractEventHandler] - Starting to listen for `TokensLocked` events... Polling every 5 seconds.
2023-10-27 15:30:07 - DEBUG - [ContractEventHandler] - No new events detected.
2023-10-27 15:30:12 - DEBUG - [ContractEventHandler] - No new events detected.
...
```

If an event were to be emitted by the target contract, you would see output similar to this:

```
...
2023-10-27 15:31:05 - INFO - [ContractEventHandler] - Found 1 new event(s).
2023-10-27 15:31:05 - INFO - [ContractEventHandler] - Processing event from block 4512350
2023-10-27 15:31:05 - INFO - [ContractEventHandler] - TokensLocked Event Data: {'user': '0x...', 'token': '0x...', 'amount': 1000000000000000000, 'destinationChainId': 80001, 'transactionId': '0x...', 'blockNumber': 4512350, 'txHash': '0x...'}
2023-10-27 15:31:05 - INFO - [CrossChainOracle] - Submitting event proof to relayer: https://api.mockrelayer.com/submit_proof
2023-10-27 15:31:06 - INFO - [CrossChainOracle] - Simulated successful submission for TxID: 0x...
2023-10-27 15:31:06 - INFO - [ContractEventHandler] - Successfully processed and relayed event for TxID: 0x...
...
```

To stop the script, press `Ctrl+C`.
