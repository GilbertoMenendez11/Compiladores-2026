"""
MÓDULO: mips.py
PROYECTO FINAL: COMPILADORES - FASE 4 (PARTE B)

Generador de Código Objeto: traduce los cuádruplos de la Fase 4 a ensamblador
MIPS32 que se ejecuta en el simulador MARS 4.5.
"""

from typing import Dict, List

from intermedio import Quad

RUNTIME_ERRORS = {
    '__err_div': "[ERROR DE EJECUCION] Division entre cero",
    '__err_stack': "[ERROR DE EJECUCION] Desbordamiento de pila: mas de 1000 llamadas anidadas",
}
MAX_DEPTH = 1000


def is_literal(op: str) -> bool:
    return op[0] == '"' or op[0].isdigit()


def literal_type(op: str) -> str:
    if op[0] == '"':
        return 'string'
    return 'float' if '.' in op else 'int'


class MipsGenerator:

    def __init__(self, code: List[Quad], types: Dict[str, Dict[str, str]],
                 return_types: Dict[str, str]):
        self.code = code
        self.types = types
        self.return_types = return_types
        self.globals = {n: t for n, t in types[''].items() if not self.is_temp(n)}
        self.data: List[str] = []
        self.text: List[str] = []
        self.strings: Dict[str, str] = {}      # literal -> etiqueta
        self.doubles: Dict[str, str] = {}      # literal -> etiqueta
        self.func = ''                          # función actual ('' = código global)
        self.slots: Dict[str, int] = {}         # nombre -> desplazamiento desde $fp
        self.pending: List[str] = []            # tipos de los 'param' pendientes
        self.counter = 0

    @staticmethod
    def is_temp(name: str) -> bool:
        return name[0] == 't' and name[1:].isdigit()

    def emit(self, line: str):
        self.text.append("    " + line)

    def label(self, name: str):
        self.text.append(f"{name}:")

    def unique(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}{self.counter}"

    # ---------- tipos y ubicaciones ----------
    def type_of(self, op: str) -> str:
        if is_literal(op):
            return literal_type(op)
        return self.types[self.func].get(op) or self.types[''][op]

    def address(self, name: str) -> str:
        """Dirección de memoria de una variable o temporal."""
        if name in self.slots:
            return f"{self.slots[name]}($fp)"
        self.emit(f"la $t9, g_{name}")
        return "0($t9)"

    def string_label(self, literal: str) -> str:
        if literal not in self.strings:
            self.strings[literal] = f"str{len(self.strings) + 1}"
            self.data.append(f"{self.strings[literal]}: .asciiz {literal}")
        return self.strings[literal]

    def double_label(self, literal: str) -> str:
        if literal not in self.doubles:
            self.doubles[literal] = f"dbl{len(self.doubles) + 1}"
            self.data += [".align 3", f"{self.doubles[literal]}: .double {literal}"]
        return self.doubles[literal]

    # ---------- carga y almacenamiento ----------
    def load_word(self, op: str, reg: str):
        """Carga un int o la dirección de un string en un registro entero."""
        if op[0] == '"':
            self.emit(f"la {reg}, {self.string_label(op)}")
        elif op[0].isdigit():
            self.emit(f"li {reg}, {op}")
        else:
            self.emit(f"lw {reg}, {self.address(op)}")

    def load_double(self, op: str, freg: str):
        if is_literal(op):
            self.emit(f"la $t9, {self.double_label(op)}")
            self.emit(f"l.d {freg}, 0($t9)")
        else:
            self.emit(f"l.d {freg}, {self.address(op)}")

    def store_word(self, reg: str, name: str):
        self.emit(f"sw {reg}, {self.address(name)}")

    def store_double(self, freg: str, name: str):
        self.emit(f"s.d {freg}, {self.address(name)}")

    # ---------- estructura del programa ----------
    def generate(self) -> str:
        # Variables globales: 8 bytes cada una, alineadas para los double.
        for name in self.globals:
            self.data += [".align 3", f"g_{name}: .space 8"]
        self.data += [".align 2", "__depth: .word 0"]
        for lbl, msg in RUNTIME_ERRORS.items():
            self.data.append(f"{lbl}_msg: .asciiz \"{msg}\"")

        self.text += [".text", ".globl main", "main:"]
        self.emit("li $t0, -8")
        self.emit("and $sp, $sp, $t0          # alinea la pila a 8 bytes (para los double)")
        self.emit("move $fp, $sp")
        segments = self.split_segments()
        for name, quads in segments:
            self.segment(name, quads)
        self.runtime()
        return "\n".join([".data"] + self.data + [""] + self.text) + "\n"

    def split_segments(self):
        """Separa el código global de cada función."""
        segments, current, name = [], [], ''
        for q in self.code:
            if q.op == 'func':
                segments.append((name, current))
                current, name = [], q.arg1
            current.append(q)
            if q.op == 'end_func':
                segments.append((name, current))
                current, name = [], None
        if current:
            segments.append((name, current))
        return [(n, qs) for n, qs in segments if qs]

    def segment(self, name: str, quads: List[Quad]):
        self.func = name
        self.slots = {}
        local_names = [n for n in self.types[name] if name or self.is_temp(n)]
        params = quads[0].arg2.split(", ") if name and quads[0].arg2 else []
        n = len(params)
        for k, p in enumerate(params):
            self.slots[p] = 16 + 8 * (n - 1 - k)        # los pushea el llamador
        locals_ = [x for x in local_names if x not in self.slots]
        for i, x in enumerate(locals_):
            self.slots[x] = -8 * (i + 1)
        frame_size = 8 * len(locals_)

        for q in quads:
            self.text.append(f"    # {q}")
            if q.op == 'func':
                self.prologue(q.arg1, frame_size)
            elif q.op == 'end_func':
                self.epilogue(name)
            else:
                if not name and frame_size and q is quads[0]:
                    self.emit(f"addi $sp, $sp, -{frame_size}   # temporales del codigo global")
                self.translate(q)

    def prologue(self, name: str, frame_size: int):
        self.label(f"f_{name}")
        self.emit("addi $sp, $sp, -16")
        self.emit("sw $ra, 8($sp)")
        self.emit("sw $fp, 0($sp)")
        self.emit("move $fp, $sp")
        if frame_size:
            self.emit(f"addi $sp, $sp, -{frame_size}")
        self.emit("lw $t0, __depth")
        self.emit("addi $t0, $t0, 1")
        self.emit("sw $t0, __depth")
        self.emit(f"li $t1, {MAX_DEPTH}")
        self.emit("bgt $t0, $t1, __err_stack")

    def epilogue(self, name: str):
        if self.return_types[name] != 'void':
            msg = f"[ERROR DE EJECUCION] La funcion '{name}' termino sin retornar un valor"
            self.data.append(f"__noret_{name}: .asciiz \"{msg}\"")
            self.emit(f"la $a0, __noret_{name}")
            self.emit("j __error")
        self.label(f"f_{name}_ret")
        self.emit("lw $t0, __depth")
        self.emit("addi $t0, $t0, -1")
        self.emit("sw $t0, __depth")
        self.emit("move $sp, $fp")
        self.emit("lw $fp, 0($sp)")
        self.emit("lw $ra, 8($sp)")
        self.emit("addi $sp, $sp, 16")
        self.emit("jr $ra")

    # ---------- traducción de cada cuádruplo ----------
    def translate(self, q: Quad):
        op = q.op
        if op == '=':
            if self.type_of(q.result) == 'float':
                self.load_double(q.arg1, "$f0")
                self.store_double("$f0", q.result)
            else:
                self.load_word(q.arg1, "$t0")
                self.store_word("$t0", q.result)
        elif op in ('+', '-', '*', '/', '%', '<', '>', '<=', '>=', '==', '!='):
            self.binary(q)
        elif op == 'neg':
            if self.type_of(q.result) == 'float':
                self.load_double(q.arg1, "$f0")
                self.emit("neg.d $f0, $f0")
                self.store_double("$f0", q.result)
            else:
                self.load_word(q.arg1, "$t0")
                self.emit("neg $t0, $t0")
                self.store_word("$t0", q.result)
        elif op == 'not':
            if self.type_of(q.arg1) == 'float':
                lbl = self.unique("__fnot_")
                self.load_double(q.arg1, "$f0")
                self.emit("mtc1 $zero, $f2")
                self.emit("cvt.d.w $f2, $f2")
                self.emit("li $t0, 1")
                self.emit("c.eq.d $f0, $f2")
                self.emit(f"bc1t {lbl}")
                self.emit("li $t0, 0")
                self.label(lbl)
                self.store_word("$t0", q.result)
            else:
                self.load_word(q.arg1, "$t0")
                self.emit("seq $t0, $t0, $zero")
                self.store_word("$t0", q.result)
        elif op == 'if_false':
            if self.type_of(q.arg1) == 'float':
                self.load_double(q.arg1, "$f0")
                self.emit("mtc1 $zero, $f2")
                self.emit("cvt.d.w $f2, $f2")
                self.emit("c.eq.d $f0, $f2")
                self.emit(f"bc1t {q.result}")
            else:
                self.load_word(q.arg1, "$t0")
                self.emit(f"beq $t0, $zero, {q.result}")
        elif op == 'itof':
            self.load_word(q.arg1, "$t0")
            self.emit("mtc1 $t0, $f0")
            self.emit("cvt.d.w $f0, $f0")
            self.store_double("$f0", q.result)
        elif op == 'label':
            self.label(q.result)
        elif op == 'goto':
            self.emit(f"j {q.result}")
        elif op == 'param':
            t = self.type_of(q.arg1)
            self.emit("addi $sp, $sp, -8")
            if t == 'float':
                self.load_double(q.arg1, "$f0")
                self.emit("s.d $f0, 0($sp)")
            else:
                self.load_word(q.arg1, "$t0")
                self.emit("sw $t0, 0($sp)")
            self.pending.append(t)
        elif op == 'call':
            self.call(q)
        elif op == 'return':
            if q.arg1 is not None:
                if self.type_of(q.arg1) == 'float':
                    self.load_double(q.arg1, "$f0")
                else:
                    self.load_word(q.arg1, "$v0")
            self.emit(f"j f_{self.func}_ret")
        elif op == 'halt':
            self.emit("li $v0, 10")
            self.emit("syscall")
        else:
            raise NotImplementedError(f"Operación no soportada en MIPS: '{op}'")

    def binary(self, q: Quad):
        """Traduce t = a op b para int, float (double) y string."""
        op = q.op
        lt = self.type_of(q.arg1)
        rt = self.type_of(q.arg2)

        # ----- Cadenas -----
        if lt == 'string' or rt == 'string':
            self.load_word(q.arg1, "$a0")
            self.load_word(q.arg2, "$a1")
            if op == '+':
                self.emit("jal __concat")
                self.store_word("$v0", q.result)
            elif op == '==':
                self.emit("jal __strequal")
                self.store_word("$v0", q.result)
            elif op == '!=':
                self.emit("jal __strequal")
                self.emit("xori $v0, $v0, 1")
                self.store_word("$v0", q.result)
            else:
                raise NotImplementedError(f"Operador '{op}' no soportado para string en MIPS")
            return

        # ----- Punto flotante (double) -----
        if lt == 'float' or rt == 'float':
            self.load_double(q.arg1, "$f0")
            self.load_double(q.arg2, "$f2")
            if op == '+':
                self.emit("add.d $f0, $f0, $f2")
                self.store_double("$f0", q.result)
            elif op == '-':
                self.emit("sub.d $f0, $f0, $f2")
                self.store_double("$f0", q.result)
            elif op == '*':
                self.emit("mul.d $f0, $f0, $f2")
                self.store_double("$f0", q.result)
            elif op == '/':
                self.emit("mtc1 $zero, $f4")
                self.emit("cvt.d.w $f4, $f4")
                self.emit("c.eq.d $f2, $f4")
                self.emit("bc1t __err_div")
                self.emit("div.d $f0, $f0, $f2")
                self.store_double("$f0", q.result)
            elif op in ('<', '>', '<=', '>=', '==', '!='):
                lbl = self.unique("__fcmp_")
                self.emit("li $t0, 1")
                if op == '<':
                    self.emit("c.lt.d $f0, $f2")
                    self.emit(f"bc1t {lbl}")
                elif op == '>':
                    self.emit("c.lt.d $f2, $f0")
                    self.emit(f"bc1t {lbl}")
                elif op == '<=':
                    self.emit("c.le.d $f0, $f2")
                    self.emit(f"bc1t {lbl}")
                elif op == '>=':
                    self.emit("c.le.d $f2, $f0")
                    self.emit(f"bc1t {lbl}")
                elif op == '==':
                    self.emit("c.eq.d $f0, $f2")
                    self.emit(f"bc1t {lbl}")
                elif op == '!=':
                    self.emit("c.eq.d $f0, $f2")
                    self.emit(f"bc1f {lbl}")
                self.emit("li $t0, 0")
                self.label(lbl)
                self.store_word("$t0", q.result)
            else:
                raise NotImplementedError(f"Operador '{op}' no soportado para float en MIPS")
            return

        # ----- Enteros (int) -----
        self.load_word(q.arg1, "$t0")
        self.load_word(q.arg2, "$t1")
        int_ops = {
            '+': 'add', '-': 'sub', '*': 'mul',
            '<': 'slt', '>': 'sgt', '<=': 'sle',
            '>=': 'sge', '==': 'seq', '!=': 'sne',
        }
        if op in int_ops:
            self.emit(f"{int_ops[op]} $t0, $t0, $t1")
        elif op == '/':
            self.emit("beq $t1, $zero, __err_div")
            self.emit("div $t0, $t1")
            self.emit("mflo $t0")
        elif op == '%':
            self.emit("beq $t1, $zero, __err_div")
            self.emit("div $t0, $t1")
            self.emit("mfhi $t0")
        else:
            raise NotImplementedError(f"Operador entero no soportado: '{op}'")
        self.store_word("$t0", q.result)

    def call(self, q: Quad):
        n = int(q.arg2)
        arg_types = self.pending[len(self.pending) - n:]
        del self.pending[len(self.pending) - n:]
        if q.arg1 in ('imprimir', 'print'):
            for i, t in enumerate(arg_types):
                offset = 8 * (n - 1 - i)
                if i:
                    self.emit("li $a0, 32")
                    self.emit("li $v0, 11                 # espacio")
                    self.emit("syscall")
                if t == 'float':
                    self.emit(f"l.d $f12, {offset}($sp)")
                    self.emit("li $v0, 3                  # print_double")
                elif t == 'string':
                    self.emit(f"lw $a0, {offset}($sp)")
                    self.emit("li $v0, 4                  # print_string")
                else:
                    self.emit(f"lw $a0, {offset}($sp)")
                    self.emit("li $v0, 1                  # print_int")
                self.emit("syscall")
            self.emit("li $a0, 10")
            self.emit("li $v0, 11                 # salto de linea")
            self.emit("syscall")
        else:
            self.emit(f"jal f_{q.arg1}")
        if n:
            self.emit(f"addi $sp, $sp, {8 * n}           # saca los argumentos")
        if q.result:
            if self.type_of(q.result) == 'float':
                self.store_double("$f0", q.result)
            else:
                self.store_word("$v0", q.result)

    # ---------- rutinas de apoyo (runtime) ----------
    def runtime(self):
        self.text.append("""
# ======================= RUNTIME =======================
# __concat: $a0 = s1, $a1 = s2  ->  $v0 = nueva cadena s1 + s2 (memoria con sbrk)
__concat:
    move $t4, $a0
    move $t5, $a1
    li $t6, 0
    move $t0, $t4
__cc_len1:
    lb $t1, 0($t0)
    beqz $t1, __cc_len2s
    addi $t6, $t6, 1
    addi $t0, $t0, 1
    j __cc_len1
__cc_len2s:
    move $t0, $t5
__cc_len2:
    lb $t1, 0($t0)
    beqz $t1, __cc_alloc
    addi $t6, $t6, 1
    addi $t0, $t0, 1
    j __cc_len2
__cc_alloc:
    addi $a0, $t6, 1
    li $v0, 9
    syscall
    move $t7, $v0
    move $t0, $v0
__cc_cp1:
    lb $t1, 0($t4)
    beqz $t1, __cc_cp2
    sb $t1, 0($t0)
    addi $t0, $t0, 1
    addi $t4, $t4, 1
    j __cc_cp1
__cc_cp2:
    lb $t1, 0($t5)
    sb $t1, 0($t0)
    beqz $t1, __cc_done
    addi $t0, $t0, 1
    addi $t5, $t5, 1
    j __cc_cp2
__cc_done:
    move $v0, $t7
    jr $ra

# __strequal: $a0, $a1  ->  $v0 = 1 si son iguales, 0 si no
__strequal:
    lb $t0, 0($a0)
    lb $t1, 0($a1)
    bne $t0, $t1, __se_no
    beqz $t0, __se_yes
    addi $a0, $a0, 1
    addi $a1, $a1, 1
    j __strequal
__se_yes:
    li $v0, 1
    jr $ra
__se_no:
    li $v0, 0
    jr $ra

# Errores de ejecución: imprimen el mensaje y terminan el programa.
__err_div:
    la $a0, __err_div_msg
    j __error
__err_stack:
    la $a0, __err_stack_msg
    j __error
__error:
    li $v0, 4
    syscall
    li $a0, 10
    li $v0, 11
    syscall
    li $v0, 10
    syscall""")