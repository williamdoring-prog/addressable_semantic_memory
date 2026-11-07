package main

import (
	"sort"
	"strings"
)

type Fragment struct {
	Address string
	Text    string
}

type ASM struct {
	Question  string
	Fragments []Fragment
	Budget    int
}

type ranked struct {
	fragment Fragment
	words    int
	score    int
}

// ASCII word splitting, matching the tokenizer used by the other
// implementations ([A-Za-z0-9]+ runs, lowercased).
func words(text string) []string {
	var out []string
	var b strings.Builder
	for _, r := range text {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') {
			if r >= 'A' && r <= 'Z' {
				r += 'a' - 'A'
			}
			b.WriteRune(r)
		} else if b.Len() > 0 {
			out = append(out, b.String())
			b.Reset()
		}
	}
	if b.Len() > 0 {
		out = append(out, b.String())
	}
	return out
}

func (a ASM) Run() map[string]interface{} {
	query := map[string]bool{}
	for _, w := range words(a.Question) {
		query[w] = true
	}

	rankedItems := []ranked{}
	originalWords := 0

	for _, f := range a.Fragments {
		ws := words(f.Text)
		originalWords += len(ws)
		seen := map[string]bool{}
		score := 0
		for _, w := range ws {
			if !seen[w] && query[w] {
				seen[w] = true
				score++
			}
		}
		if score > 0 {
			rankedItems = append(rankedItems, ranked{f, len(ws), score})
		}
	}

	sort.Slice(rankedItems, func(i, j int) bool {
		if rankedItems[i].score != rankedItems[j].score {
			return rankedItems[i].score > rankedItems[j].score
		}
		return rankedItems[i].fragment.Address < rankedItems[j].fragment.Address
	})

	addresses := []string{}
	selected := []map[string]interface{}{}
	contextParts := []string{}
	contextWords := 0

	for _, item := range rankedItems {
		addresses = append(addresses, item.fragment.Address)
		if contextWords+item.words > a.Budget {
			continue
		}
		contextWords += item.words
		contextParts = append(contextParts, item.fragment.Text)
		selected = append(selected, map[string]interface{}{
			"address": item.fragment.Address,
			"score":   item.score,
		})
	}

	return map[string]interface{}{
		"original_source_words": originalWords,
		"question_words":        len(words(a.Question)),
		"retrieved_addresses":   addresses,
		"selected":              selected,
		"context":               strings.Join(contextParts, " "),
		"context_words":         contextWords,
	}
}
