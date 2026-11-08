package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sort"
	"strconv"
	"strings"
)

type fragment struct {
	address string
	text    string
	score   int
	tokens  int
}

type lookup struct {
	Address string  `json:"address"`
	Text    *string `json:"text"`
}

type expandedFragment struct {
	Address string `json:"address"`
	Text    string `json:"text"`
}

type result struct {
	InputID            string             `json:"input_id"`
	OriginalSource     int                `json:"original_source_tokens"`
	QuestionTokens     int                `json:"question_tokens"`
	RetrievedAddresses []string           `json:"retrieved_addresses"`
	Lookups            []lookup           `json:"lookups"`
	Expanded           []expandedFragment `json:"expanded"`
	Context            string             `json:"context"`
	ContextTokens      int                `json:"context_tokens"`
	ElapsedNS          int64              `json:"elapsed_ns"`
}

type operationMetrics struct {
	InputParseNS        int64 `json:"input_parse_ns"`
	RetrievalNS         int64 `json:"retrieval_ns"`
	AddressLookupNS     int64 `json:"address_lookup_ns"`
	ExpansionAssemblyNS int64 `json:"expansion_assembly_ns"`
	SerializationNS     int64 `json:"serialization_ns"`
}

func fail(message string) {
	fmt.Fprintln(os.Stderr, message)
	os.Exit(1)
}

func unescape(value string) (string, error) {
	var output strings.Builder
	for index := 0; index < len(value); index++ {
		if value[index] != '\\' {
			output.WriteByte(value[index])
			continue
		}
		index++
		if index == len(value) {
			return "", fmt.Errorf("invalid trailing escape")
		}
		switch value[index] {
		case '\\':
			output.WriteByte('\\')
		case 't':
			output.WriteByte('\t')
		case 'n':
			output.WriteByte('\n')
		case 'r':
			output.WriteByte('\r')
		default:
			return "", fmt.Errorf("invalid escape sequence")
		}
	}
	return output.String(), nil
}

func tokens(value string) []string {
	words := make([]string, 0)
	for index := 0; index < len(value); {
		current := value[index]
		if !asciiAlphanumeric(current) {
			index++
			continue
		}
		start := index
		for index < len(value) && asciiAlphanumeric(value[index]) {
			index++
		}
		word := []byte(value[start:index])
		for position, char := range word {
			if char >= 'A' && char <= 'Z' {
				word[position] = char + ('a' - 'A')
			}
		}
		words = append(words, string(word))
	}
	return words
}

func truncateToBudget(value string, budget int) string {
	count := 0
	inWord := false
	for index := 0; index < len(value); index++ {
		word := asciiAlphanumeric(value[index])
		if word && !inWord {
			count++
			if count == budget {
				end := index + 1
				for end < len(value) && asciiAlphanumeric(value[end]) { end++ }
				return value[:end]
			}
		}
		inWord = word
	}
	return value
}

func asciiAlphanumeric(value byte) bool {
	return value >= 'A' && value <= 'Z' || value >= 'a' && value <= 'z' || value >= '0' && value <= '9'
}

func distinct(values []string) map[string]bool {
	set := make(map[string]bool, len(values))
	for _, value := range values {
		set[value] = true
	}
	return set
}

func parse(input string) (string, string, int, []string, []fragment, error) {
	reader := bufio.NewReader(strings.NewReader(input))
	header, err := reader.ReadString('\n')
	if err != nil && err != io.EOF {
		return "", "", 0, nil, nil, err
	}
	header = strings.TrimSuffix(strings.TrimSuffix(header, "\n"), "\r")
	if header != "ASM-BENCH-V1" {
		return "", "", 0, nil, nil, fmt.Errorf("invalid input header")
	}
	id, question, budget := "", "", 0
	lookups := make([]string, 0)
	fragments := make([]fragment, 0)
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 1024), 16*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSuffix(scanner.Text(), "\r")
		if line == "" {
			continue
		}
		fields := strings.SplitN(line, "\t", 3)
		if len(fields) < 2 {
			return "", "", 0, nil, nil, fmt.Errorf("record is missing tab separators")
		}
		switch fields[0] {
		case "fragment":
			if len(fields) != 3 {
				return "", "", 0, nil, nil, fmt.Errorf("fragment record requires address and text")
			}
			address, addressErr := unescape(fields[1])
			text, textErr := unescape(fields[2])
			if addressErr != nil || textErr != nil {
				return "", "", 0, nil, nil, fmt.Errorf("invalid fragment escape")
			}
			fragments = append(fragments, fragment{address: address, text: text})
		case "lookup":
			value, unescapeErr := unescape(fields[1])
			if unescapeErr != nil {
				return "", "", 0, nil, nil, unescapeErr
			}
			lookups = append(lookups, value)
		case "id":
			id, err = unescape(fields[1])
		case "question":
			question, err = unescape(fields[1])
		case "budget":
			budget, err = strconv.Atoi(fields[1])
			if err == nil && budget < 1 {
				err = fmt.Errorf("budget must be a positive integer")
			}
		default:
			return "", "", 0, nil, nil, fmt.Errorf("unknown record type")
		}
		if err != nil {
			return "", "", 0, nil, nil, fmt.Errorf("invalid %s record: %w", fields[0], err)
		}
	}
	if err := scanner.Err(); err != nil {
		return "", "", 0, nil, nil, err
	}
	if id == "" || question == "" || budget < 1 || len(fragments) == 0 {
		return "", "", 0, nil, nil, fmt.Errorf("fixture requires id, question, positive budget, and fragments")
	}
	seen := make(map[string]bool, len(fragments))
	for _, item := range fragments {
		if seen[item.address] {
			return "", "", 0, nil, nil, fmt.Errorf("duplicate fragment address")
		}
		seen[item.address] = true
	}
	return id, question, budget, lookups, fragments, nil
}

