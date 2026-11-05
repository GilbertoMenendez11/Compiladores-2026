"""
MÓDULO: sintactico.py
PROYECTO FINAL: COMPILADORES - FASE 2

Analizador Sintáctico Descendente Recursivo.
"""

from lexer import Token

# 1. ESTRUCTURAS DE DATOS


class ASTNode:
    """Nodo del Árbol de Sintaxis Abstracta (AST)."""

    def __init__(
        self,
        kind: str,
        value: str | None = None,
        children: list["ASTNode"] | None = None,
        line: int = 0,
        column: int = 0,
    ):
        self.kind = kind
        self.value = value
        self.children = children or []
        self.line = line
        self.column = column

    def pretty(
        self, prefix: str = "", is_last: bool = True, is_root: bool = True
    ) -> str:
        """Devuelve el árbol como texto con sangría."""
        label = self.kind if self.value is None else f"{self.kind}: {self.value}"
        if is_root:
            lines, child_prefix = [label], ""
        else:
            lines = [prefix + ("└── " if is_last else "├── ") + label]
            child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(self.children):
            lines.append(child.pretty(child_prefix, i == len(self.children) - 1, False))
        return "\n".join(lines)


class ParseError(Exception):
    """Error sintáctico detectado (se lanza para abortar la regla actual)."""

    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


# 2. CONSTANTES DE LA GRAMÁTICA

LITERALS = {
    "INT_LITERAL": "Entero",
    "FLOAT_LITERAL": "Flotante",
    "STRING_LITERAL": "Cadena",
}

# Conjuntos de sincronización y tipos base
TYPES = {"int", "float", "string", "void"}
STATEMENT_START = {"if", "while", "for", "return", "{"}


# 3. CLASE PRINCIPAL DEL ANALIZADOR SINTÁCTICO


