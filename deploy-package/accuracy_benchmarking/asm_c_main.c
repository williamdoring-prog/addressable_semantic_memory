#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

#include "asm_c.h"

typedef struct {
    unsigned long long ticks;
} TimerRaw;

/* Captures a raw tick value; the delta is converted to ns afterwards so that
   huge absolute counter values cannot overflow during conversion. */
static TimerRaw timer_now(void) {
    TimerRaw raw;
#ifdef _WIN32
    LARGE_INTEGER counter;
    QueryPerformanceCounter(&counter);
    raw.ticks = (unsigned long long)counter.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    raw.ticks = (unsigned long long)ts.tv_sec * 1000000000ULL + (unsigned long long)ts.tv_nsec;
#endif
    return raw;
}

static unsigned long long timer_elapsed_ns(TimerRaw start, TimerRaw end) {
#ifdef _WIN32
    LARGE_INTEGER freq;
    QueryPerformanceFrequency(&freq);
    return (end.ticks - start.ticks) * 1000000000ULL / (unsigned long long)freq.QuadPart;
#else
    return end.ticks - start.ticks;
#endif
}

/* Input-file mode (challenge, WORKQUEUE W4). Line format:
   1: question ("\t"/"\n" escapes), 2: default budget, 3..N: address\011text.
   Parsing happens before the timed section; ASM_run (algorithm +
   serialization) is the only timed work, identical to the other languages. */
static void unescape_inplace(char *s) {
    size_t read_cursor = 0;
    size_t write_cursor = 0;
    while (s[read_cursor] != '\0') {
        if (s[read_cursor] == '\\' && s[read_cursor + 1] != '\0') {
            char next = s[read_cursor + 1];
            if (next == 't') { s[write_cursor++] = '\t'; read_cursor += 2; continue; }
            if (next == 'n') { s[write_cursor++] = '\n'; read_cursor += 2; continue; }
            if (next == '\\') { s[write_cursor++] = '\\'; read_cursor += 2; continue; }
        }
        s[write_cursor++] = s[read_cursor++];
    }
    s[write_cursor] = '\0';
}

static void strip_eol(char *line, char *const *limit_end) {
    (void)limit_end;
    size_t length = strlen(line);
    while (length > 0 && (line[length - 1] == '\r' || line[length - 1] == '\n')) {
        line[--length] = '\0';
    }
}

static int run_file(const char *path, const char *budget_arg) {
    FILE *file = fopen(path, "rb");
    if (!file) {
        fprintf(stderr, "cannot open input file: %s\n", path);
        return 2;
    }
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);
    if (file_size < 0) {
        fclose(file);
        fprintf(stderr, "cannot size input file: %s\n", path);
        return 2;
    }
    char *buffer = malloc((size_t)file_size + 1);
    if (!buffer) {
        fclose(file);
        fprintf(stderr, "out of memory reading input file\n");
        return 2;
    }
    size_t read_size = fread(buffer, 1, (size_t)file_size, file);
    fclose(file);
    buffer[read_size] = '\0';

    /* Line 1: question (strip EOL, unescape in place). */
    char *question = buffer;
    char *newline = strchr(buffer, '\n');
    char *cursor;
    if (newline) {
        *newline = '\0';
        cursor = newline + 1;
    } else {
        cursor = buffer + read_size;
    }
    strip_eol(question, NULL);
    unescape_inplace(question);

    /* Line 2: default budget. */
    char *budget_line = cursor;
    newline = strchr(cursor, '\n');
    if (newline) {
        *newline = '\0';
        cursor = newline + 1;
    } else {
        cursor = buffer + read_size;
    }
    strip_eol(budget_line, NULL);
    unsigned long long default_budget = strtoull(budget_line, NULL, 10);
    unsigned long long budget = budget_arg
        ? strtoull(budget_arg, NULL, 10)
        : default_budget;

    /* Lines 3..N: count non-empty lines for the fragment array upper bound. */
    char *endbuf = buffer + read_size;
    size_t capacity = 0;
    for (char *p = cursor; p < endbuf; ++p) {
        if (*p == '\n') ++capacity;
    }
    capacity += 2;
    Fragment *fragments = malloc(sizeof(Fragment) * capacity);
    if (!fragments) {
        free(buffer);
        fprintf(stderr, "out of memory allocating fragments\n");
        return 2;
    }
    size_t fragment_count = 0;
    while (cursor < endbuf) {
        char *line = cursor;
        newline = strchr(cursor, '\n');
        if (newline) {
            *newline = '\0';
            cursor = newline + 1;
        } else {
            cursor = endbuf;
        }
        strip_eol(line, NULL);
        char *tab = strchr(line, '\t');
        if (!tab || tab == line) {
            continue;
        }
        *tab = '\0';
        fragments[fragment_count].address = line;
        fragments[fragment_count].text = tab + 1;
        ++fragment_count;
    }

    ASM instance = {
        question,
        fragments,
        fragment_count,
        (size_t)budget
    };

    /* Timed: algorithm + serialization. Output happens after the timer. */
    TimerRaw start = timer_now();
    char *json = ASM_run(&instance);
    TimerRaw end = timer_now();

    if (json) {
        fputs(json, stdout);
        putchar('\n');
        free(json);
    }

    fprintf(stderr, "BENCHMARK_NS %llu\n", timer_elapsed_ns(start, end));
    free(fragments);
    free(buffer);
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 2) {
        return run_file(argv[1], argc >= 3 ? argv[2] : NULL);
    }

    Fragment fragments[] = {
        {"architecture", "ASM uses deterministic retrieval and bounded context assembly."},
        {"memory", "Persistent memory should preserve important project state across sessions."},
        {"retrieval", "Retrieval ranks relevant fragments using question term overlap."},
        {"voice", "Voice output should remain responsive and interruptible."},
        {"safety", "Snapshots validation and rollback protect autonomous project changes."},
        {"research", "Research agents can investigate new techniques and report evidence."}
    };

    ASM instance = {
        "How does ASM retrieve relevant context and keep the context bounded?",
        fragments,
        sizeof(fragments)/sizeof(fragments[0]),
        28
    };

    /* Timed: algorithm + serialization. Output happens after the timer. */
    TimerRaw start = timer_now();
    char *json = ASM_run(&instance);
    TimerRaw end = timer_now();

    fputs(json, stdout);
    putchar('\n');
    free(json);

    fprintf(stderr, "BENCHMARK_NS %llu\n", timer_elapsed_ns(start, end));
    return 0;
}
