package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// unescape is a left-to-right scanner: \\t -> TAB, \\n -> NL, \\\\ -> backslash.
func unescape(s string) string {
	var out strings.Builder
	out.Grow(len(s))
	for i := 0; i < len(s); i++ {
		if s[i] == '\\' && i+1 < len(s) {
			switch s[i+1] {
			case 't':
				out.WriteByte('\t')
				i++
				continue
			case 'n':
				out.WriteByte('\n')
				i++
				continue
			case '\\':
				out.WriteByte('\\')
				i++
				continue
			}
		}
		out.WriteByte(s[i])
	}
	return out.String()
}

// splitLines splits on '\n' and strips trailing '\r' per line.
func splitLines(data string) []string {
	raw := strings.Split(data, "\n")
	out := make([]string, 0, len(raw))
	for _, line := range raw {
		out = append(out, strings.TrimSuffix(line, "\r"))
	}
	return out
}

// runFile implements input-file mode (challenge, WORKQUEUE W4): parsing
// happens before the timed section; asm.Run() + json.Marshal (algorithm +
// serialization) are the only timed work, identical to the other languages.
func runFile(path string, budgetArg string) {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "cannot open input file: %s\n", err)
		os.Exit(2)
	}

	lines := splitLines(string(data))
	question := unescape(lines[0])
	defaultBudget := 0
	if len(lines) > 1 {
		defaultBudget, _ = strconv.Atoi(strings.TrimSpace(lines[1]))
	}
	budget := defaultBudget
	if budgetArg != "" {
		value, convErr := strconv.Atoi(budgetArg)
		if convErr == nil {
			budget = value
		}
	}

	fragments := []Fragment{}
	for _, line := range lines[2:] {
		if line == "" {
			continue
		}
		tab := strings.IndexByte(line, '\t')
		if tab <= 0 {
			continue
		}
		fragments = append(fragments, Fragment{Address: line[:tab], Text: line[tab+1:]})
	}

	asm := ASM{Question: question, Budget: budget, Fragments: fragments}

	start := time.Now()
	result := asm.Run()
	jsonData, _ := json.Marshal(result)
	internal := time.Since(start).Nanoseconds()
	fmt.Println(string(jsonData))
	fmt.Fprintf(os.Stderr, "BENCHMARK_NS %d\n", internal)
}

func main() {
	args := os.Args[1:]
	if len(args) >= 1 {
		budgetArg := ""
		if len(args) >= 2 {
			budgetArg = args[1]
		}
		runFile(args[0], budgetArg)
		return
	}

	asm := ASM{
		Question: "How does ASM retrieve relevant context and keep the context bounded?",
		Budget:   28,
		Fragments: []Fragment{
			{"architecture", "ASM uses deterministic retrieval and bounded context assembly."},
			{"memory", "Persistent memory should preserve important project state across sessions."},
			{"retrieval", "Retrieval ranks relevant fragments using question term overlap."},
			{"voice", "Voice output should remain responsive and interruptible."},
			{"safety", "Snapshots validation and rollback protect autonomous project changes."},
			{"research", "Research agents can investigate new techniques and report evidence."},
		},
	}

	start := time.Now()
	result := asm.Run()
	data, _ := json.Marshal(result)
	internal := time.Since(start).Nanoseconds()
	fmt.Println(string(data))
	fmt.Fprintf(os.Stderr, "BENCHMARK_NS %d\n", internal)
}
