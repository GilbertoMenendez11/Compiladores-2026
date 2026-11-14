"""
MÓDULO: parser.py
PROYECTO FINAL: COMPILADORES - FASE 2 (VERSIÓN PYTHON)
Analizador Sintáctico Descendente Recursivo basado en indentación.
"""

from typing import List, Optional, Tuple
from lexer import Token, LexicalError

class ASTNode:
    def __init__(self, kind: str, value: Optional[str] = None,
                 children: Optional[List['ASTNode']] = None, line: int = 0, column: int = 0):
        self.kind = kind
        self.value = value
        self.children = children or []
        self.line = line
        self.column = column

    def pretty(self, prefix: str = "", is_last: bool = True, is_root: bool = True) -> str:
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
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

LITERALS = {'INT_LITERAL': 'Entero', 'FLOAT_LITERAL': 'Flotante', 'STRING_LITERAL': 'Cadena'}
STATEMENT_START = {'def', 'if', 'elif', 'else', 'while', 'for', 'return', 'print'}

class Parser:
    def __init__(self, tokens: List[Token]):
        last = tokens[-1] if tokens else Token('EOF', '', 1, 0)
        eof = Token('EOF', '', last.line, last.column + len(last.value))
        self.tokens = list(tokens) + [eof]
        self.pos = 0
        self.errors: List[ParseError] = []

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, k: int = 1) -> Token:
        return self.tokens[min(self.pos + k, len(self.tokens) - 1)]

    def check(self, *values: str) -> bool:
        tok = self.current
        return tok.type not in ('ID', 'EOF') and tok.type not in LITERALS and tok.value in values

    def check_type(self, *types: str) -> bool:
        return self.current.type in types

    def at_end(self) -> bool:
        return self.current.type == 'EOF'

    def advance(self) -> Token:
        tok = self.current
        if not self.at_end():
            self.pos += 1
        return tok

    @staticmethod
    def describe(tok: Token) -> str:
        return "fin de archivo" if tok.type == 'EOF' else f"'{tok.value}'"

    def error(self, message: str, tok: Optional[Token] = None) -> ParseError:
        tok = tok or self.current
        return ParseError(message, tok.line, tok.column)

    def expect(self, value: str, context: str = "") -> Token:
        if self.check(value):
            return self.advance()
        raise self.error(f"Se esperaba '{value}'{' ' + context if context else ''} pero se encontró {self.describe(self.current)}")

    def expect_type(self, token_type: str, context: str = "") -> Token:
        if self.check_type(token_type):
            return self.advance()
        raise self.error(f"Se esperaba {token_type}{' ' + context if context else ''} pero se encontró {self.describe(self.current)}")

    def expect_id(self, context: str = "") -> Token:
        if self.check_type('ID'):
            return self.advance()
        raise self.error(f"Se esperaba un identificador{' ' + context if context else ''} pero se encontró {self.describe(self.current)}")

    def synchronize(self):
        """Recuperación en Modo Pánico (salta al siguiente NEWLINE o palabra clave)."""
        self.advance()
        while not self.at_end():
            if self.tokens[self.pos - 1].type == 'NEWLINE':
                return
            if self.current.value in STATEMENT_START:
                return
            self.advance()

    def consume_newlines(self):
        while self.check_type('NEWLINE'):
            self.advance()

    def parse(self) -> Tuple[ASTNode, List[ParseError]]:
        program = ASTNode('Programa')
        while not self.at_end():
            self.consume_newlines()
            if self.at_end():
                break
            try:
                program.children.append(self.statement())
            except ParseError as err:
                self.errors.append(err)
                self.synchronize()
        return program, self.errors

    def statement(self) -> ASTNode:
        if self.check('def'):
            return self.function_decl()
        if self.check('if'):
            return self.if_statement()
        if self.check('while'):
            return self.while_statement()
        if self.check('return'):
            return self.return_statement()
        
        expr = self.expression()
        self.expect_type('NEWLINE', "al final de la instrucción")
        return ASTNode('SentenciaExpresion', children=[expr], line=expr.line, column=expr.column)

    def function_decl(self) -> ASTNode:
        tok = self.advance()
        id_tok = self.expect_id("como nombre de función")
        self.expect('(', "después del nombre de la función")
        
        params = []
        if not self.check(')'):
            params.append(ASTNode('Parametro', value=self.expect_id().value))
            while self.check(','):
                self.advance()
                params.append(ASTNode('Parametro', value=self.expect_id().value))
                
        self.expect(')', "al cerrar parámetros")
        self.expect(':', "al iniciar el bloque de la función")
        body = self.block()
        
        return ASTNode('Funcion', value=id_tok.value, children=[ASTNode('Parametros', children=params), body], line=tok.line, column=tok.column)

    def if_statement(self) -> ASTNode:
        tok = self.advance()
        cond = self.expression()
        self.expect(':', "después de la condición del 'if'")
        body = self.block()
        
        children = [ASTNode('Condicion', children=[cond]), ASTNode('Entonces', children=[body])]
        
        if self.check('else'):
            self.advance()
            self.expect(':', "después de 'else'")
            else_body = self.block()
            children.append(ASTNode('SiNo', children=[else_body]))
            
        return ASTNode('If', children=children, line=tok.line, column=tok.column)

    def while_statement(self) -> ASTNode:
        tok = self.advance()
        cond = self.expression()
        self.expect(':', "después de la condición del 'while'")
        body = self.block()
        return ASTNode('While', children=[cond, body], line=tok.line, column=tok.column)

    def return_statement(self) -> ASTNode:
        tok = self.advance()
        val = None
        if not self.check_type('NEWLINE'):
            val = self.expression()
        self.expect_type('NEWLINE', "al final del return")
        return ASTNode('Return', children=[val] if val else [], line=tok.line, column=tok.column)

    def block(self) -> ASTNode:
        self.expect_type('NEWLINE', "esperando salto de línea antes del bloque")
        self.expect_type('INDENT', "esperando indentación para el bloque")
        stmts = []
        while not self.check_type('DEDENT') and not self.at_end():
            self.consume_newlines()
            if self.check_type('DEDENT'): break
            stmts.append(self.statement())
        self.expect_type('DEDENT', "al cerrar el bloque")
        return ASTNode('Bloque', children=stmts)

    def expression(self) -> ASTNode:
        return self.assignment()

    def assignment(self) -> ASTNode:
        expr = self.equality()
        if self.check('='):
            op = self.advance()
            value = self.assignment()
            if expr.kind == 'Variable':
                return ASTNode('Asignacion', value=expr.value, children=[value], line=op.line, column=op.column)
            else:
                raise self.error("El lado izquierdo de la asignación debe ser una variable", op)
        return expr

    def equality(self) -> ASTNode:
        expr = self.relational()
        while self.check('==', '!='):
            op = self.advance()
            right = self.relational()
            expr = ASTNode('OpBinaria', value=op.value, children=[expr, right], line=op.line, column=op.column)
        return expr

    def relational(self) -> ASTNode:
        expr = self.additive()
        while self.check('<', '<=', '>', '>='):
            op = self.advance()
            right = self.additive()
            expr = ASTNode('OpBinaria', value=op.value, children=[expr, right], line=op.line, column=op.column)
        return expr

    def additive(self) -> ASTNode:
        expr = self.multiplicative()
        while self.check('+', '-'):
            op = self.advance()
            right = self.multiplicative()
            expr = ASTNode('OpBinaria', value=op.value, children=[expr, right], line=op.line, column=op.column)
        return expr

    def multiplicative(self) -> ASTNode:
        expr = self.unary()
        while self.check('*', '/', '%'):
            op = self.advance()
            right = self.unary()
            expr = ASTNode('OpBinaria', value=op.value, children=[expr, right], line=op.line, column=op.column)
        return expr

    def unary(self) -> ASTNode:
        if self.check('not', '-'):
            op = self.advance()
            right = self.unary()
            return ASTNode('OpUnaria', value=op.value, children=[right], line=op.line, column=op.column)
        return self.primary()

    def primary(self) -> ASTNode:
        tok = self.advance()
        if tok.type in LITERALS:
            return ASTNode(LITERALS[tok.type], value=tok.value, line=tok.line, column=tok.column)
            
        if tok.type == 'ID':
            if self.check('('):
                self.advance()
                args = []
                if not self.check(')'):
                    args.append(self.expression())
                    while self.check(','):
                        self.advance()
                        args.append(self.expression())
                self.expect(')', "al cerrar parámetros de función")
                return ASTNode('Llamada', value=tok.value, children=args, line=tok.line, column=tok.column)
            return ASTNode('Variable', value=tok.value, line=tok.line, column=tok.column)
            
        if tok.value == '(':
            expr = self.expression()
            self.expect(')', "para cerrar paréntesis")
            return expr
            
        raise self.error(f"Se esperaba una expresión, pero se encontró {self.describe(tok)}")