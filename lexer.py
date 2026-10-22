"""
MÓDULO: lexer.py
PROYECTO FINAL: COMPILADORES - FASE 1 (VERSIÓN PYTHON)
"""

import re
from typing import NamedTuple

# 1. ESTRUCTURAS DE DATOS


class Token(NamedTuple):
    """Estructura para representar un Token detectado."""

    type: str
    value: str
    line: int
    column: int


class LexicalError(NamedTuple):
    """Estructura para representar un error léxico detectado."""

    message: str
    char: str
    line: int
    column: int


# 2. CLASE PRINCIPAL DEL ANALIZADOR LÉXICO


class PythonLexer:
    """
    Analizador Léxico (Scanner) para un subconjunto de Python.
    Maneja la detección de tokens y la indentación estricta (INDENT/DEDENT).
    """

    # Definimos los patrones en orden de prioridad (Maximal Munch)
    TOKEN_SPECIFICATION = [
        ("NEWLINE", r"\n"),
        ("COMMENT", r"#.*"),
        ("FLOAT_LITERAL", r"\d+\.\d+"),
        ("INT_LITERAL", r"\d+"),
        # Soporta comillas dobles y simples
        ("STRING_LITERAL", r'"[^"\\]*(\\.[^"\\]*)*"|\'[^\'\\]*(\\.[^\'\\]*)*\''),
        ("OP_REL", r"==|!=|<=|>=|<|>"),
        ("OP_ASSIGN", r"="),
        ("OP_ARITH", r"\*\*|//|[+\-*/%]"),
        ("DELIM", r"[()\[\]{},:;.@]"),
        ("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("SKIP", r"[ \t]+"),  # Espacios en blanco
        ("MISMATCH", r"."),  # Comodín para errores
    ]

    # Mapeo de palabras reservadas
    KEYWORD_MAP = {
        "def": "PR_DEF",
        "if": "PR_IF",
        "elif": "PR_ELIF",
        "else": "PR_ELSE",
        "while": "PR_WHILE",
        "for": "PR_FOR",
        "return": "PR_RETURN",
        "print": "PR_PRINT",
        "True": "PR_TRUE",
        "False": "PR_FALSE",
        "None": "PR_NONE",
        "and": "PR_AND",
        "or": "PR_OR",
        "not": "PR_NOT",
    }

    def __init__(self, code: str):
        self.code = code
        # Compila la expresión regular combinando todos los grupos etiquetados
        tok_regex = "|".join(
            f"(?P<{pair[0]}>{pair[1]})" for pair in self.TOKEN_SPECIFICATION
        )
        self.regex = re.compile(tok_regex)

    def tokenize(self) -> tuple[list[Token], list[LexicalError]]:
        tokens: list[Token] = []
        errors: list[LexicalError] = []

        indent_stack = [0]
        current_indent = 0
        at_line_start = (
            True  # Bandera para capturar los espacios iniciales de cada línea
        )

        line_num = 1
        line_start = 0

        for mo in self.regex.finditer(self.code):
            kind = mo.lastgroup
            value = mo.group()
            position = mo.start()
            col_num = position - line_start + 1

            # 1. Manejo de saltos de línea
            if kind == "NEWLINE":
                tokens.append(Token(kind, value, line_num, col_num))
                at_line_start = True
                current_indent = 0
                line_start = mo.end()
                line_num += 1
                continue

            # 2. Manejo de indentación al inicio de la línea
            if at_line_start:
                if kind == "SKIP":
                    # Contamos los espacios (asumiendo 1 tab = 4 espacios)
                    current_indent += len(value.replace("\t", "    "))
                    continue
                elif kind == "COMMENT":
                    # Los comentarios no afectan la indentación ni emiten tokens
                    continue
                else:
                    # Llegamos al primer token real de la línea, evaluamos la indentación
                    if current_indent > indent_stack[-1]:
                        indent_stack.append(current_indent)
                        tokens.append(Token("INDENT", "", line_num, 1))
                    elif current_indent < indent_stack[-1]:
                        while current_indent < indent_stack[-1]:
                            indent_stack.pop()
                            tokens.append(Token("DEDENT", "", line_num, 1))
                        # Si al sacar elementos no coincide exactamente, hay un error de indentación
                        if current_indent != indent_stack[-1]:
                            errors.append(
                                LexicalError(
                                    "IndentationError",
                                    "Nivel de indentación inconsistente",
                                    line_num,
                                    1,
                                )
                            )

                    at_line_start = (
                        False  # Apagamos la bandera para el resto de la línea
                    )

            # 3. Procesamiento normal de tokens (si no estamos al inicio o ya pasamos la indentación)
            if kind == "SKIP" or kind == "COMMENT":
                continue

            elif kind == "ID":
                # Regla de Preferencia de Palabra Reservada
                kind = self.KEYWORD_MAP.get(value, "ID")
                tokens.append(Token(kind, value, line_num, col_num))

            elif kind == "MISMATCH":
                errors.append(
                    LexicalError("Carácter no reconocido", value, line_num, col_num)
                )

            else:
                # Cualquier otro token válido (números, operadores, strings, delimitadores)
                tokens.append(Token(kind, value, line_num, col_num))

        # 4. Al finalizar el código, debemos emitir DEDENTs restantes si la pila no está vacía
        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token("DEDENT", "", line_num, 1))

        return tokens, errors
