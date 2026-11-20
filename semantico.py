"""Analizador semantico para el AST generado por parser.py.

Fase 3 del proyecto Compiladores-2026.

Decora cada nodo de expresion y funcion del AST con el atributo `.type`
para su consumo en la Fase 4 (generacion de codigo intermedio y MIPS).
"""

from typing import NamedTuple

from parser import ASTNode

# ---------------------------------------------------------------------------
# 1. ESTRUCTURAS DE DATOS
# ---------------------------------------------------------------------------


class Symbol(NamedTuple):
    """Entrada de la tabla de simbolos."""

    name: str
    category: str  # variable, parametro o funcion
    type: str  # tipo de dato o tipo de retorno
    scope: str
    line: int
    params: tuple[str, ...] = ()
    variadic: bool = False

    def type_label(self) -> str:
        if self.category == "funcion":
            return f"{self.type}({', '.join(self.params)})"
        return self.type


class SemanticError(NamedTuple):
    message: str
    line: int
    column: int


class SymbolTable:
    """Pila de ambitos. Cada ambito es un diccionario nombre -> Symbol."""

    def __init__(self):
        self.scopes: list[tuple[str, dict[str, Symbol]]] = [("global", {})]
        self.all_symbols: list[Symbol] = []

    @property
    def current_scope(self) -> str:
        return self.scopes[-1][0]

    def open_scope(self, name: str):
        self.scopes.append((name, {}))

    def close_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare(self, symbol: Symbol) -> Symbol | None:
        """Declara en el ambito actual; retorna el simbolo previo si se repite."""
        current = self.scopes[-1][1]
        previous = current.get(symbol.name)
        if previous is not None:
            return previous
        current[symbol.name] = symbol
        if symbol.scope != "-":
            self.all_symbols.append(symbol)
        return None

    def lookup(self, name: str) -> Symbol | None:
        """Busca desde el ambito mas interno hasta el global."""
        for _, scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_local(self, name: str) -> Symbol | None:
        """Busca unicamente en el ambito actual."""
        return self.scopes[-1][1].get(name)

    def replace(self, old: Symbol, new: Symbol):
        """Actualiza un simbolo en su ambito y en el historial de impresion."""
        for _, scope in self.scopes:
            if scope.get(old.name) == old:
                scope[old.name] = new
                break
        for index, symbol in enumerate(self.all_symbols):
            if symbol == old:
                self.all_symbols[index] = new
                break


# ---------------------------------------------------------------------------
# 2. REGLAS DE TIPOS
# ---------------------------------------------------------------------------

ERROR = "error"
NUMERIC = ("int", "float")
ANY = "any"


def assignable(target: str, value: str) -> bool:
    """Indica si un valor puede asignarse a una variable del tipo destino."""
    if ERROR in (target, value) or ANY in (target, value):
        return True
    if target == value:
        return True
    return target == "float" and value == "int"


def binary_result(op: str, left: str, right: str) -> str:
    """Calcula el tipo resultante de una operacion binaria."""
    if ERROR in (left, right) or "void" in (left, right):
        return ERROR

    if op in ("==", "!="):
        if (
            ANY in (left, right)
            or left == right
            or (left in NUMERIC and right in NUMERIC)
        ):
            return "int"
        return ERROR

    if op in ("<", "<=", ">", ">="):
        if ANY in (left, right) or (left in NUMERIC and right in NUMERIC):
            return "int"
        return ERROR

    if op == "+" and (left == "string" or right == "string"):
        if left in ("string", ANY) and right in ("string", ANY):
            return "string"
        return ERROR

    if op == "/" and left in (*NUMERIC, ANY) and right in (*NUMERIC, ANY):
        return "float"

    if op == "%":
        if left in ("int", ANY) and right in ("int", ANY):
            return "int"
        return ERROR

    if left == ANY or right == ANY:
        if op in ("+", "-", "*") and "float" in (left, right):
            return "float"
        return ANY

    if left in NUMERIC and right in NUMERIC:
        if op in ("+", "-", "*"):
            return "float" if "float" in (left, right) else "int"

    return ERROR


# ---------------------------------------------------------------------------
# 3. ANALIZADOR SEMANTICO
# ---------------------------------------------------------------------------


