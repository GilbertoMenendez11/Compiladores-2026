"""
MÓDULO: intermedio.py
PROYECTO FINAL: COMPILADORES - FASE 4 (PARTE A)

Generador de Código Intermedio: recorre el AST decorado por la Fase 3 (cada
expresión tiene el atributo .type) y produce Código de Tres Direcciones,
representado internamente como una lista de Cuádruplos (op, arg1, arg2, result).
"""

from typing import NamedTuple

from parser import ASTNode

# ==============================================================================
# 1. ESTRUCTURAS DE DATOS
# ==============================================================================


class Quad(NamedTuple):
    """Cuádruplo: una instrucción de código de tres direcciones."""

    op: str
    arg1: str | None = None
    arg2: str | None = None
    result: str | None = None

    def __str__(self) -> str:
        op, a1, a2, r = self
        if op == "=":
            return f"{r} = {a1}"
        if op in BINARY_OPS:
            return f"{r} = {a1} {op} {a2}"
        if op == "neg":
            return f"{r} = -{a1}"
        if op == "not":
            return f"{r} = not {a1}"
        if op == "itof":
            return f"{r} = (float) {a1}"
        if op == "label":
            return f"{r}:"
        if op == "goto":
            return f"goto {r}"
        if op == "if_false":
            return f"if_false {a1} goto {r}"
        if op == "param":
            return f"param {a1}"
        if op == "call":
            return f"{r} = call {a1}, {a2}" if r else f"call {a1}, {a2}"
        if op == "return":
            return f"return {a1}" if a1 is not None else "return"
        if op == "func":
            return f"func {a1}({a2 or ''}):"
        return op  # end_func, halt


BINARY_OPS = {"+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!="}
ARITHMETIC_OPS = {"+", "-", "*", "/", "%"}
DEFAULTS = {"int": "0", "float": "0.0", "string": '""'}
BUILTINS = {"imprimir", "print"}


# ==============================================================================
# 2. GENERADOR
# ==============================================================================


