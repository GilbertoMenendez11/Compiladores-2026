.data
.align 3
g_limite: .space 8
.align 3
g_tasa: .space 8
.align 3
g_mensaje: .space 8
.align 2
__depth: .word 0
__err_div_msg: .asciiz "[ERROR DE EJECUCION] Division entre cero"
__err_stack_msg: .asciiz "[ERROR DE EJECUCION] Desbordamiento de pila: mas de 1000 llamadas anidadas"
.align 3
dbl1: .double 0.5
str1: .asciiz "Resultado: "
__noret_factorial: .asciiz "[ERROR DE EJECUCION] La funcion 'factorial' termino sin retornar un valor"
__noret_sumaPares: .asciiz "[ERROR DE EJECUCION] La funcion 'sumaPares' termino sin retornar un valor"

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
    # mensaje = "Resultado: "
    la $t0, str1
    la $t9, g_mensaje
    sw $t0, 0($t9)
    # call main, 0
    jal f_main
    # halt
    li $v0, 10
    syscall
    # func factorial(n):
f_factorial:
    addi $sp, $sp, -16
    sw $ra, 8($sp)
    sw $fp, 0($sp)
    move $fp, $sp
    addi $sp, $sp, -32
    lw $t0, __depth
    addi $t0, $t0, 1
    sw $t0, __depth
    li $t1, 1000
    bgt $t0, $t1, __err_stack
    # t1 = n <= 1
    lw $t0, 16($fp)
    li $t1, 1
    sle $t0, $t0, $t1
    sw $t0, -8($fp)
    # if_false t1 goto L1
    lw $t0, -8($fp)
    beq $t0, $zero, L1
    # return 1
    li $v0, 1
    j f_factorial_ret
    # goto L2
    j L2
    # L1:
L1:
    # t2 = n - 1
    lw $t0, 16($fp)
    li $t1, 1
    sub $t0, $t0, $t1
    sw $t0, -16($fp)
    # param t2
    addi $sp, $sp, -8
    lw $t0, -16($fp)
    sw $t0, 0($sp)
    # t3 = call factorial, 1
    jal f_factorial
    addi $sp, $sp, 8           # saca los argumentos
    sw $v0, -24($fp)
    # t4 = n * t3
    lw $t0, 16($fp)
    lw $t1, -24($fp)
    mul $t0, $t0, $t1
    sw $t0, -32($fp)
    # return t4
    lw $v0, -32($fp)
    j f_factorial_ret
    # L2:
L2:
    # end_func
    la $a0, __noret_factorial
    j __error
f_factorial_ret:
    lw $t0, __depth
    addi $t0, $t0, -1
    sw $t0, __depth
    move $sp, $fp
    lw $fp, 0($sp)
    lw $ra, 8($sp)
    addi $sp, $sp, 16
    jr $ra
    # func sumaPares(max):
f_sumaPares:
    addi $sp, $sp, -16
    sw $ra, 8($sp)
    sw $fp, 0($sp)
    move $fp, $sp
    addi $sp, $sp, -112
    lw $t0, __depth
    addi $t0, $t0, 1
    sw $t0, __depth
    li $t1, 1000
    bgt $t0, $t1, __err_stack
    # suma = 0
    li $t0, 0
    sw $t0, -8($fp)
    # i = 0
    li $t0, 0
    sw $t0, -16($fp)
    # L3:
L3:
    # t5 = i <= max
    lw $t0, -16($fp)
    lw $t1, 16($fp)
    sle $t0, $t0, $t1
    sw $t0, -24($fp)
    # if_false t5 goto L4
    lw $t0, -24($fp)
    beq $t0, $zero, L4
    # t6 = (float) i
    lw $t0, -16($fp)
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -32($fp)
    # t7 = (float) 2
    li $t0, 2
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -40($fp)
    # t8 = t6 / t7
    l.d $f0, -32($fp)
    l.d $f2, -40($fp)
    mtc1 $zero, $f4
    cvt.d.w $f4, $f4
    c.eq.d $f2, $f4
    bc1t __err_div
    div.d $f0, $f0, $f2
    s.d $f0, -48($fp)
    # t9 = (float) 2
    li $t0, 2
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -56($fp)
    # t10 = t8 * t9
    l.d $f0, -48($fp)
    l.d $f2, -56($fp)
    mul.d $f0, $f0, $f2
    s.d $f0, -64($fp)
    # t11 = (float) i
    lw $t0, -16($fp)
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -72($fp)
    # t12 = t11 - t10
    l.d $f0, -72($fp)
    l.d $f2, -64($fp)
    sub.d $f0, $f0, $f2
    s.d $f0, -80($fp)
    # t13 = (float) 0
    li $t0, 0
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -88($fp)
    # t14 = t12 == t13
    l.d $f0, -80($fp)
    l.d $f2, -88($fp)
    li $t0, 1
    c.eq.d $f0, $f2
    bc1t __fcmp_1
    li $t0, 0