class SemanticAnalyzer:
    """Recorre el AST y verifica nombres, ambitos, tipos y llamadas."""

    def __init__(self):
        self.table = SymbolTable()
        self.errors: list[SemanticError] = []
        self.current_function: Symbol | None = None
        self._return_stack: list[list[str]] = []
        self._predeclared: dict[int, bool] = {}

        # Funciones predefinidas: aceptan cualquier cantidad y tipo de argumentos.
        self.table.declare(Symbol("imprimir", "funcion", "void", "-", 0, variadic=True))
        self.table.declare(Symbol("print", "funcion", "void", "-", 0, variadic=True))

    def error(self, message: str, node: ASTNode):
        self.errors.append(SemanticError(message, node.line, node.column))

    def analyze(self, ast: ASTNode) -> tuple[SymbolTable, list[SemanticError]]:
        self.visit(ast)
        return self.table, self.errors

    def visit(self, node: ASTNode):
        method = getattr(self, f"visit_{node.kind}", None)
        if method is None:
            raise NotImplementedError(f"Falta implementar visit_{node.kind}")
        result = method(node)
        if isinstance(result, str):
            node.type = result
        return result

    def visit_children(self, node: ASTNode):
        for child in node.children:
            self.visit(child)

    def visit_Programa(self, node: ASTNode):
        for child in node.children:
            if child.kind == "Funcion":
                self._register_function(child, global_scope=True)
        self.visit_children(node)

    # ----- Tabla de simbolos y funciones -----

    def _register_function(self, node: ASTNode, global_scope: bool = False):
        params_node = node.children[0] if node.children else ASTNode("Parametros")
        param_names = [p.value for p in params_node.children]

        symbol = Symbol(
            node.value,
            "funcion",
            ANY,
            "global" if global_scope else self.table.current_scope,
            node.line,
            tuple(ANY for _ in param_names),
        )
        previous = self.table.declare(symbol)
        self._predeclared[id(node)] = previous is None
        if previous is not None:
            self.error(
                f"La funcion '{node.value}' ya fue declarada en el ambito '{self.table.current_scope}'",
                node,
            )

    def visit_Funcion(self, node: ASTNode):
        params_node, body = node.children
        symbol = self.table.lookup(node.value)
        if id(node) not in self._predeclared:
            self._register_function(node)
            symbol = self.table.lookup(node.value)
        if not self._predeclared.get(id(node), False):
            return
        if symbol is None or symbol.category != "funcion":
            return

        previous_function = self.current_function
        self.current_function = symbol
        self._return_stack.append([])

        self.table.open_scope(f"funcion:{node.value}")
        for param in params_node.children:
            param.type = ANY
            parameter = Symbol(
                param.value, "parametro", ANY, self.table.current_scope, param.line
            )
            previous = self.table.declare(parameter)
            if previous is not None:
                self.error(f"El parametro '{param.value}' esta repetido", param)

        self.visit(body)
        return_types = self._return_stack.pop()
        self.table.close_scope()

        return_type = self._infer_return_type(return_types, node)
        node.type = return_type
        if symbol is not None:
            updated = symbol._replace(type=return_type)
            self.table.replace(symbol, updated)
        self.current_function = previous_function

    def _infer_return_type(self, types: list[str], node: ASTNode) -> str:
        if not types:
            return "void"
        has_void = "void" in types
        values = [t for t in types if t != "void" and t != ERROR]
        if has_void and values:
            self.error(
                f"La funcion '{node.value}' mezcla return con valor y return sin valor",
                node,
            )
            return ERROR
        if not values:
            return ERROR if ERROR in types else "void"
        if ANY in values:
            return ANY
        unique = set(values)
        if unique.issubset(set(NUMERIC)):
            return "float" if "float" in unique else "int"
        if len(unique) == 1:
            return values[0]
        self.error(
            f"La funcion '{node.value}' retorna tipos incompatibles: {', '.join(sorted(unique))}",
            node,
        )
        return ERROR

    # ----- Ambitos y sentencias -----

    def visit_Bloque(self, node: ASTNode):
        self.visit_children(node)

    def visit_If(self, node: ASTNode):
        condition = node.children[0].children[0]
        self.check_condition(condition, "if")
        for branch in node.children[1:]:
            self.visit(branch.children[0])

    def check_condition(self, expr: ASTNode, keyword: str):
        result_type = self.visit(expr)
        if result_type not in NUMERIC and result_type not in (ANY, ERROR):
            self.error(
                f"La condicion del '{keyword}' debe ser numerica, se encontro '{result_type}'",
                expr,
            )

    def visit_While(self, node: ASTNode):
        condition, body = node.children
        self.check_condition(condition, "while")
        self.visit(body)

    def visit_SentenciaExpresion(self, node: ASTNode):
        if node.children:
            self.visit(node.children[0])

    def visit_Return(self, node: ASTNode):
        if self.current_function is None:
            self.error("'return' solo puede utilizarse dentro de una funcion", node)
            if node.children:
                self.visit(node.children[0])
            return
        result_type = self.visit(node.children[0]) if node.children else "void"
        if node.children and result_type == "void":
            self.error("No se puede retornar el resultado de una funcion void", node)
        self._return_stack[-1].append(result_type)

    def visit_Asignacion(self, node: ASTNode):
        value_type = self.visit(node.children[0])
        if value_type == "void":
            self.error(
                f"No se puede asignar a '{node.value}' el resultado de una funcion void",
                node,
            )
            return ERROR

        existing = self.table.lookup_local(node.value)

        if existing is not None and existing.category == "funcion":
            self.error(
                f"No se puede asignar un valor al nombre de funcion '{node.value}'",
                node,
            )
            return ERROR

        if existing is None:
            symbol = Symbol(
                node.value, "variable", value_type, self.table.current_scope, node.line
            )
            self.table.declare(symbol)
            return value_type

        if not assignable(existing.type, value_type):
            self.error(
                f"No se puede asignar un valor de tipo '{value_type}' a la variable '{node.value}' de tipo '{existing.type}'",
                node,
            )
            return ERROR
        return existing.type

    def visit_Variable(self, node: ASTNode):
        symbol = self.table.lookup(node.value)
        if symbol is None:
            self.error(f"La variable '{node.value}' no ha sido declarada", node)
            return ERROR
        if symbol.category == "funcion":
            self.error(
                f"'{node.value}' es una funcion; debe invocarse con parentesis", node
            )
            return ERROR
        return symbol.type

    # ----- Expresiones -----

    def visit_Entero(self, node: ASTNode):
        return "int"

    def visit_Flotante(self, node: ASTNode):
        return "float"

    def visit_Cadena(self, node: ASTNode):
        return "string"

    def visit_OpBinaria(self, node: ASTNode):
        left_type = self.visit(node.children[0])
        right_type = self.visit(node.children[1])
        result = binary_result(node.value, left_type, right_type)
        if result == ERROR and left_type != ERROR and right_type != ERROR:
            self.error(
                f"Operacion '{node.value}' no valida entre tipos '{left_type}' y '{right_type}'",
                node,
            )
        return result

    def visit_OpUnaria(self, node: ASTNode):
        operand_type = self.visit(node.children[0])
        if operand_type == ERROR:
            return ERROR
        if node.value == "-" and (operand_type in NUMERIC or operand_type == ANY):
            return operand_type
        if node.value == "not" and (operand_type in NUMERIC or operand_type == ANY):
            return "int"
        self.error(
            f"El operador unario '{node.value}' no admite el tipo '{operand_type}'",
            node,
        )
        return ERROR

    def visit_Llamada(self, node: ASTNode):
        argument_types = [self.visit(argument) for argument in node.children]
        for index, argument_type in enumerate(argument_types, start=1):
            if argument_type == "void":
                self.error(
                    f"El argumento {index} de '{node.value}' no puede ser el resultado de una funcion void",
                    node,
                )

        symbol = self.table.lookup(node.value)
        if symbol is None:
            self.error(f"La funcion '{node.value}' no ha sido declarada", node)
            return ERROR
        if symbol.category != "funcion":
            self.error(f"'{node.value}' no es una funcion", node)
            return ERROR

        if not symbol.variadic and len(argument_types) != len(symbol.params):
            self.error(
                f"La funcion '{node.value}' espera {len(symbol.params)} argumento(s), pero recibio {len(argument_types)}",
                node,
            )
        elif not symbol.variadic:
            for index, (expected, actual) in enumerate(
                zip(symbol.params, argument_types), start=1
            ):
                if not assignable(expected, actual):
                    self.error(
                        f"El argumento {index} de '{node.value}' debe ser '{expected}', se recibio '{actual}'",
                        node,
                    )
        return symbol.type


def format_table(table: SymbolTable) -> str:
    """Devuelve la tabla de simbolos en formato tabular."""
    headers = ("Nombre", "Categoria", "Tipo", "Ambito", "Linea")
    rows = [
        (s.name, s.category, s.type_label(), s.scope, str(s.line))
        for s in table.all_symbols
    ]
    widths = [
        max([len(header)] + [len(row[i]) for row in rows])
        for i, header in enumerate(headers)
    ]
    widths = [max(width, 6) for width in widths]
    fmt = lambda row: " | ".join(
        cell.ljust(width) for cell, width in zip(row, widths)
    ).rstrip()
    separator = "-+-".join("-" * width for width in widths)
    return "\n".join([fmt(headers), separator] + [fmt(row) for row in rows])
