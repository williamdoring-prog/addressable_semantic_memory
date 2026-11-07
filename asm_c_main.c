#include <stdio.h>
#include <stdlib.h>

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

int main(void) {
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
