#if !defined(_WIN32)
#define _POSIX_C_SOURCE 199309L
#endif
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

typedef struct { char **items; size_t count; } WordSet;
typedef struct { char *address; char *text; size_t token_count; int score; } Fragment;
typedef struct { char *address; const char *resolved_text; } Lookup;

static char *read_line(FILE *input) {
    size_t capacity = 256, length = 0;
    char *line = (char *)malloc(capacity);
    if (!line) return NULL;
    int ch;
    while ((ch = fgetc(input)) != EOF && ch != '\n') {
        if (length + 1 >= capacity) {
            capacity *= 2;
            char *grown = (char *)realloc(line, capacity);
            if (!grown) { free(line); return NULL; }
            line = grown;
        }
        line[length++] = (char)ch;
    }
    if (ch == EOF && length == 0) { free(line); return NULL; }
    if (length > 0 && line[length - 1] == '\r') length--;
    line[length] = '\0';
    return line;
}

static char *unescape_field(const char *text) {
    size_t length = strlen(text);
    char *output = (char *)malloc(length + 1);
    if (!output) return NULL;
    size_t in = 0, out = 0;
    while (in < length) {
        if (text[in] == '\\') {
            if (in + 1 >= length) { free(output); return NULL; }
            char next = text[in + 1];
            if (next == '\\' || next == 't' || next == 'n' || next == 'r') {
                output[out++] = next == 't' ? '\t' : next == 'n' ? '\n' : next == 'r' ? '\r' : '\\';
                in += 2;
                continue;
            }
            free(output);
            return NULL;
        }
        output[out++] = text[in++];
    }
    output[out] = '\0';
    return output;
}

static int is_ascii_alnum(unsigned char ch) {
    return (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9');
}

static char *lowercase_copy(const char *start, size_t length) {
    char *word = (char *)malloc(length + 1);
    if (!word) return NULL;
    for (size_t i = 0; i < length; i++) {
        unsigned char ch = (unsigned char)start[i];
        word[i] = (char)((ch >= 'A' && ch <= 'Z') ? ch + ('a' - 'A') : ch);
    }
    word[length] = '\0';
    return word;
}

static int wordset_contains(const WordSet *set, const char *word) {
    for (size_t i = 0; i < set->count; i++) if (strcmp(set->items[i], word) == 0) return 1;
    return 0;
}

static void wordset_add(WordSet *set, char *word) {
    if (wordset_contains(set, word)) { free(word); return; }
    char **grown = (char **)realloc(set->items, (set->count + 1) * sizeof(char *));
    if (!grown) { free(word); return; }
    set->items = grown;
    set->items[set->count++] = word;
}

static WordSet tokenize(const char *text) {
    WordSet words = {NULL, 0};
    size_t index = 0, length = strlen(text);
    while (index < length) {
        while (index < length && !is_ascii_alnum((unsigned char)text[index])) index++;
        size_t start = index;
        while (index < length && is_ascii_alnum((unsigned char)text[index])) index++;
        if (index > start) wordset_add(&words, lowercase_copy(text + start, index - start));
    }
    return words;
}

static size_t word_count(const char *text) {
    size_t count = 0;
    int in_word = 0;
    for (const unsigned char *p = (const unsigned char *)text; *p; p++) {
        int current = is_ascii_alnum(*p);
        if (current && !in_word) count++;
        in_word = current;
    }
    return count;
}

static void fail(const char *message);

static char *baseline_context(Fragment *fragments, size_t count, size_t budget) {
    size_t capacity = 1;
    for (size_t i = 0; i < count; i++) capacity += strlen(fragments[i].text) + 1;
    char *source = (char *)calloc(capacity, 1);
    if (!source) fail("out of memory");
    for (size_t i = 0; i < count; i++) {
        if (i) strcat(source, " ");
        strcat(source, fragments[i].text);
    }
    size_t seen = 0;
    int in_word = 0;
    char *end = source;
    for (char *cursor = source; *cursor; cursor++) {
        int word = is_ascii_alnum((unsigned char)*cursor);
        if (word && !in_word && ++seen == budget) {
            end = cursor + 1;
            while (is_ascii_alnum((unsigned char)*end)) end++;
            *end = '\0';
            break;
        }
        in_word = word;
    }
    return source;
}

static void wordset_free(WordSet *set) {
    for (size_t i = 0; i < set->count; i++) free(set->items[i]);
    free(set->items);
    set->items = NULL;
    set->count = 0;
}

static int fragment_compare(const void *left, const void *right) {
    const Fragment *a = *(const Fragment * const *)left;
    const Fragment *b = *(const Fragment * const *)right;
    if (a->score != b->score) return a->score > b->score ? -1 : 1;
    return strcmp(a->address, b->address);
}

static void json_string(const char *text) {
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)text; *p; p++) {
        switch (*p) {
            case '"': fputs("\\\"", stdout); break;
            case '\\': fputs("\\\\", stdout); break;
            case '\b': fputs("\\b", stdout); break;
            case '\f': fputs("\\f", stdout); break;
            case '\n': fputs("\\n", stdout); break;
            case '\r': fputs("\\r", stdout); break;
            case '\t': fputs("\\t", stdout); break;
            default:
                if (*p < 0x20) printf("\\u%04x", *p);
                else putchar(*p);
        }
    }
    putchar('"');
}

