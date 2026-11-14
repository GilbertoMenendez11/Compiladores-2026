"""
MÓDULO: lexer.py
PROYECTO FINAL: COMPILADORES - FASE 1 Análisis Léxico (Con Indentación)
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


class Lexer:
    """
    Analizador Léxico (Scanner).
    Transforma una cadena de código fuente en una lista de Tokens y Errores Léxicos
    incluyendo soporte para NEWLINE, INDENT y DEDENT.
    """

    TOKEN_SPECIFICATION = [  # noqa: RUF012
        ("NEWLINE", r"\n"),
        ("COMMENT_MULTI", r"/\*[\s\S]*?\*/"),
        ("COMMENT_SINGLE", r"//.*"),
        ("COMMENT", r"#.*"),
        ("FLOAT_LITERAL", r"\d+\.\d+"),
        ("INT_LITERAL", r"\d+"),
        ("STRING_LITERAL", r'"[^"\\]*(\\.[^"\\]*)*"|\'[^\'\\]*(\\.[^\'\\]*)*\''),
        ("UNCLOSED_STRING", r'"[^"\n]*|\'[^\'\n]*'),
        ("OP_REL", r"==|!=|<=|>=|<|>"),
        ("OP_ASSIGN", r"\+=|-=|\*=|/=|//=|%=|="),
        ("OP_ARITH", r"\*\*|//|[+\-*/%]"),
        ("DELIM", r"[()\[\]{},:;.@]"),
        ("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("SKIP", r"[ \t]+"),
        ("MISMATCH", r"."),
    ]

    KEYWORD_MAP = {  # noqa: RUF012
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
        "and": "OP_LOGIC",
        "or": "OP_LOGIC",
        "not": "OP_LOGIC",
        "is": "OP_LOGIC",
        "in": "OP_LOGIC",
        "int": "PR_INT",
        "float": "PR_FLOAT",
        "void": "PR_VOID",
        "string": "PR_STRING",
    }

    def __init__(self, code: str):
        self.code = code
        tok_regex = "|".join(
            f"(?P<{pair[0]}>{pair[1]})" for pair in self.TOKEN_SPECIFICATION
        )
        self.regex = re.compile(tok_regex)

    def tokenize(self) -> tuple[list[Token], list[LexicalError]]:
        tokens: list[Token] = []
        errors: list[LexicalError] = []

        line_num = 1
        line_start = 0
        indent_stack = [0]
        at_line_start = True
        pending_indent = 0

        for mo in self.regex.finditer(self.code):
            kind = mo.lastgroup
            value = mo.group()
            position = mo.start()
            col_num = position - line_start + 1

            if at_line_start:
                if kind == "SKIP":
                    pending_indent = len(value.replace('\t', '    '))
                    continue
                elif kind == "NEWLINE":
                    line_start = mo.end()
                    line_num += 1
                    tokens.append(Token("NEWLINE", value, line_num - 1, col_num))
                    continue
                elif kind in ("COMMENT", "COMMENT_SINGLE", "COMMENT_MULTI"):
                    if kind == "COMMENT_MULTI":
                        newlines = value.count("\n")
                        if newlines > 0:
                            line_num += newlines
                            line_start = position + value.rfind("\n") + 1
                    continue
                else:
                    current_indent = indent_stack[-1]
                    if pending_indent > current_indent:
                        indent_stack.append(pending_indent)
                        tokens.append(Token("INDENT", "", line_num, col_num))
                    elif pending_indent < current_indent:
                        while indent_stack[-1] > pending_indent:
                            indent_stack.pop()
                            tokens.append(Token("DEDENT", "", line_num, col_num))
                        if indent_stack[-1] != pending_indent:
                            errors.append(LexicalError("Error de indentación", "", line_num, col_num))
                    at_line_start = False
                    pending_indent = 0

            if kind == "NEWLINE":
                line_start = mo.end()
                line_num += 1
                tokens.append(Token("NEWLINE", value, line_num - 1, col_num))
                at_line_start = True
                pending_indent = 0
                continue

            elif kind == "COMMENT_MULTI":
                newlines = value.count("\n")
                if newlines > 0:
                    line_num += newlines
                    line_start = position + value.rfind("\n") + 1
                continue

            elif kind in ("SKIP", "COMMENT", "COMMENT_SINGLE"):
                continue

            elif kind == "ID":
                kind = self.KEYWORD_MAP.get(value, "ID")
                tokens.append(Token(kind, value, line_num, col_num))

            elif kind == "UNCLOSED_STRING":
                errors.append(
                    LexicalError("Cadena sin cerrar", value, line_num, col_num)
                )

            elif kind == "MISMATCH":
                errors.append(
                    LexicalError("Carácter no reconocido", value, line_num, col_num)
                )

            else:
                tokens.append(Token(kind, value, line_num, col_num))

        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token("DEDENT", "", line_num, 1))

        return tokens, errors