__fcmp_1:
    sw $t0, -96($fp)
    # if_false t14 goto L5
    lw $t0, -96($fp)
    beq $t0, $zero, L5
    # t15 = suma + i
    lw $t0, -8($fp)
    lw $t1, -16($fp)
    add $t0, $t0, $t1
    sw $t0, -104($fp)
    # suma = t15
    lw $t0, -104($fp)
    sw $t0, -8($fp)
    # L5:
L5:
    # t16 = i + 1
    lw $t0, -16($fp)
    li $t1, 1
    add $t0, $t0, $t1
    sw $t0, -112($fp)
    # i = t16
    lw $t0, -112($fp)
    sw $t0, -16($fp)
    # goto L3
    j L3
    # L4:
L4:
    # return suma
    lw $v0, -8($fp)
    j f_sumaPares_ret
    # end_func
    la $a0, __noret_sumaPares
    j __error
f_sumaPares_ret:
    lw $t0, __depth
    addi $t0, $t0, -1
    sw $t0, __depth
    move $sp, $fp
    lw $fp, 0($sp)
    lw $ra, 8($sp)
    addi $sp, $sp, 16
    jr $ra
    # func main():
f_main:
    addi $sp, $sp, -16
    sw $ra, 8($sp)
    sw $fp, 0($sp)
    move $fp, $sp
    addi $sp, $sp, -112
    lw $t0, __depth
    addi $t0, $t0, 1
    sw $t0, __depth
    li $t1, 1000
    bgt $t0, $t1, __err_stack
    # param 5
    addi $sp, $sp, -8
    li $t0, 5
    sw $t0, 0($sp)
    # t17 = call factorial, 1
    jal f_factorial
    addi $sp, $sp, 8           # saca los argumentos
    sw $v0, -8($fp)
    # x = t17
    lw $t0, -8($fp)
    sw $t0, -16($fp)
    # param limite
    addi $sp, $sp, -8
    la $t9, g_limite
    lw $t0, 0($t9)
    sw $t0, 0($sp)
    # t18 = call sumaPares, 1
    jal f_sumaPares
    addi $sp, $sp, 8           # saca los argumentos
    sw $v0, -24($fp)
    # y = t18
    lw $t0, -24($fp)
    sw $t0, -32($fp)
    # t19 = x + y
    lw $t0, -16($fp)
    lw $t1, -32($fp)
    add $t0, $t0, $t1
    sw $t0, -40($fp)
    # t20 = (float) t19
    lw $t0, -40($fp)
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -48($fp)
    # t21 = t20 * tasa
    l.d $f0, -48($fp)
    la $t9, g_tasa
    l.d $f2, 0($t9)
    mul.d $f0, $f0, $f2
    s.d $f0, -56($fp)
    # t22 = -1
    li $t0, 1
    neg $t0, $t0
    sw $t0, -64($fp)
    # t23 = (float) t22
    lw $t0, -64($fp)
    mtc1 $t0, $f0
    cvt.d.w $f0, $f0
    s.d $f0, -72($fp)
    # t24 = t21 - t23
    l.d $f0, -56($fp)
    l.d $f2, -72($fp)
    sub.d $f0, $f0, $f2
    s.d $f0, -80($fp)
    # total = t24
    l.d $f0, -80($fp)
    s.d $f0, -88($fp)
    # L6:
L6:
    # t25 = x != 0
    lw $t0, -16($fp)
    li $t1, 0
    sne $t0, $t0, $t1
    sw $t0, -96($fp)
    # if_false t25 goto L7
    lw $t0, -96($fp)
    beq $t0, $zero, L7
    # t26 = x - 1
    lw $t0, -16($fp)
    li $t1, 1
    sub $t0, $t0, $t1
    sw $t0, -104($fp)
    # x = t26
    lw $t0, -104($fp)
    sw $t0, -16($fp)
    # goto L6
    j L6
    # L7:
L7:
    # resultado_final = total
    l.d $f0, -88($fp)
    s.d $f0, -112($fp)
    # return
    j f_main_ret
    # end_func
f_main_ret:
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
