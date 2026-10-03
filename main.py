import sys
from lexer import PythonLexer

def main():
    # Código fuente de prueba (luego esto se leerá de un archivo .py real)
    codigo = """
def sumar(a, b):
    if a > 0:
        return a + b
    else:
        return 0
"""
    print("=== INICIANDO FASE 1: ANÁLISIS LÉXICO ===")
    lexer = PythonLexer(codigo)
    tokens, errores = lexer.tokenize()

    if errores:
        print("Se encontraron errores léxicos:")
        for e in errores:
            print(f"[{e.line}:{e.column}] Error: {e.message} -> '{e.char}'")
    else:
        print("Análisis léxico exitoso. Tokens generados:")
        for t in tokens:
            # Filtramos los saltos de línea visualmente para no saturar la consola
            if t.type != 'NEWLINE':
                print(f"Tipo: {t.type:10} | Valor: {t.value:10} | Línea: {t.line}")

if __name__ == "__main__":
    main()