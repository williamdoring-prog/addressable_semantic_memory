#ifndef ASM_C_H
#define ASM_C_H

#include <stddef.h>

typedef struct {
    const char *address;
    const char *text;
} Fragment;

typedef struct {
    const char *question;
    Fragment *fragments;
    size_t fragment_count;
    size_t budget;
} ASM;

/*
 * Computes ranking and bounded selection and returns the shared JSON document
 * as a malloc'd NUL-terminated string (caller frees with free()).
 * Performs no I/O so calls can be timed cleanly.
 */
char *ASM_run(const ASM *asm_instance);

#endif