class IntermediateCodeGenerator:

    def __init__(self):
        self.code: list[Quad] = []
        self.temp_count = 0
        self.label_count = 0
        self.scopes: list[dict[str, str]] = [{}]  # nombre fuente -> nombre en el código
        self.rename_count: dict[str, int] = {}
        self.global_names = set()
        self.functions: dict[str, ASTNode] = {}
        self.function_list: list[ASTNode] = []
        self.current_return_type: str | None = None
        # Tipo de cada variable y temporal, por función ('' = código global).
        self.current_function = ""
        self.types: dict[str, dict[str, str]] = {"": {}}
        self.return_types: dict[str, str] = {}

    # ---------- utilidades ----------
    @staticmethod
    def concrete_type(type_: str | None) -> str:
        """Convierte tipos dinámicos ('any') a un tipo concreto para MIPS."""
        if type_ in (None, "any", "error"):
            return "int"
        return type_

    @staticmethod
    def normalize_string(raw: str) -> str:
        """Asegura comillas dobles para la directiva .asciiz de MARS."""
        if raw.startswith("'") and raw.endswith("'"):
            inner = raw[1:-1].replace('"', '\\"')
            return f'"{inner}"'
        return raw

    def emit(self, op, arg1=None, arg2=None, result=None):
        self.code.append(Quad(op, arg1, arg2, result))

    def new_temp(self, type_: str) -> str:
        self.temp_count += 1
        name = f"t{self.temp_count}"
        self.types[self.current_function][name] = self.concrete_type(type_)
        return name

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    def declare(self, name: str, type_: str) -> str:
        """Da a cada variable un nombre único cuando oculta a otra (limite -> limite.1)."""
        visible = any(name in s for s in self.scopes) or (
            len(self.scopes) > 1 and name in self.global_names
        )
        if visible:
            self.rename_count[name] = self.rename_count.get(name, 0) + 1
            ir_name = f"{name}.{self.rename_count[name]}"
        else:
            ir_name = name
        self.scopes[-1][name] = ir_name
        self.types[self.current_function][ir_name] = self.concrete_type(type_)
        return ir_name

    def resolve(self, name: str) -> str:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return name

    def operand_type(self, op: str) -> str:
        """Determina el tipo concreto de un literal, variable o temporal."""
        if op.startswith('"'):
            return "string"
        if op[0].isdigit():
            return "float" if "." in op else "int"
        if op in self.types[self.current_function]:
            return self.types[self.current_function][op]
        return self.types[""].get(op, "int")

    def convert(self, operand: str, from_type: str, to_type: str) -> str:
        """Inserta la conversión implícita int -> float que validó la Fase 3."""
        if from_type == "int" and to_type == "float":
            t = self.new_temp("float")
            self.emit("itof", operand, None, t)
            return t
        return operand

    def _collect_functions(self, node: ASTNode):
        """Recolecta funciones globales y anidadas para emitirlas como bloques separados."""
        for child in node.children:
            if child.kind == "Funcion":
                name = child.value.split()[-1]
                self.functions[name] = child
                self.function_list.append(child)
                self.return_types[name] = self.concrete_type(
                    getattr(child, "type", None)
                )
            self._collect_functions(child)

    def _collect_globals(self, ast: ASTNode):
        """Identifica nombres asignados en el ámbito global."""
        for n in ast.children:
            if (
                n.kind == "SentenciaExpresion"
                and n.children
                and n.children[0].kind == "Asignacion"
            ):
                self.global_names.add(n.children[0].value)
            elif n.kind == "Asignacion":
                self.global_names.add(n.value)

    # ---------- programa ----------
    def generate(self, ast: ASTNode) -> list[Quad]:
        """
        Estructura del código generado:
          1. Código global (variables globales y sentencias fuera de funciones)
          2. call main, 0  (si existe main)  y  halt
          3. Cada función: func nombre(params): ... end_func
        """
        self._collect_globals(ast)
        self._collect_functions(ast)

        for n in ast.children:
            if n.kind != "Funcion":
                self.statement(n)
        called_main = any(q.op == "call" and q.arg1 == "main" for q in self.code)
        if "main" in self.functions and not called_main:
            self.emit("call", "main", "0")
        self.emit("halt")
        for f in self.function_list:
            self.function(f)
        return self.code

    def function(self, node: ASTNode):
        name = node.value.split()[-1]
        params_node, body = node.children
        ret_type = self.return_types.get(
            name, self.concrete_type(getattr(node, "type", None))
        )

        prev_func = self.current_function
        prev_ret = self.current_return_type

        self.current_function = name
        self.current_return_type = ret_type
        self.types[name] = {}
        self.return_types[name] = ret_type
        self.scopes.append({})

        param_ir_names: list[str] = []
        for param in params_node.children:
            p_type = self.concrete_type(getattr(param, "type", None))
            param_ir_names.append(self.declare(param.value, p_type))

        self.emit("func", name, ", ".join(param_ir_names))
        self.statement(body)
        self.emit("end_func")

        self.scopes.pop()
        self.current_function = prev_func
        self.current_return_type = prev_ret

    # ---------- sentencias ----------
    def statement(self, node: ASTNode):
        method = getattr(self, f"stmt_{node.kind}", None)
        if method is None:
            raise NotImplementedError(f"TODO: stmt_{node.kind}")
        method(node)

    def stmt_Funcion(self, node: ASTNode):
        # Las funciones anidadas ya fueron registradas y se emiten fuera del cuerpo.
        pass

    def stmt_SentenciaExpresion(self, node: ASTNode):
        if not node.children:
            return
        expr_node = node.children[0]
        if expr_node.kind == "Llamada":
            self.call(expr_node, want_result=False)
        else:
            self.expr(expr_node)

    def stmt_SentenciaVacia(self, node: ASTNode):
        pass

    def stmt_Bloque(self, node: ASTNode):
        # En Python los bloques if/else/while comparten el ámbito de la función actual.
        for child in node.children:
            self.statement(child)

    def stmt_If(self, node: ASTNode):
        cond_node = node.children[0].children[0]
        then_block = node.children[1].children[0]
        cond = self.expr(cond_node)

        if len(node.children) == 3:
            else_block = node.children[2].children[0]
            lbl_else, lbl_end = self.new_label(), self.new_label()
            self.emit("if_false", cond, None, lbl_else)
            self.statement(then_block)
            self.emit("goto", None, None, lbl_end)
            self.emit("label", None, None, lbl_else)
            self.statement(else_block)
            self.emit("label", None, None, lbl_end)
        else:
            lbl_end = self.new_label()
            self.emit("if_false", cond, None, lbl_end)
            self.statement(then_block)
            self.emit("label", None, None, lbl_end)

    def stmt_While(self, node: ASTNode):
        start, end = self.new_label(), self.new_label()
        self.emit("label", None, None, start)
        cond_node = (
            node.children[0].children[0]
            if node.children[0].kind == "Condicion"
            else node.children[0]
        )
        cond = self.expr(cond_node)
        self.emit("if_false", cond, None, end)
        self.statement(node.children[1])
        self.emit("goto", None, None, start)
        self.emit("label", None, None, end)

    def stmt_Return(self, node: ASTNode):
        if node.children:
            val = self.expr(node.children[0])
            val_type = self.operand_type(val)
            if self.current_return_type and self.current_return_type != "void":
                val = self.convert(val, val_type, self.current_return_type)
            self.emit("return", val)
        else:
            self.emit("return")

    # ---------- expresiones ----------
    def expr(self, node: ASTNode) -> str:
        kind = node.kind

        if kind == "Entero":
            return node.value
        if kind == "Flotante":
            return node.value
        if kind == "Cadena":
            return self.normalize_string(node.value)
        if kind in ("Variable", "Identificador"):
            return self.resolve(node.value)

        if kind == "Asignacion":
            val = self.expr(node.children[0])
            val_type = self.operand_type(val)
            if node.value in self.scopes[-1]:
                target = self.scopes[-1][node.value]
                target_type = self.types[self.current_function][target]
                val = self.convert(val, val_type, target_type)
            else:
                declared_type = getattr(node, "type", None)
                target_type = (
                    val_type
                    if declared_type in (None, "any", "error")
                    else declared_type
                )
                val = self.convert(val, val_type, target_type)
                target = self.declare(node.value, target_type)
            self.emit("=", val, None, target)
            return target

        if kind == "OpUnaria":
            operand = self.expr(node.children[0])
            op_type = self.operand_type(operand)
            if node.value == "-":
                t = self.new_temp(op_type)
                self.emit("neg", operand, None, t)
                return t
            if node.value == "not":
                t = self.new_temp("int")
                self.emit("not", operand, None, t)
                return t
            raise NotImplementedError(f"Operador unario no soportado: {node.value}")

        if kind == "OpBinaria":
            left = self.expr(node.children[0])
            right = self.expr(node.children[1])
            lt = self.operand_type(left)
            rt = self.operand_type(right)
            op = node.value

            if op in ARITHMETIC_OPS:
                if op == "+" and lt == "string" and rt == "string":
                    res_type = "string"
                elif op == "/" or lt == "float" or rt == "float":
                    left = self.convert(left, lt, "float")
                    right = self.convert(right, rt, "float")
                    res_type = "float"
                else:
                    res_type = "int"
            else:
                if lt == "float" or rt == "float":
                    left = self.convert(left, lt, "float")
                    right = self.convert(right, rt, "float")
                res_type = "int"

            t = self.new_temp(res_type)
            self.emit(op, left, right, t)
            return t

        if kind == "Llamada":
            return self.call(node, want_result=True)

        raise NotImplementedError(f"Expresión no soportada en intermedio: {kind}")

    def call(self, node: ASTNode, want_result: bool) -> str | None:
        func_name = node.value
        func_node = self.functions.get(func_name)
        param_types: list[str] = []
        if func_node is not None:
            params_node = func_node.children[0]
            param_types = [
                self.concrete_type(getattr(p, "type", None))
                for p in params_node.children
            ]

        # Primero se evalúan todos los argumentos antes de emitir los 'param'.
        evaluated: list[str] = []
        for i, arg_node in enumerate(node.children):
            op = self.expr(arg_node)
            op_type = self.operand_type(op)
            if i < len(param_types):
                op = self.convert(op, op_type, param_types[i])
            evaluated.append(op)

        for op in evaluated:
            self.emit("param", op)

        ret_type = (
            "void"
            if func_name in BUILTINS
            else self.return_types.get(
                func_name, self.concrete_type(getattr(node, "type", None))
            )
        )
        if want_result and ret_type != "void":
            t = self.new_temp(ret_type)
            self.emit("call", func_name, str(len(evaluated)), t)
            return t

        self.emit("call", func_name, str(len(evaluated)))
        return None


def format_code(code: list[Quad]) -> str:
    """Código de tres direcciones numerado; el cuerpo de las funciones va con sangría."""
    lines, inside = [], False
    for i, q in enumerate(code):
        if q.op == "func":
            inside = True
        indent = "" if q.op in ("func", "end_func", "label") or not inside else "    "
        lines.append(f"{i:>4}: {indent}{q}")
        if q.op == "end_func":
            inside = False
    return "\n".join(lines)


def format_quads(code: list[Quad]) -> str:
    """Tabla de cuádruplos: # | op | arg1 | arg2 | resultado."""
    rows = [
        (str(i), q.op, q.arg1 or "", q.arg2 or "", q.result or "")
        for i, q in enumerate(code)
    ]
    headers = ("#", "op", "arg1", "arg2", "resultado")
    widths = [max([len(h)] + [len(r[c]) for r in rows]) for c, h in enumerate(headers)]
    fmt = lambda r: " | ".join(v.ljust(w) for v, w in zip(r, widths)).rstrip()
    return "\n".join(
        [fmt(headers), "-+-".join("-" * w for w in widths)] + [fmt(r) for r in rows]
    )