func run(input string, started timerStart, strategy string) (result, operationMetrics, error) {
	var timings operationMetrics
	parseStarted := started
	id, question, budget, lookupAddresses, fragments, err := parse(input)
	if err != nil {
		return result{}, timings, err
	}
	timings.InputParseNS = elapsedNS(parseStarted)
	out := result{
		InputID:            id,
		OriginalSource:     0,
		QuestionTokens:     len(tokens(question)),
		RetrievedAddresses: make([]string, 0),
		Lookups:            make([]lookup, 0),
		Expanded:           make([]expandedFragment, 0),
	}
	if strategy == "baseline" {
		assemblyStarted := monotonicStart()
		parts := make([]string, 0, len(fragments))
		for _, item := range fragments {
			out.OriginalSource += len(tokens(item.text))
			parts = append(parts, item.text)
		}
		out.Context = truncateToBudget(strings.Join(parts, " "), budget)
		out.ContextTokens = len(tokens(out.Context))
		out.ElapsedNS = elapsedNS(started)
		timings.ExpansionAssemblyNS = elapsedNS(assemblyStarted)
		return out, timings, nil
	}
	retrievalStarted := monotonicStart()
	query := distinct(tokens(question))
	for index := range fragments {
		fragmentWords := tokens(fragments[index].text)
		terms := distinct(fragmentWords)
		fragments[index].tokens = len(fragmentWords)
		out.OriginalSource += fragments[index].tokens
		for term := range query {
			if terms[term] {
				fragments[index].score++
			}
		}
	}
	ranked := make([]fragment, 0, len(fragments))
	for _, item := range fragments {
		if item.score > 0 {
			ranked = append(ranked, item)
		}
	}
	sort.Slice(ranked, func(i, j int) bool {
		if ranked[i].score != ranked[j].score {
			return ranked[i].score > ranked[j].score
		}
		return ranked[i].address < ranked[j].address
	})
	timings.RetrievalNS = elapsedNS(retrievalStarted)
	lookupStarted := monotonicStart()
	lookupText := make(map[string]string, len(fragments))
	for _, item := range fragments {
		lookupText[item.address] = item.text
	}
	for _, address := range lookupAddresses {
		item := lookup{Address: address}
		if text, ok := lookupText[address]; ok {
			copyText := text
			item.Text = &copyText
		}
		out.Lookups = append(out.Lookups, item)
	}
	timings.AddressLookupNS = elapsedNS(lookupStarted)
	assemblyStarted := monotonicStart()
	contextParts := make([]string, 0)
	for _, item := range ranked {
		out.RetrievedAddresses = append(out.RetrievedAddresses, item.address)
		if out.ContextTokens+item.tokens > budget {
			continue
		}
		out.Expanded = append(out.Expanded, expandedFragment{Address: item.address, Text: item.text})
		contextParts = append(contextParts, item.text)
		out.ContextTokens += item.tokens
	}
	out.Context = strings.Join(contextParts, " ")
	timings.ExpansionAssemblyNS = elapsedNS(assemblyStarted)
	out.ElapsedNS = elapsedNS(started)
	return out, timings, nil
}

func main() {
	started := monotonicStart()
	strategy := "asm"
	if len(os.Args) > 2 { strategy = os.Args[2] }
	if strategy != "asm" && strategy != "baseline" { fail("strategy must be asm or baseline") }
	var source []byte
	var err error
	if len(os.Args) > 1 {
		source, err = os.ReadFile(os.Args[1])
	} else {
		source, err = io.ReadAll(os.Stdin)
	}
	if err != nil {
		fail("could not read benchmark fixture")
	}
	output, timings, err := run(string(source), started, strategy)
	if err != nil {
		fail(err.Error())
	}
	serializationStarted := monotonicStart()
	serialized, err := json.Marshal(output)
	if err != nil {
		fail("could not serialize benchmark output")
	}
	if _, err := os.Stdout.Write(append(serialized, '\n')); err != nil {
		fail("could not write benchmark output")
	}
	timings.SerializationNS = elapsedNS(serializationStarted)
	metricsJSON, err := json.Marshal(timings)
	if err != nil {
		fail("could not serialize operation metrics")
	}
	fmt.Fprintf(os.Stderr, "ASM-BENCH-METRICS %s\n", metricsJSON)
}
