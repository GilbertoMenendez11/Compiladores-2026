# Gramática del Lenguaje — Compiladores-2026

El lenguaje implementado es un subconjunto imperativo con sintaxis inspirada en Python y bloques delimitados por indentación (`INDENT` / `DEDENT`)[cite: 2]. El analizador sintáctico (`parser.py`) es descendente recursivo con recuperación de errores en modo pánico.

## 1. Convenciones Léxicas y de Bloques

- **Bloques (`block`):** Se abren tras `:` y `NEWLINE` mediante un token `INDENT`, contienen una o más sentencias y se cierran con `DEDENT`.
- **Fin de sentencia:** `NEWLINE`, o bien `DEDENT` / `EOF` al cierre de un bloque o archivo.
- **Identificadores y literales:** `ID` (`[a-zA-Z_][a-zA-Z0-9_]*`), `INT_LITERAL` (`Entero`), `FLOAT_LITERAL` (`Flotante`) y `STRING_LITERAL` (`Cadena`).
- **Operadores y palabras reservadas:** El lexer reconoce palabras como `def`, `if`, `elif`, `else`, `while`, `for`, `return`, `True`, `False`, `None`, operadores lógicos (`and`, `or`, `not`, `is`, `in`), relacionales, de asignación y aritméticos (`+`, `-`, `*`, `/`, `%`, `//`, `**`).

## 2. Reglas Sintácticas (EBNF)

```ebnf
programa          ::= { NEWLINE | sentencia } EOF

sentencia         ::= declaracion_funcion
                    | sentencia_if
                    | sentencia_while
                    | sentencia_return
                    | sentencia_expresion

declaracion_funcion
                  ::= "def" ID "(" [ parametros ] ")" ":" bloque

parametros        ::= ID { "," ID }

sentencia_if      ::= "if" expresion ":" bloque
                      { "elif" expresion ":" bloque }
                      [ "else" ":" bloque ]

sentencia_while   ::= "while" expresion ":" bloque

sentencia_return  ::= "return" [ expresion ] ( NEWLINE | DEDENT | EOF )

sentencia_expresion
                  ::= expresion ( NEWLINE | DEDENT | EOF )

bloque            ::= NEWLINE INDENT { NEWLINE | sentencia } DEDENT

expresion         ::= asignacion

asignacion        ::= igualdad [ "=" asignacion ]

igualdad          ::= relacional { ( "==" | "!=" ) relacional }

relacional        ::= aditiva { ( "<" | "<=" | ">" | ">=" ) aditiva }

aditiva           ::= multiplicativa { ( "+" | "-" ) multiplicativa }

multiplicativa    ::= unaria { ( "*" | "/" | "%" ) unaria }

unaria            ::= ( "not" | "-" ) unaria
                    | primaria

primaria          ::= INT_LITERAL
                    | FLOAT_LITERAL
                    | STRING_LITERAL
                    | ID [ "(" [ argumentos ] ")" ]
                    | "(" expresion ")"

argumentos        ::= expresion { "," expresion }
```

## 3. Precedencia de Operadores (de menor a mayor)

1. **Asignación:** `=` (asociativa a la derecha; el lado izquierdo debe ser una variable).
2. **Igualdad:** `==`, `!=` (asociativa a la izquierda).
3. **Relacionales:** `<`, `<=`, `>`, `>=` (asociativa a la izquierda).
4. **Aditivos:** `+`, `-` (asociativa a la izquierda).
5. **Multiplicativos:** `*`, `/`, `%` (asociativa a la izquierda).
6. **Unarios:** `not`, `-` (prefijos).
7. **Primarios:** literales, variables, llamadas a función `id(...)` y expresiones agrupadas `(...)`.

## 4. Notas de Diseño y Alcance Actual

- **Tipado dinámico:** Las variables y parámetros no llevan declaración de tipo explícita en la sintaxis; los tipos (`int`, `float`, `string`, `void` o inferidos) se resuelven y verifican en el análisis semántico (`semantico.py`) y en la generación de código intermedio / MIPS32 (`intermedio.py`, `mips.py`)[cite: 2].
- **Alcance de sentencias:** Aunque el lexer tokeniza `for` e `in`, la gramática actual de `statement()` en `parser.py` implementa `def`, `if`/`elif`/`else`, `while`, `return` y sentencias de expresión. Las cláusulas `elif` o `else` sin un `if` previo generan error sintáctico.
