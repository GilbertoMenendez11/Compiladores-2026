"""
MÓDULO: parser.py
PROYECTO FINAL: COMPILADORES - FASE 2
ANÁLISIS SINTÁCTICO
"""

# Nodos del árbol de sintaxis abstracta


class ASTNode:
    pass


class NumberNode(ASTNode):
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f"Num({self.token.value})"


class StringNode(ASTNode):
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f"String({self.token.value})"


class VarNode(ASTNode):
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f"Var({self.token.value})"


class BinOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"BinOp({self.left}, '{self.op.value}', {self.right})"


class AssignNode(ASTNode):
    def __init__(self, var_node, expr):
        self.var_node = var_node
        self.expr = expr

    def __repr__(self):
        return f"Assign({self.var_node}, {self.expr})"


# Analizador sintáctico


class Parser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos] if self.tokens else None

    # Avanza al siguiente token

    def advance(self):
        self.pos += 1

        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    # Ignora saltos de línea e indentación

    def consume_newlines(self):
        while self.current_token and self.current_token.type in (
            "NEWLINE",
            "INDENT",
            "DEDENT",
        ):
            self.advance()

    # Inicia el análisis sintáctico

    def parse(self):
        statements = []

        self.consume_newlines()

        while self.current_token is not None:
            statements.append(self.parse_statement())
            self.consume_newlines()

        return statements

    # Reconoce una asignación o una expresión

    def parse_statement(self):

        if (
            self.current_token.type == "ID"
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].type == "OP_ASSIGN"
        ):
            var_node = VarNode(self.current_token)

            self.advance()
            self.advance()

            expr = self.parse_expression()

            return AssignNode(var_node, expr)

        return self.parse_expression()

    # Reconoce operaciones de suma y resta

    def parse_expression(self):

        left = self.parse_term()

        while (
            self.current_token
            and self.current_token.type == "OP_ARITH"
            and self.current_token.value in ("+", "-")
        ):
            op_token = self.current_token

            self.advance()

            right = self.parse_term()

            left = BinOpNode(left, op_token, right)

        return left

    # Reconoce operaciones de multiplicación, división y módulo

    def parse_term(self):

        left = self.parse_factor()

        while (
            self.current_token
            and self.current_token.type == "OP_ARITH"
            and self.current_token.value in ("*", "/", "%")
        ):
            op_token = self.current_token

            self.advance()

            right = self.parse_factor()

            left = BinOpNode(left, op_token, right)

        return left

    # Reconoce números, strings, identificadores y expresiones entre paréntesis

    def parse_factor(self):

        token = self.current_token

        if token is None:
            raise SyntaxError("Fin de archivo inesperado.")

        if token.type in ("INT_LITERAL", "FLOAT_LITERAL"):
            self.advance()
            return NumberNode(token)

        if token.type == "STRING_LITERAL":
            self.advance()
            return StringNode(token)

        if token.type == "ID":
            self.advance()
            return VarNode(token)

        if token.type == "DELIM" and token.value == "(":

            self.advance()

            expr = self.parse_expression()

            if (
                self.current_token
                and self.current_token.type == "DELIM"
                and self.current_token.value == ")"
            ):
                self.advance()
                return expr

            raise SyntaxError(f"Falta ')' en la línea {token.line}")

        raise SyntaxError(
            f"Sintaxis inválida cerca de '{token.value}' " f"en la línea {token.line}"
        )