static uint64_t now_ns(void) {
#if defined(_WIN32)
    LARGE_INTEGER counter, frequency;
    if (!QueryPerformanceFrequency(&frequency) || !QueryPerformanceCounter(&counter)) return 0;
    return (uint64_t)(((long double)counter.QuadPart * 1000000000.0L) / (long double)frequency.QuadPart);
#else
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) return 0;
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
#endif
}

static void fail(const char *message) {
    fprintf(stderr, "%s\n", message);
    exit(1);
}

int main(int argc, char **argv) {
    uint64_t started = now_ns();
    int baseline = argc > 2 && strcmp(argv[2], "baseline") == 0;
    if (argc > 2 && !baseline && strcmp(argv[2], "asm") != 0) fail("strategy must be asm or baseline");
    FILE *input = stdin;
    if (argc > 1) {
        input = fopen(argv[1], "rb");
        if (!input) fail("could not open benchmark fixture");
    }
    char *line = read_line(input);
    if (!line || strcmp(line, "ASM-BENCH-V1") != 0) fail("invalid input header");
    free(line);

    char *fixture_id = NULL, *question = NULL;
    size_t budget = 0, fragment_count = 0, fragment_capacity = 8, lookup_count = 0, lookup_capacity = 4;
    Fragment *fragments = (Fragment *)calloc(fragment_capacity, sizeof(Fragment));
    Lookup *lookups = (Lookup *)calloc(lookup_capacity, sizeof(Lookup));
    if (!fragments || !lookups) fail("out of memory");

    while ((line = read_line(input)) != NULL) {
        if (line[0] == '\0') { free(line); continue; }
        char *first = strchr(line, '\t');
        if (!first) fail("record is missing tab separators");
        *first = '\0';
        char *kind = line, *rest = first + 1;
        if (strcmp(kind, "fragment") == 0) {
            char *second = strchr(rest, '\t');
            if (!second) fail("fragment record requires address and text");
            *second = '\0';
            if (fragment_count == fragment_capacity) {
                fragment_capacity *= 2;
                Fragment *grown = (Fragment *)realloc(fragments, fragment_capacity * sizeof(Fragment));
                if (!grown) fail("out of memory");
                fragments = grown;
                /* realloc leaves the extended slots uninitialized; scores must start at zero. */
                memset(fragments + fragment_count, 0, (fragment_capacity - fragment_count) * sizeof(Fragment));
            }
            fragments[fragment_count].address = unescape_field(rest);
            fragments[fragment_count].text = unescape_field(second + 1);
            if (!fragments[fragment_count].address || !fragments[fragment_count].text) fail("invalid fragment escape or out of memory");
            fragment_count++;
        } else if (strcmp(kind, "lookup") == 0) {
            if (lookup_count == lookup_capacity) {
                lookup_capacity *= 2;
                Lookup *grown = (Lookup *)realloc(lookups, lookup_capacity * sizeof(Lookup));
                if (!grown) fail("out of memory");
                lookups = grown;
            }
            lookups[lookup_count].address = unescape_field(rest);
            if (!lookups[lookup_count].address) fail("invalid field escape");
            lookup_count++;
        } else if (strcmp(kind, "id") == 0) {
            fixture_id = unescape_field(rest);
            if (!fixture_id) fail("invalid field escape");
        } else if (strcmp(kind, "question") == 0) {
            question = unescape_field(rest);
            if (!question) fail("invalid field escape");
        }
        else if (strcmp(kind, "budget") == 0) {
            if (rest[0] == '-') fail("budget must be a positive integer");
            char *end = NULL;
            unsigned long parsed = strtoul(rest, &end, 10);
            if (!end || *end || parsed == 0) fail("budget must be a positive integer");
            budget = (size_t)parsed;
        } else fail("unknown record type");
        free(line);
    }
    if (input != stdin) fclose(input);
    if (!fixture_id || !fixture_id[0] || !question || !question[0] || budget == 0 || fragment_count == 0) fail("fixture requires id, question, positive budget, and fragments");

    for (size_t i = 0; i < fragment_count; i++) {
        for (size_t j = i + 1; j < fragment_count; j++) {
            if (strcmp(fragments[i].address, fragments[j].address) == 0) fail("duplicate fragment address");
        }
    }

    uint64_t parsing_ns = now_ns() - started;
    uint64_t retrieval_started = now_ns();
    uint64_t baseline_assembly_started = baseline ? retrieval_started : 0;
    WordSet query_words = baseline ? (WordSet){NULL, 0} : tokenize(question);
    size_t original_tokens = 0;
    Fragment **ranked = (Fragment **)malloc(fragment_count * sizeof(Fragment *));
    size_t ranked_count = 0;
    for (size_t i = 0; i < fragment_count; i++) {
        fragments[i].token_count = word_count(fragments[i].text);
        if (!baseline) {
            WordSet terms = tokenize(fragments[i].text);
            for (size_t term = 0; term < terms.count; term++) {
                if (wordset_contains(&query_words, terms.items[term])) fragments[i].score++;
            }
            wordset_free(&terms);
            if (fragments[i].score > 0) ranked[ranked_count++] = &fragments[i];
        }
        original_tokens += fragments[i].token_count;
    }
    qsort(ranked, ranked_count, sizeof(Fragment *), fragment_compare);
    uint64_t retrieval_ns = baseline ? 0 : now_ns() - retrieval_started;

    uint64_t lookup_started = now_ns();
    for (size_t i = 0; i < (baseline ? 0 : lookup_count); i++) {
        lookups[i].resolved_text = NULL;
        for (size_t j = 0; j < fragment_count; j++) {
            if (strcmp(lookups[i].address, fragments[j].address) == 0) {
                lookups[i].resolved_text = fragments[j].text;
                break;
            }
        }
    }
    uint64_t address_lookup_ns = baseline ? 0 : now_ns() - lookup_started;

    uint64_t assembly_started = baseline ? baseline_assembly_started : now_ns();
    size_t context_tokens = 0, selected_count = 0, context_capacity = 1;
    int *selected_flags = (int *)calloc(ranked_count ? ranked_count : 1, sizeof(int));
    char *context = (char *)calloc(1, context_capacity);
    if (baseline) {
        free(context);
        context = baseline_context(fragments, fragment_count, budget);
        context_tokens = word_count(context);
    }
    for (size_t i = 0; !baseline && i < ranked_count; i++) {
        Fragment *fragment = ranked[i];
        if (context_tokens + fragment->token_count > budget) continue;
        selected_flags[i] = 1;
        size_t needed = strlen(context) + strlen(fragment->text) + (selected_count ? 2 : 1);
        if (needed > context_capacity) {
            context_capacity = needed * 2;
            char *grown = (char *)realloc(context, context_capacity);
            if (!grown) fail("out of memory");
            context = grown;
        }
        if (selected_count) strcat(context, " ");
        strcat(context, fragment->text);
        context_tokens += fragment->token_count;
        selected_count++;
    }
    uint64_t expansion_assembly_ns = now_ns() - assembly_started;
    uint64_t elapsed_ns = now_ns() - started;

    uint64_t serialization_started = now_ns();
    printf("{\"input_id\":"); json_string(fixture_id);
    printf(",\"original_source_tokens\":%zu,\"question_tokens\":%zu,\"retrieved_addresses\":[", original_tokens, word_count(question));
    for (size_t i = 0; i < ranked_count; i++) { if (i) putchar(','); json_string(ranked[i]->address); }
    printf("],\"lookups\":[");
    for (size_t i = 0; !baseline && i < lookup_count; i++) {
        if (i) putchar(',');
        printf("{\"address\":"); json_string(lookups[i].address); printf(",\"text\":");
        if (lookups[i].resolved_text) json_string(lookups[i].resolved_text); else fputs("null", stdout);
        putchar('}');
    }
    printf("],\"expanded\":[");
    size_t emitted = 0;
    for (size_t i = 0; i < ranked_count; i++) {
        Fragment *fragment = ranked[i];
        if (!selected_flags[i]) continue;
        if (emitted++) putchar(',');
        printf("{\"address\":"); json_string(fragment->address); printf(",\"text\":"); json_string(fragment->text); putchar('}');
    }
    printf("],\"context\":"); json_string(context);
    printf(",\"context_tokens\":%zu,\"elapsed_ns\":%llu}\n", context_tokens, (unsigned long long)elapsed_ns);
    fflush(stdout);
    uint64_t serialization_ns = now_ns() - serialization_started;
    fprintf(stderr, "ASM-BENCH-METRICS {\"input_parse_ns\":%llu,\"retrieval_ns\":%llu,\"address_lookup_ns\":%llu,\"expansion_assembly_ns\":%llu,\"serialization_ns\":%llu}\n",
        (unsigned long long)parsing_ns, (unsigned long long)retrieval_ns, (unsigned long long)address_lookup_ns,
        (unsigned long long)expansion_assembly_ns, (unsigned long long)serialization_ns);

    wordset_free(&query_words);
    for (size_t i = 0; i < fragment_count; i++) { free(fragments[i].address); free(fragments[i].text); }
    for (size_t i = 0; i < lookup_count; i++) free(lookups[i].address);
    free(fixture_id); free(question); free(fragments); free(lookups); free(ranked); free(selected_flags); free(context);
    return 0;
}
