# Compiladores-2026 — Fase 3: Análisis semántico

Esta versión integra la Fase 3 al proyecto existente, conservando la sintaxis
estilo Python basada en indentación.

## Archivos principales

- `lexer.py`: análisis léxico.
- `parser.py`: análisis sintáctico y construcción del AST.
- `semantico.py`: tabla de símbolos, ámbitos, reglas de tipos y validaciones.
- `main.py`: ejecución de las tres fases.
- `tests/`: casos léxicos, sintácticos y semánticos.

## Ejecutar

Desde la carpeta raíz del proyecto:

```bash
python main.py tests/caso_valido.txt
python main.py tests/caso_error.txt
python main.py tests/caso_semantico_valido.txt
python main.py tests/caso_semantico_error.txt
```

En Windows también puede utilizarse `py` en lugar de `python`.

## Reglas semánticas implementadas

- Tabla de símbolos con búsqueda desde el ámbito actual hacia los ámbitos
  exteriores.
- Registro de funciones antes de analizar los cuerpos, para permitir llamadas
  recursivas y llamadas a funciones definidas más adelante.
- Detección de variables no declaradas, redeclaración de funciones y uso de
  funciones como si fueran variables.
- Inferencia del tipo de una variable a partir de su primera asignación.
- Compatibilidad de asignación: mismo tipo e int hacia float.
- Operaciones aritméticas numéricas, concatenación de cadenas con `+` y
  comparaciones.
- Validación de condiciones de `if` y `while`.
- Validación de existencia de funciones, cantidad de argumentos y uso de
  resultados `void`.
- Validación de `return` dentro de funciones y consistencia de los tipos
  retornados.
- Función predefinida `imprimir(...)`, de tipo `void` y con argumentos variables.

## Consideraciones de esta gramática

El parser actual no declara tipos en parámetros ni en variables. Por eso los
parámetros se registran como `any` y las variables infieren su tipo al asignarse.
El tipo `any` representa información que no puede determinarse estáticamente
con la gramática actual; se permite en operaciones compatibles para evitar
rechazar funciones cuyo resultado depende de sus argumentos.

La plantilla recibida menciona `sintactico.py` y nodos como `Declaracion` e
`Identificador`, pero el proyecto utiliza `parser.py` y nodos como `Variable`,
`Asignacion`, `Funcion`, `Bloque`, `While` y `OpBinaria`. El analizador semántico
se adaptó a estos nombres y estructuras reales. El parser actual tampoco genera
nodos `For`, por lo que ese método no forma parte de esta integración.

Las reglas de este README son la implementación de trabajo basada en la
estructura y los tipos disponibles en el proyecto. Si el enunciado completo de
la Fase 3 establece reglas distintas en su apartado 2.4, deben contrastarse y
ajustarse a ese apartado.
