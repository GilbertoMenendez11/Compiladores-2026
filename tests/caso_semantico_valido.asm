.data
.align 3
g_limite: .space 8
.align 3
g_tasa: .space 8
.align 2
__depth: .word 0
__err_div_msg: .asciiz "[ERROR DE EJECUCION] Division entre cero"
__err_stack_msg: .asciiz "[ERROR DE EJECUCION] Desbordamiento de pila: mas de 1000 llamadas anidadas"
.align 3
dbl1: .double 0.5
__noret_sumar: .asciiz "[ERROR DE EJECUCION] La funcion 'sumar' termino sin retornar un valor"

.text
.globl main
main:
    li $t0, -8
    and $sp, $sp, $t0          # alinea la pila a 8 bytes (para los double)
    move $fp, $sp
    # limite = 10
    li $t0, 10
    la $t9, g_limite
    sw $t0, 0($t9)
    # tasa = 0.5
    la $t9, dbl1
    l.d $f0, 0($t9)
    la $t9, g_tasa
    s.d $f0, 0($t9)
    # call principal, 0
    jal f_principal
    # halt
    li $v0, 10
    syscall
    # func sumar(a, b):
f_sumar:
    addi $sp, $sp, -16
    sw $ra, 8($sp)
    sw $fp, 0($sp)
    move $fp, $sp
    addi $sp, $sp, -16
    lw $t0, __depth
    addi $t0, $t0, 1
    sw $t0, __depth
    li $t1, 1000
    bgt $t0, $t1, __err_stack
    # t1 = a + b
    lw $t0, 24($fp)
    lw $t1, 16($fp)
    add $t0, $t0, $t1
    sw $t0, -8($fp)
    # resultado = t1
    lw $t0, -8($fp)
    sw $t0, -16($fp)
    # return resultado
    lw $v0, -16($fp)
    j f_sumar_ret
    # end_func
    la $a0, __noret_sumar
    j __error
f_sumar_ret:
    lw $t0, __depth
    addi $t0, $t0, -1
    sw $t0, __depth
    move $sp, $fp
    lw $fp, 0($sp)
    lw $ra, 8($sp)
    addi $sp, $sp, 16
    jr $ra
    # func principal():
f_principal:
    addi $sp, $sp, -16
    sw $ra, 8($sp)
    sw $fp, 0($sp)
    move $fp, $sp
    addi $sp, $sp, -40
    lw $t0, __depth
    addi $t0, $t0, 1
    sw $t0, __depth
    li $t1, 1000
    bgt $t0, $t1, __err_stack
    # param limite
    addi $sp, $sp, -8
    la $t9, g_limite
    lw $t0, 0($t9)
    sw $t0, 0($sp)
    # param 5
    addi $sp, $sp, -8
    li $t0, 5
    sw $t0, 0($sp)
    # t2 = call sumar, 2
    jal f_sumar
    addi $sp, $sp, 16           # saca los argumentos
    sw $v0, -8($fp)
    # subtotal = t2
    lw $t0, -8($fp)
    sw $t0, -16($fp)
    # t3 = (float) subtotal
    lw $t0, -16($fp)
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -24($fp)
    # t4 = t3 * tasa
    l.d $f0, -24($fp)
    la $t9, g_tasa
    l.d $f2, 0($t9)
    mul.d $f0, $f0, $f2
    s.d $f0, -32($fp)
    # total = t4
    l.d $f0, -32($fp)
    s.d $f0, -40($fp)
    # param total
    addi $sp, $sp, -8
    l.d $f0, -40($fp)
    s.d $f0, 0($sp)
    # call imprimir, 1
    l.d $f12, 0($sp)
    li $v0, 3                  # print_double
    syscall
    li $a0, 10
    li $v0, 11                 # salto de linea
    syscall
    addi $sp, $sp, 8           # saca los argumentos
    # return
    j f_principal_ret
    # end_func
f_principal_ret:
    lw $t0, __depth
    addi $t0, $t0, -1
    sw $t0, __depth
    move $sp, $fp
    lw $fp, 0($sp)
    lw $ra, 8($sp)
    addi $sp, $sp, 16
    jr $ra

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
    syscall
