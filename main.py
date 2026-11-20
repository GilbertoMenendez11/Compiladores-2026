import os
import sys

from intermedio import IntermediateCodeGenerator, format_code, format_quads
from lexer import Lexer
from mips import MipsGenerator
from parser import Parser
from semantico import SemanticAnalyzer, format_table


def main():
    args = sys.argv[1:]
    mostrar_cuadruplos = "--cuadruplos" in args
    archivos = [a for a in args if a != "--cuadruplos"]

    if len(archivos) != 1:
        print("Uso: python main.py <ruta_archivo> [--cuadruplos]")
        return

    ruta_archivo = archivos[0]

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

    if errores:
        return

    print("\n-----FASE 2: ANÁLISIS SINTÁCTICO-----")

    parser = Parser(tokens)
    ast, errores_sintacticos = parser.parse()

    if errores_sintacticos:
        for error in errores_sintacticos:
            print(
                f"[ERROR SINTÁCTICO] {error.message} "
                f"en Posición: [Línea {error.line}, Col {error.column}]"
            )
        print(f"Errores sintácticos: {len(errores_sintacticos)}")
        return

    print("Análisis sintáctico completado sin errores.")
    print(ast.pretty())
    print("Errores sintácticos: 0")

    print("\n-----FASE 3: ANÁLISIS SEMÁNTICO-----")
    semantic = SemanticAnalyzer()
    tabla, errores_semanticos = semantic.analyze(ast)

    print("\n-----TABLA DE SÍMBOLOS-----")
    print(format_table(tabla))

    if errores_semanticos:
        for error in errores_semanticos:
            print(
                f"[ERROR SEMÁNTICO] {error.message} "
                f"en Posición: [Línea {error.line}, Col {error.column}]"
            )
        print(f"Errores semánticos: {len(errores_semanticos)}")
        print("Resultado: COMPILACIÓN CON ERRORES SEMÁNTICOS")
        return

    print("Análisis semántico completado sin errores.")
    print("Errores semánticos: 0")

    print("\n-----FASE 4A: CÓDIGO INTERMEDIO-----")
    ir_gen = IntermediateCodeGenerator()
    cuadruplos = ir_gen.generate(ast)
    print(format_code(cuadruplos))

    if mostrar_cuadruplos:
        print("\n-----TABLA DE CUÁDRUPLOS-----")
        print(format_quads(cuadruplos))

    print("\n-----FASE 4B: GENERACIÓN DE CÓDIGO MIPS-----")
    try:
        mips_gen = MipsGenerator(cuadruplos, ir_gen.types, ir_gen.return_types)
        codigo_mips = mips_gen.generate()
    except NotImplementedError as error:
        print(f"[PENDIENTE EN MIPS] {error}")
        return

    ruta_salida = os.path.splitext(ruta_archivo)[0] + ".asm"
    try:
        with open(ruta_salida, "w", encoding="utf-8") as salida:
            salida.write(codigo_mips)
    except OSError as error:
        print(f"Error al escribir el archivo MIPS: {error}")
        return

    print(f"Archivo MIPS generado en: {ruta_salida}")
    print("Resultado: COMPILACIÓN EXITOSA")


if __name__ == "__main__":
    main()