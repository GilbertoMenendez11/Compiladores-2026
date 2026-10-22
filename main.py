import sys

from lexer import PythonLexer
from parser import Parser


def main():
    if len(sys.argv) != 2:
        print("Uso: python main.py <ruta_archivo>")
        return

    ruta_archivo = sys.argv[1]

    try:
        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            codigo = archivo.read()
    except OSError as error:
        print(f"Error al leer el archivo: {error}")
        return

    print("-----FASE 1: ANÁLISIS LÉXICO-----")

    lexer = PythonLexer(codigo)
    tokens, errores = lexer.tokenize()

    for token in tokens:
        print(
            f"[TOKEN] Tipo: {token.type:15} | "
            f"Lexema: '{token.value}' | "
            f"Posición: [Línea {token.line}, Col {token.column}]"
        )

    for error in errores:
        print(
            f"[ERROR LÉXICO] {error.message}: '{error.char}' "
            f"en [Línea {error.line}, Col {error.column}]"
        )

    if errores:
        return

    print("\n-----FASE 2: ANÁLISIS SINTÁCTICO-----")

    try:
        parser = Parser(tokens)
        ast = parser.parse()

        print("AST generado:")
        for nodo in ast:
            print(nodo)
    except SyntaxError as error:
        print(f"Error sintáctico: {error}")


if __name__ == "__main__":
    main()
