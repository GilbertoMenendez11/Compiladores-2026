.data
.align 3
g_valor: .space 8
.align 2
__depth: .word 0
__err_div_msg: .asciiz "[ERROR DE EJECUCION] Division entre cero"
__err_stack_msg: .asciiz "[ERROR DE EJECUCION] Desbordamiento de pila: mas de 1000 llamadas anidadas"
__noret_externa: .asciiz "[ERROR DE EJECUCION] La funcion 'externa' termino sin retornar un valor"
__noret_interna: .asciiz "[ERROR DE EJECUCION] La funcion 'interna' termino sin retornar un valor"

.text
.globl main
main:
    li $t0, -8
    and $sp, $sp, $t0          # alinea la pila a 8 bytes (para los double)
    move $fp, $sp
    # param 3
    addi $sp, $sp, -8   # temporales del codigo global
    addi $sp, $sp, -8
    li $t0, 3
    sw $t0, 0($sp)
    # t1 = call externa, 1
    jal f_externa
    addi $sp, $sp, 8           # saca los argumentos
    sw $v0, -8($fp)
    # valor = t1
    lw $t0, -8($fp)
    la $t9, g_valor
    sw $t0, 0($t9)
    # halt
    li $v0, 10
    syscall
    # func externa(x):
f_externa:
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
    # param x
    addi $sp, $sp, -8
    lw $t0, 16($fp)
    sw $t0, 0($sp)
    # t2 = call interna, 1
    jal f_interna
    addi $sp, $sp, 8           # saca los argumentos
    sw $v0, -8($fp)
    # resultado = t2
    lw $t0, -8($fp)
    sw $t0, -16($fp)
    # return resultado
    lw $v0, -16($fp)
    j f_externa_ret
    # end_func
    la $a0, __noret_externa
    j __error
f_externa_ret:
    lw $t0, __depth
    addi $t0, $t0, -1
    sw $t0, __depth
    move $sp, $fp
    lw $fp, 0($sp)
    lw $ra, 8($sp)
    addi $sp, $sp, 16
    jr $ra
    # func interna(y):
f_interna:
    addi $sp, $sp, -16
    sw $ra, 8($sp)
    sw $fp, 0($sp)
    move $fp, $sp
    addi $sp, $sp, -8
    lw $t0, __depth
    addi $t0, $t0, 1
    sw $t0, __depth
    li $t1, 1000
    bgt $t0, $t1, __err_stack
    # t3 = y + 1
    lw $t0, 16($fp)
    li $t1, 1
    add $t0, $t0, $t1
    sw $t0, -8($fp)
    # return t3
    lw $v0, -8($fp)
    j f_interna_ret
    # end_func
    la $a0, __noret_interna
    j __error
f_interna_ret:
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
