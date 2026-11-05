import sys

from lexer import Lexer
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

    lexer = Lexer(codigo)
    tokens, errores = lexer.tokenize()

    for token in tokens:
        print(
            f"[TOKEN] Tipo: {token.type:15} | "
            f"Lexema: '{token.value}' | "
            f"Posición: [Línea {token.line}, Col {token.column}]"
        )

    for error in errores:
        print(
            f"[ERROR LÉXICO] {error.message} '{error.char}' "
            f"en Posición: [Línea {error.line}, Col {error.column}]"
        )

    # Si hay errores léxicos, el programa se detiene aquí y no pasa a la Fase 2
    if errores:
        return

    print("\n-----FASE 2: ANÁLISIS SINTÁCTICO-----")

    # Instanciamos el parser con los tokens obtenidos en la Fase 1
    parser = Parser(tokens)

    # Ejecutamos el análisis sintáctico (ahora devuelve el AST y los errores)
    ast, errores_sintacticos = parser.parse()

    # Evaluamos si el parser reportó errores recuperados (Modo Pánico)
    if errores_sintacticos:
        for error in errores_sintacticos:
            print(
                f"[ERROR SINTÁCTICO] {error.message} "
                f"en Posición: [Línea {error.line}, Col {error.column}]"
            )
        print(f"Errores sintácticos: {len(errores_sintacticos)}")
    else:
        print("Análisis sintáctico completado sin errores.")
        # Imprime el Árbol de Sintaxis Abstracta con el formato de sangría del template
        print(ast.pretty())
        print("Errores sintácticos: 0")
        print("Resultado: COMPILACIÓN EXITOSA")


if __name__ == "__main__":
    main()
