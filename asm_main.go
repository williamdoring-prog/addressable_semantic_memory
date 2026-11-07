package main

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

func main() {
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
