import re

# --- Abstract Syntax Tree (AST) Nodes ---

class Formula:
    """Base class for all logical formulas."""
    pass

class Variable(Formula):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"{self.name}"

class Constant(Formula):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"{self.name}"

class Predicate(Formula):
    def __init__(self, name, terms):
        self.name = name
        self.terms = terms
    def __repr__(self):
        return f"{self.name}({', '.join(map(str, self.terms))})"

class Negation(Formula):
    def __init__(self, formula):
        self.formula = formula
    def __repr__(self):
        return f"~({self.formula})"

class BinaryConnective(Formula):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Conjunction(BinaryConnective):
    def __repr__(self):
        return f"({self.left} & {self.right})"

class Disjunction(BinaryConnective):
    def __repr__(self):
        return f"({self.left} | {self.right})"

class Implication(BinaryConnective):
    def __repr__(self):
        return f"({self.left} -> {self.right})"

class Quantifier(Formula):
    def __init__(self, variable, formula):
        self.variable = variable
        self.formula = formula

class Forall(Quantifier):
    def __repr__(self):
        return f"forall {self.variable}. ({self.formula})"

class Exists(Quantifier):
    def __repr__(self):
        return f"exists {self.variable}. ({self.formula})"

# --- Parser ---

class ParseError(Exception):
    pass

class FOLParser:
    """
    A simple parser for a subset of First-Order Logic expressions.
    
    Supported Syntax:
    - Variables: lowercase letters (e.g., x, y)
    - Constants: Uppercase letters followed by optional numbers (e.g., A, B, C1)
    - Predicates: Uppercase letters followed by terms in parentheses (e.g., P(x), Q(A, y))
    - Negation: ~
    - Conjunction: &
    - Disjunction: |
    - Implication: ->
    - Quantifiers: 'forall', 'exists' (e.g., 'forall x. P(x)')
    - Parentheses for grouping binary connectives are required.
    """
    def __init__(self, text):
        self.tokens = self._tokenize(text)
        self.pos = 0

    def _tokenize(self, text):
        text = text.replace('(', ' ( ').replace(')', ' ) ').replace('.', ' . ')
        token_regex = r'\s*(\(|\)|[a-z][a-z0-9]*|[A-Z][A-Z0-9]*|~|&|\||->|\.|,)\s*'
        tokens = [t for t in re.split(token_regex, text) if t and not t.isspace()]
        return tokens

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self, expected=None):
        token = self._peek()
        if expected and token != expected:
            raise ParseError(f"Expected '{expected}' but found '{token}' at position {self.pos}")
        if token is None:
            raise ParseError("Unexpected end of input")
        self.pos += 1
        return token

    def parse(self):
        formula = self.parse_formula()
        if self.pos < len(self.tokens):
            raise ParseError(f"Unexpected token '{self._peek()}' at end of expression")
        return formula

    def parse_formula(self):
        token = self._peek()
        if token == '(':
            self._consume('(')
            left = self.parse_formula()
            op = self._consume()
            right = self.parse_formula()
            self._consume(')')
            if op == '&':
                return Conjunction(left, right)
            elif op == '|':
                return Disjunction(left, right)
            elif op == '->':
                return Implication(left, right)
            else:
                raise ParseError(f"Unknown binary operator: {op}")
        elif token == '~':
            self._consume('~')
            return Negation(self.parse_formula())
        elif token in ('forall', 'exists'):
            return self.parse_quantifier()
        elif token and token[0].isupper():
            return self.parse_predicate()
        else:
            raise ParseError(f"Unexpected token for a formula: {token}")

    def parse_quantifier(self):
        quantifier_type = self._consume()
        var_name = self._consume()
        if not var_name.islower():
            raise ParseError(f"Expected a lowercase variable after quantifier, but got '{var_name}'")
        variable = Variable(var_name)
        self._consume('.')
        formula = self.parse_formula()
        if quantifier_type == 'forall':
            return Forall(variable, formula)
        else: # exists
            return Exists(variable, formula)

    def parse_predicate(self):
        name = self._consume()
        self._consume('(')
        terms = []
        if self._peek() != ')':
            while True:
                terms.append(self.parse_term())
                if self._peek() == ')':
                    break
                self._consume(',')
        self._consume(')')
        return Predicate(name, terms)
    
    def parse_term(self):
        token = self._peek()
        if not token:
             raise ParseError("Unexpected end of input, expected a term.")
        if token[0].islower():
            self._consume()
            return Variable(token)
        elif token[0].isupper():
            self._consume()
            return Constant(token)
        else:
            raise ParseError(f"Invalid term: {token}")

if __name__ == '__main__':
    # --- Example Usage ---
    formulas_to_test = [
        "forall x. (P(x) -> Q(x, A))",
        "exists y. ~(P(y) & Q(y))",
        "( (forall x. P(x)) | (exists y. Q(y)) )",
        "R(B, z)"
    ]

    for f_str in formulas_to_test:
        try:
            print(f"Parsing: {f_str}")
            parser = FOLParser(f_str)
            parsed_formula = parser.parse()
            print(f"  Result: {parsed_formula}")
            print(f"  Type: {type(parsed_formula)}")
            print("-" * 20)
        except ParseError as e:
            print(f"  Error: {e}")
            print("-" * 20)

    # Example of a failing case
    fail_formula = "forall x P(x)" # Missing dot
    try:
        print(f"Parsing failing case: {fail_formula}")
        FOLParser(fail_formula).parse()
    except ParseError as e:
        print(f"  Successfully caught error: {e}")
