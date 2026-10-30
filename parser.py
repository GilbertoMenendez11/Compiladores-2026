"""
MÓDULO: parser.py
PROYECTO FINAL: COMPILADORES - FASE 2
ANÁLISIS SINTÁCTICO
"""

# 1. NODOS DEL ÁRBOL DE SINTAXIS ABSTRACTA (AST)


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


class UnaryOpNode(ASTNode):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def __repr__(self):
        return f"UnaryOp('{self.op.value}', {self.expr})"


class AssignNode(ASTNode):
    def __init__(self, var_node, expr):
        self.var_node = var_node
        self.expr = expr

    def __repr__(self):
        return f"Assign({self.var_node}, {self.expr})"


# 2. ANALIZADOR SINTÁCTICO


class Parser:

    def __init__(self, tokens):
        # Ignorar tokens de espacios estructurales
        self.tokens = [
            token
            for token in tokens
            if token.type not in ("NEWLINE", "INDENT", "DEDENT")
        ]
        self.pos = 0
        self.current_token = self.tokens[self.pos] if self.tokens else None

    # Avanza al siguiente token
    def advance(self):
        self.pos += 1

        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    # Verifica el tipo y valor de un token
    def check(self, token_type, value=None):
        if self.current_token is None:
            return False

        if self.current_token.type != token_type:
            return False

        if value is not None and self.current_token.value != value:  # noqa: SIM103
            return False

        return True

    # Genera errores sintácticos
    def syntax_error(self, message):
        if self.current_token:
            raise SyntaxError(
                f"{message} en línea {self.current_token.line}, "
                f"columna {self.current_token.column}"
            )

        raise SyntaxError(f"{message} al final del archivo")

    # Inicia el análisis sintáctico
    def parse(self):
        statements = []

        while self.current_token is not None:
            statements.append(self.parse_statement())

        return statements

    # Reconoce asignaciones o expresiones
    def parse_statement(self):

        if (
            self.check("ID")
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].type == "OP_ASSIGN"
        ):
            var_node = VarNode(self.current_token)

            self.advance()
            self.advance()

            expr = self.parse_expression()

            return AssignNode(var_node, expr)

        return self.parse_expression()

    # Suma y resta
    def parse_expression(self):
        left = self.parse_term()

        while self.check("OP_ARITH") and self.current_token.value in ("+", "-"):
            op = self.current_token
            self.advance()

            right = self.parse_term()
            left = BinOpNode(left, op, right)

        return left

    # Multiplicación, división, módulo y división entera
    def parse_term(self):
        left = self.parse_factor()

        while self.check("OP_ARITH") and self.current_token.value in (
            "*",
            "/",
            "%",
            "//",
        ):
            op = self.current_token
            self.advance()

            right = self.parse_factor()
            left = BinOpNode(left, op, right)

        return left

    # Potencia
    def parse_power(self):
        left = self.parse_primary()

        if self.check("OP_ARITH", "**"):
            op = self.current_token
            self.advance()

            right = self.parse_factor()
            left = BinOpNode(left, op, right)

        return left

    # Factor: operadores unarios y potencia
    def parse_factor(self):

        if self.check("OP_ARITH") and self.current_token.value in ("+", "-"):
            op = self.current_token
            self.advance()

            return UnaryOpNode(op, self.parse_factor())

        return self.parse_power()

    # Números, cadenas, variables y paréntesis
    def parse_primary(self):
        token = self.current_token

        if token is None:
            self.syntax_error("Expresión incompleta")

        if token.type in ("INT_LITERAL", "FLOAT_LITERAL"):
            self.advance()
            return NumberNode(token)

        if token.type == "STRING_LITERAL":
            self.advance()
            return StringNode(token)

        if token.type == "ID":
            self.advance()
            return VarNode(token)

        if self.check("DELIM", "("):
            self.advance()

            expr = self.parse_expression()

            if not self.check("DELIM", ")"):
                self.syntax_error("Falta ')'")

            self.advance()
            return expr

        self.syntax_error(f"Sintaxis inválida cerca de '{token.value}'")
