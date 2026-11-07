#include "asm_c.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const Fragment *fragment;
    size_t words;
    int score;
} Ranked;

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} Buf;

static void out_of_memory(void) {
    fprintf(stderr, "out of memory\n");
    exit(1);
}

static void *xalloc(size_t count, size_t size) {
    void *p;
    if (count == 0) count = 1;
    p = calloc(count, size);
    if (!p) out_of_memory();
    return p;
}

static int is_word(unsigned char c) {
    return isalnum(c);
}

static size_t word_count(const char *text) {
    size_t count = 0;
    int in_word = 0;
    while (*text) {
        int current = is_word((unsigned char)*text);
        if (current && !in_word) count++;
        in_word = current;
        text++;
    }
    return count;
}

/*
 * Splits a lowercase copy of text into words in place. buf must point to a
 * buffer of at least strlen(text) + 1 bytes; words[] receives pointers into
 * buf. Returns the token count.
 */
static size_t split_words(char *buf, const char *text, const char **words) {
    size_t count = 0;
    char *p;
    strcpy(buf, text);
    for (p = buf; *p; p++) {
        *p = (char)tolower((unsigned char)*p);
    }
    p = buf;
    while (*p) {
        if (!is_word((unsigned char)*p)) {
            *p = '\0';
            p++;
            continue;
        }
        words[count++] = p;
        while (is_word((unsigned char)*p)) p++;
        if (*p) {
            *p = '\0';
            p++;
        }
    }
    return count;
}

static int contains_query_word(const char *question, const char *word, size_t len) {
    const char *p = question;
    while (*p) {
        while (*p && !is_word((unsigned char)*p)) p++;
        const char *start = p;
        while (*p && is_word((unsigned char)*p)) p++;
        if ((size_t)(p - start) == len) {
            size_t i;
            int same = 1;
            for (i = 0; i < len; i++) {
                if (tolower((unsigned char)start[i]) != tolower((unsigned char)word[i])) {
                    same = 0;
                    break;
                }
            }
            if (same) return 1;
        }
    }
    return 0;
}

/*
 * Counts distinct fragment words that also appear in the question, matching
 * the set intersection used by the Python/Rust/Go implementations.
 */
static int score_words(const char **words, size_t count, const char *question) {
    int score = 0;
    size_t i, j;
    for (i = 0; i < count; i++) {
        int seen = 0;
        for (j = 0; j < i; j++) {
            if (strcmp(words[j], words[i]) == 0) {
                seen = 1;
                break;
            }
        }
        if (seen) continue;
        if (contains_query_word(question, words[i], strlen(words[i]))) score++;
    }
    return score;
}

static void buf_reserve(Buf *b, size_t extra) {
    size_t needed = b->len + extra + 1;
    size_t cap;
    char *grown;
    if (b->data && needed <= b->cap) return;
    cap = b->cap ? b->cap : 64;
    while (cap < needed) cap *= 2;
    grown = realloc(b->data, cap);
    if (!grown) {
        free(b->data);
        out_of_memory();
    }
    b->data = grown;
    b->cap = cap;
}

static void buf_appendn(Buf *b, const char *s, size_t n) {
    buf_reserve(b, n);
    memcpy(b->data + b->len, s, n);
    b->len += n;
    b->data[b->len] = '\0';
}

static void buf_putc(Buf *b, char c) {
    buf_appendn(b, &c, 1);
}

static void buf_puts(Buf *b, const char *s) {
    buf_appendn(b, s, strlen(s));
}

static void buf_put_size(Buf *b, size_t value) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "%zu", value);
    buf_puts(b, tmp);
}

static void buf_put_int(Buf *b, int value) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "%d", value);
    buf_puts(b, tmp);
}

/* Appends the contents of s as JSON string data, escaping quotes, backslashes,
   and control characters. Bytes >= 0x80 pass through unchanged. */
static void buf_put_json_escaped(Buf *b, const char *s) {
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        switch (c) {
        case '"': buf_puts(b, "\\\""); break;
        case '\\': buf_puts(b, "\\\\"); break;
        case '\b': buf_puts(b, "\\b"); break;
        case '\f': buf_puts(b, "\\f"); break;
        case '\n': buf_puts(b, "\\n"); break;
        case '\r': buf_puts(b, "\\r"); break;
        case '\t': buf_puts(b, "\\t"); break;
        default:
            if (c < 0x20) {
                char tmp[8];
                snprintf(tmp, sizeof(tmp), "\\u%04x", c);
                buf_puts(b, tmp);
            } else {
                buf_putc(b, (char)c);
            }
        }
    }
}

static void buf_put_json_string(Buf *b, const char *s) {
    buf_putc(b, '"');
    buf_put_json_escaped(b, s);
    buf_putc(b, '"');
}

static int ranked_compare(const void *a, const void *b) {
    const Ranked *x = a, *y = b;
    if (x->score != y->score) return (y->score > x->score) - (y->score < x->score);
    return strcmp(x->fragment->address, y->fragment->address);
}

char *ASM_run(const ASM *asm_instance) {
    Ranked *ranked = xalloc(asm_instance->fragment_count, sizeof(Ranked));
    size_t ranked_count = 0, original_words = 0;
    size_t context_words = 0, selected_count = 0;
    size_t *selected;
    Buf out = {NULL, 0, 0};
    size_t i;

    for (i = 0; i < asm_instance->fragment_count; i++) {
        const Fragment *f = &asm_instance->fragments[i];
        size_t text_len = strlen(f->text);
        const char **words = xalloc(text_len + 1, sizeof(char *));
        char *buf = xalloc(text_len + 1, 1);
        size_t token_count = split_words(buf, f->text, words);
        int score = score_words(words, token_count, asm_instance->question);

        original_words += token_count;
        if (score > 0) {
            ranked[ranked_count].fragment = f;
            ranked[ranked_count].words = token_count;
            ranked[ranked_count].score = score;
            ranked_count++;
        }
        free(words);
        free(buf);
    }

    qsort(ranked, ranked_count, sizeof(Ranked), ranked_compare);

    selected = xalloc(asm_instance->fragment_count, sizeof(size_t));
    for (i = 0; i < ranked_count; i++) {
        if (context_words + ranked[i].words > asm_instance->budget) continue;
        selected[selected_count++] = i;
        context_words += ranked[i].words;
    }

    buf_puts(&out, "{\"original_source_words\":");
    buf_put_size(&out, original_words);
    buf_puts(&out, ",\"question_words\":");
    buf_put_size(&out, word_count(asm_instance->question));
    buf_puts(&out, ",\"retrieved_addresses\":[");
    for (i = 0; i < ranked_count; i++) {
        if (i) buf_putc(&out, ',');
        buf_put_json_string(&out, ranked[i].fragment->address);
    }
    buf_puts(&out, "],\"selected\":[");
    for (i = 0; i < selected_count; i++) {
        const Ranked *r = &ranked[selected[i]];
        if (i) buf_putc(&out, ',');
        buf_puts(&out, "{\"address\":");
        buf_put_json_string(&out, r->fragment->address);
        buf_puts(&out, ",\"score\":");
        buf_put_int(&out, r->score);
        buf_putc(&out, '}');
    }
    buf_puts(&out, "],\"context\":\"");
    for (i = 0; i < selected_count; i++) {
        if (i) buf_putc(&out, ' ');
        buf_put_json_escaped(&out, ranked[selected[i]].fragment->text);
    }
    buf_puts(&out, "\",\"context_words\":");
    buf_put_size(&out, context_words);
    buf_putc(&out, '}');

    free(selected);
    free(ranked);
    return out.data;
}
