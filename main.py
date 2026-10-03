from lexer import PythonLexer
from parser import Parser


def main():
    codigo = """x = 10 + 5 * 2"""

    print("=== FASE 1: ANÁLISIS LÉXICO ===")

    lexer = PythonLexer(codigo)
    tokens, errores = lexer.tokenize()

    if errores:
        for error in errores:
            print(
                f"[{error.line}:{error.column}] "
                f"Error Léxico: {error.message} -> '{error.char}'"
            )
        return

    for token in tokens:
        print(f"Tipo: {token.type:15} " f"Valor: {token.value}")

    print("\n=== FASE 2: ANÁLISIS SINTÁCTICO ===")

    try:
        parser = Parser(tokens)
        ast = parser.parse()

        print("AST generado:")
        for nodo in ast:
            print(nodo)

    except SyntaxError as error:
        print(f"Error Sintáctico: {error}")


if __name__ == "__main__":
    main()
