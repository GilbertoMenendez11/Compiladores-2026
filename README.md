# Compiladores-2026 — Compilador de subconjunto de Python a MIPS32

Compilador completo de cuatro fases para un subconjunto de Python basado en
indentación, con generación de código intermedio (cuádruplos) y ensamblador
MIPS32 ejecutable en el simulador MARS 4.5.

## Arquitectura del proyecto

- `lexer.py`: **Fase 1 (Análisis léxico)** — tokenización con pila de
  indentación (`NEWLINE`, `INDENT`, `DEDENT`) y reporte de errores léxicos.
- `parser.py`: **Fase 2 (Análisis sintáctico)** — analizador descendente
  recursivo, construcción del AST y recuperación de errores en modo pánico.
- `semantico.py`: **Fase 3 (Análisis semántico)** — tabla de símbolos con
  ámbitos de función/global, inferencia y validación de tipos, y decoración
  del AST con `.type`.
- `intermedio.py`: **Fase 4A (Código intermedio)** — generación de código de
  tres direcciones (cuádruplos) y conversiones implícitas `int -> float` (`itof`).
- `mips.py`: **Fase 4B (Código objeto)** — traducción de cuádruplos a
  ensamblador MIPS32 (`.asm`) con soporte para enteros, flotantes (`double`),
  cadenas (`__concat`, `__strequal`), `imprimir`/`print` y errores de ejecución.
- `main.py`: orquestador de las cuatro fases y generación del archivo `.asm`.
- `tests/`: casos de prueba léxicos, sintácticos, semánticos y de ejecución.

## Requisitos

- Python 3.10 o superior.
- Java (JRE/JDK) y `Mars4_5.jar` en la raíz del proyecto para ejecutar los
  archivos `.asm` generados (descarga: https://github.com/dpetersanderson/MARS/releases).

## Ejecución

Desde la carpeta raíz del proyecto:

```bash
# Compilar un archivo fuente (genera un .asm en la misma carpeta)
python main.py tests/caso_mips_completo.txt

# Compilar mostrando también la tabla de cuádruplos
python main.py tests/caso_mips_completo.txt --cuadruplos

# Ejecutar el código MIPS32 generado en MARS 4.5
java -jar Mars4_5.jar nc tests/caso_mips_completo.asm