class Parser:
    def __init__(self, tokens: list[Token]):
        last = tokens[-1] if tokens else Token("EOF", "", 1, 0)
        eof = Token("EOF", "", last.line, last.column + len(last.value))
        self.tokens = list(tokens) + [eof]
        self.pos = 0
        self.errors: list[ParseError] = []

    # Utilidades
    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, k: int = 1) -> Token:
        return self.tokens[min(self.pos + k, len(self.tokens) - 1)]

    def check(self, *values: str) -> bool:
        tok = self.current
        return (
            tok.type not in ("ID", "EOF")
            and tok.type not in LITERALS
            and tok.value in values
        )

    def at_end(self) -> bool:
        return self.current.type == "EOF"

    def advance(self) -> Token:
        tok = self.current
        if not self.at_end():
            self.pos += 1
        return tok

    @staticmethod
    def describe(tok: Token) -> str:
        return "fin de archivo" if tok.type == "EOF" else f"'{tok.value}'"

    def error(self, message: str, tok: Token | None = None) -> ParseError:
        tok = tok or self.current
        return ParseError(message, tok.line, tok.column)

    def expect(self, value: str, context: str = "") -> Token:
        if self.check(value):
            return self.advance()
        msg = f"Se esperaba '{value}'{' ' + context if context else ''} pero se encontró {self.describe(self.current)}"
        if value in (";", ")") and self.pos > 0:
            prev = self.tokens[self.pos - 1]
            raise ParseError(msg, prev.line, prev.column + len(prev.value))
        raise self.error(msg)

    def expect_id(self, context: str = "") -> Token:
        if self.current.type == "ID":
            return self.advance()
        raise self.error(
            f"Se esperaba un identificador{' ' + context if context else ''} pero se encontró {self.describe(self.current)}"
        )

    # Recuperación de errores
    def synchronize(self):
        """Recuperación en Modo Pánico: avanza hasta un punto seguro."""
        self.advance()  # Consumimos el token que causó el error
        while not self.at_end():
            # Si el token anterior fue fin de sentencia, estamos seguros
            if self.tokens[self.pos - 1].value == ";":
                return
            # Si el token actual inicia una nueva sentencia o declaración
            if self.current.value in TYPES or self.current.value in STATEMENT_START:
                return
            self.advance()

    # REGLA PRINCIPAL
    def parse(self) -> tuple[ASTNode, list[ParseError]]:
        program = ASTNode("Programa")
        while not self.at_end():
            try:
                program.children.append(self.declaration())
            except ParseError as err:
                self.errors.append(err)
                self.synchronize()
        return program, self.errors

    # Declaraciones (Variables y Funciones)
    def declaration(self) -> ASTNode:
        if self.current.value in TYPES:
            return self.type_decl()
        return self.statement()

    def type_decl(self) -> ASTNode:
        type_tok = self.advance()  # int, float, etc.
        id_tok = self.expect_id("como nombre de variable o función")

        # Miramos si es función o variable según el siguiente token
        if self.check("("):
            return self.function_decl(type_tok, id_tok)
        else:
            return self.var_decl_tail(type_tok, id_tok)

    def function_decl(self, type_tok: Token, id_tok: Token) -> ASTNode:
        self.advance()  # Consume '('
        params = []
        if not self.check(")"):
            while True:
                p_type = self.advance()
                if p_type.value not in TYPES:
                    raise self.error(
                        f"Se esperaba tipo de dato pero se encontró {self.describe(p_type)}",
                        p_type,
                    )
                p_id = self.expect_id("como parámetro")
                params.append(
                    ASTNode(
                        "Parametro",
                        value=f"{p_type.value} {p_id.value}",
                        line=p_type.line,
                        column=p_type.column,
                    )
                )
                if not self.check(","):
                    break
                self.advance()
        self.expect(")", "al cerrar parámetros")
        body = self.block()
        return ASTNode(
            "Funcion",
            value=f"{type_tok.value} {id_tok.value}",
            children=[ASTNode("Parametros", children=params), body],
            line=type_tok.line,
            column=type_tok.column,
        )

    def var_decl_tail(self, type_tok: Token, id_tok: Token) -> ASTNode:
        vars_nodes = []

        def parse_single_var(name_tok):
            node = ASTNode(
                "Variable",
                value=name_tok.value,
                line=name_tok.line,
                column=name_tok.column,
            )
            if self.check("="):
                self.advance()
                node.children.append(self.expression())
            return node

        vars_nodes.append(parse_single_var(id_tok))

        while self.check(","):
            self.advance()
            next_id = self.expect_id("en lista de variables")
            vars_nodes.append(parse_single_var(next_id))

        self.expect(";", "al final de la declaración")

        kind = "Declaracion" if len(vars_nodes) == 1 else "DeclaracionMultiple"
        return ASTNode(
            kind,
            value=type_tok.value,
            children=vars_nodes,
            line=type_tok.line,
            column=type_tok.column,
        )

    # Sentencias
    def statement(self) -> ASTNode:
        if self.check("if"):
            return self.if_statement()
        if self.check("while"):
            return self.while_statement()
        if self.check("for"):
            return self.for_statement()
        if self.check("return"):
            return self.return_statement()
        if self.check("{"):
            return self.block()

        # Sentencia vacía
        if self.check(";"):
            tok = self.advance()
            return ASTNode("SentenciaVacia", line=tok.line, column=tok.column)

        expr = self.expression()
        self.expect(";", "al final de la sentencia")
        return ASTNode(
            "SentenciaExpresion", children=[expr], line=expr.line, column=expr.column
        )

    def if_statement(self) -> ASTNode:
        tok = self.advance()
        self.expect("(", "después de 'if'")
        cond = self.expression()
        self.expect(")", "al cerrar la condición del 'if'")
        children = [
            ASTNode("Condicion", children=[cond]),
            ASTNode("Entonces", children=[self.statement()]),
        ]
        if self.check("else"):
            self.advance()
            children.append(ASTNode("SiNo", children=[self.statement()]))
        return ASTNode("If", children=children, line=tok.line, column=tok.column)

    def while_statement(self) -> ASTNode:
        tok = self.advance()
        self.expect("(", "después de 'while'")
        cond = self.expression()
        self.expect(")", "al cerrar la condición")
        body = self.statement()
        return ASTNode("While", children=[cond, body], line=tok.line, column=tok.column)

    def for_statement(self) -> ASTNode:
        tok = self.advance()
        self.expect("(", "después de 'for'")

        # Inicialización
        if self.check(";"):
            init = ASTNode("SentenciaVacia")
            self.advance()
        elif self.current.value in TYPES:
            t_tok = self.advance()
            i_tok = self.expect_id()
            init = self.var_decl_tail(t_tok, i_tok)
        else:
            expr = self.expression()
            self.expect(";", "en inicialización del 'for'")
            init = ASTNode("SentenciaExpresion", children=[expr])

        # Condición
        if self.check(";"):
            cond = ASTNode("SentenciaVacia")
            self.advance()
        else:
            cond = self.expression()
            self.expect(";", "en condición del 'for'")

        # Paso/Incremento
        if self.check(")"):
            step = ASTNode("SentenciaVacia")
        else:
            step = self.expression()

        self.expect(")", "al cerrar el 'for'")
        body = self.statement()

        return ASTNode(
            "For", children=[init, cond, step, body], line=tok.line, column=tok.column
        )

    def return_statement(self) -> ASTNode:
        tok = self.advance()
        if self.check(";"):
            self.advance()
            return ASTNode("Return", line=tok.line, column=tok.column)
        expr = self.expression()
        self.expect(";", "al final del return")
        return ASTNode("Return", children=[expr], line=tok.line, column=tok.column)

    def block(self) -> ASTNode:
        tok = self.advance()
        stmts = []
        while not self.check("}") and not self.at_end():
            stmts.append(self.declaration())
        self.expect("}", "al cerrar el bloque")
        return ASTNode("Bloque", children=stmts, line=tok.line, column=tok.column)

    # Expresiones (Aplicando niveles de precedencia)
    def expression(self) -> ASTNode:
        return self.assignment()

    def assignment(self) -> ASTNode:
        # Menor precedencia (asociativa por la derecha)
        expr = self.equality()
        if self.check("="):
            eq_tok = self.advance()
            value = self.assignment()
            if expr.kind == "Identificador":
                return ASTNode(
                    "Asignacion",
                    value=expr.value,
                    children=[value],
                    line=expr.line,
                    column=expr.column,
                )
            else:
                raise self.error(
                    "Asignación no válida (el lado izquierdo debe ser un identificador)",
                    eq_tok,
                )
        return expr

    def equality(self) -> ASTNode:
        expr = self.relational()
        while self.check("==", "!="):
            op = self.advance()
            right = self.relational()
            expr = ASTNode(
                "OpBinaria",
                value=op.value,
                children=[expr, right],
                line=op.line,
                column=op.column,
            )
        return expr

    def relational(self) -> ASTNode:
        expr = self.additive()
        while self.check("<", ">", "<=", ">="):
            op = self.advance()
            right = self.additive()
            expr = ASTNode(
                "OpBinaria",
                value=op.value,
                children=[expr, right],
                line=op.line,
                column=op.column,
            )
        return expr

    def additive(self) -> ASTNode:
        expr = self.multiplicative()
        while self.check("+", "-"):
            op = self.advance()
            right = self.multiplicative()
            expr = ASTNode(
                "OpBinaria",
                value=op.value,
                children=[expr, right],
                line=op.line,
                column=op.column,
            )
        return expr

    def multiplicative(self) -> ASTNode:
        expr = self.unary()
        while self.check("*", "/"):
            op = self.advance()
            right = self.unary()
            expr = ASTNode(
                "OpBinaria",
                value=op.value,
                children=[expr, right],
                line=op.line,
                column=op.column,
            )
        return expr

    def unary(self) -> ASTNode:
        if self.check("-"):
            op = self.advance()
            right = self.unary()
            return ASTNode(
                "OpUnaria",
                value=op.value,
                children=[right],
                line=op.line,
                column=op.column,
            )
        return self.primary()

    def primary(self) -> ASTNode:
        # Mayor precedencia
        tok = self.advance()
        if tok.type in LITERALS:
            return ASTNode(
                LITERALS[tok.type], value=tok.value, line=tok.line, column=tok.column
            )

        if tok.type == "ID":
            # Verificamos si es una llamada a función
            if self.check("("):
                self.advance()
                args = []
                if not self.check(")"):
                    args.append(self.expression())
                    while self.check(","):
                        self.advance()
                        args.append(self.expression())
                self.expect(")", "al cerrar argumentos de llamada")
                return ASTNode(
                    "Llamada",
                    value=tok.value,
                    children=args,
                    line=tok.line,
                    column=tok.column,
                )
            return ASTNode(
                "Identificador", value=tok.value, line=tok.line, column=tok.column
            )

        if tok.value == "(":
            expr = self.expression()
            self.expect(")", "al cerrar paréntesis")
            return expr

        raise self.error(
            f"Se esperaba una expresión pero se encontró {self.describe(tok)}", tok
        )
