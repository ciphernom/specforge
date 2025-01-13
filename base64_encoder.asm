;=============================================================================
;  Assemble: nasm -f elf64 base64_encoder.asm -o base64_encoder.o
;  Link:     ld base64_encoder.o -o base64_encoder
;  Usage:    echo -n "Hello!" | ./base64_encoder
;  Expected: SGVsbG8h
;=============================================================================

BITS 64

; System call definitions
%define SYS_READ    0
%define SYS_WRITE   1
%define SYS_EXIT    60
%define STDIN       0
%define STDOUT      1
%define BUF_SIZE    4096

section .rodata
    ; Standard Base64 alphabet
    base64_table:    db "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

section .bss
    raw_buf:        resb BUF_SIZE    ; Input buffer
    leftover_buf:   resb 2           ; Buffer for incomplete triplets
    leftover_count: resq 1           ; Count of leftover bytes
    triplet_count:  resq 1           ; Count of complete triplets
    encoded_block:  resb 4           ; Output block for encoded characters

section .text
    global _start

_start:
    ; Initialize leftover count
    xor rax, rax
    mov qword [leftover_count], rax

read_loop:
    ; Read input chunk
    mov rax, SYS_READ
    mov rdi, STDIN
    mov rsi, raw_buf
    mov rdx, BUF_SIZE
    syscall

    ; Check for EOF and errors
    cmp rax, 0
    je finish
    js read_error

    ; Calculate number of complete triplets
    mov rcx, 3
    mov rax, rax
    xor rdx, rdx
    div rcx
    mov qword [triplet_count], rax    ; Store complete triplets
    mov qword [leftover_count], rdx   ; Store leftover bytes

    ; Process complete triplets
    test rax, rax
    jz process_leftovers

    mov rbx, rax        ; Store triplet count for loop
    xor r9, r9         ; Initialize triplet offset

process_triplets:
    ; Load three bytes
    movzx r8, byte [raw_buf + r9]
    movzx r10, byte [raw_buf + r9 + 1]
    movzx r11, byte [raw_buf + r9 + 2]

    ; Combine bytes
    shl r8, 16
    shl r10, 8
    or r8, r10
    or r8, r11

    ; Extract 6-bit chunks
    mov r10, r8
    shr r10, 18
    and r10, 0x3F      ; First 6 bits
    mov r11, r8
    shr r11, 12
    and r11, 0x3F      ; Second 6 bits
    mov rbx, r8
    shr rbx, 6
    and rbx, 0x3F      ; Third 6 bits
    mov r8, r8
    and r8, 0x3F       ; Fourth 6 bits

    ; Look up in base64_table and store
    mov rsi, base64_table
    mov al, byte [rsi + r10]
    mov byte [encoded_block], al
    mov al, byte [rsi + r11]
    mov byte [encoded_block + 1], al
    mov al, byte [rsi + rbx]
    mov byte [encoded_block + 2], al
    mov al, byte [rsi + r8]
    mov byte [encoded_block + 3], al

    ; Write encoded block
    mov rax, SYS_WRITE
    mov rdi, STDOUT
    mov rsi, encoded_block
    mov rdx, 4
    syscall
    js write_error

    ; Update counters and continue
    add r9, 3
    dec qword [triplet_count]
    jnz process_triplets

process_leftovers:
    ; Handle leftover bytes
    mov rax, qword [leftover_count]
    test rax, rax
    jz read_loop

    ; Copy leftover bytes
    xor rcx, rcx
copy_leftovers:
    cmp rcx, qword [leftover_count]
    je encode_leftovers
    mov al, byte [raw_buf + r9 + rcx]
    mov byte [leftover_buf + rcx], al
    inc rcx
    jmp copy_leftovers

encode_leftovers:
    ; Encode 1 or 2 leftover bytes
    mov rax, qword [leftover_count]
    cmp rax, 1
    je encode_one_byte
    cmp rax, 2
    je encode_two_bytes
    jmp read_loop

encode_one_byte:
    ; Handle single leftover byte
    movzx r8, byte [leftover_buf]
    shl r8, 4
    and r8, 0x3F
    mov rsi, base64_table
    mov al, byte [rsi + r8]
    mov byte [encoded_block], al
    shr r8, 2
    and r8, 0x3F
    mov al, byte [rsi + r8]
    mov byte [encoded_block + 1], al
    mov byte [encoded_block + 2], '='
    mov byte [encoded_block + 3], '='
    
    ; Write padded block
    mov rax, SYS_WRITE
    mov rdi, STDOUT
    mov rsi, encoded_block
    mov rdx, 4
    syscall
    js write_error
    jmp read_loop

encode_two_bytes:
    ; Handle two leftover bytes
    movzx r8, byte [leftover_buf]
    movzx r10, byte [leftover_buf + 1]
    shl r8, 16
    shl r10, 8
    or r8, r10
    
    mov r10, r8
    shr r10, 18
    and r10, 0x3F
    mov r11, r8
    shr r11, 12
    and r11, 0x3F
    mov rbx, r8
    shr rbx, 6
    and rbx, 0x3F
    
    mov rsi, base64_table
    mov al, byte [rsi + r10]
    mov byte [encoded_block], al
    mov al, byte [rsi + r11]
    mov byte [encoded_block + 1], al
    mov al, byte [rsi + rbx]
    mov byte [encoded_block + 2], al
    mov byte [encoded_block + 3], '='
    
    ; Write padded block
    mov rax, SYS_WRITE
    mov rdi, STDOUT
    mov rsi, encoded_block
    mov rdx, 4
    syscall
    js write_error
    jmp read_loop

finish:
    ; Process any final leftovers
    mov rax, qword [leftover_count]
    test rax, rax
    jnz encode_leftovers
    
    ; Exit successfully
    xor rdi, rdi
    jmp exit

read_error:
    mov rdi, 1
    jmp exit

write_error:
    mov rdi, 1
    jmp exit

exit:
    mov rax, SYS_EXIT
    syscall
