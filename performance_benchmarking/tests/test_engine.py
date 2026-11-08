import unittest

from asm.engine import ASMEngine, AddressNotFoundError, prepare_asm, tokenize


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.source = "Mira designed the amber telescope. It weighs 4 kilograms. It must remain dry."
        self.engine = ASMEngine()
        self.fragments = self.engine.ingest(self.source)
        self.representations = self.engine.compress()

    def test_source_is_unchanged_and_addresses_are_stable(self):
        again = ASMEngine()
        self.assertEqual(again.ingest(self.source), self.fragments)
        self.assertEqual(self.engine.source_text, self.source)
        self.assertEqual(len({f.address for f in self.fragments}), len(self.fragments))
        self.assertEqual("".join(fragment.text for fragment in self.fragments), self.source)
        restored = self.engine.expand(fragment.address for fragment in self.fragments)
        self.assertEqual("".join(fragment.text for fragment in restored), self.source)

    def test_duplicate_text_resolves_to_all_occurrences(self):
        engine = ASMEngine()
        fragments = engine.ingest("Same sentence. Same sentence.")
        self.assertEqual(engine.address("Same sentence."), (fragments[0].address, fragments[1].address))

    def test_semantic_representation_requires_complete_valid_provenance(self):
        addresses = [fragment.address for fragment in self.fragments]
        summary = "Mira's amber telescope weighs four kilograms and must stay dry."
        semantic = self.engine.compress([{"addresses": addresses, "text": summary}])
        self.assertEqual(semantic[0].method, "local-model-semantic")
        self.assertEqual(semantic[0].addresses, tuple(addresses))
        self.assertEqual(self.engine.expand(semantic[0].addresses), self.fragments)
        assembled = self.engine.assemble("How heavy is the telescope?", 64, expand_sources=False)
        self.assertEqual(assembled["context"], summary)
        self.assertEqual(assembled["selected"][0]["expanded"], [])
        self.assertLess(assembled["token_count"], len(tokenize(self.source)))
        with self.assertRaisesRegex(ValueError, "omit source addresses"):
            self.engine.compress([{"addresses": [addresses[0]], "text": "Partial summary"}])
        with self.assertRaisesRegex(ValueError, "unknown addresses"):
            self.engine.compress([{"addresses": ["src:fake:000000"], "text": "Invalid summary"}])

    def test_retrieval_expands_exact_original_fragment(self):
        results = self.engine.retrieve("How many kilograms?")
        self.assertTrue(results)
        expanded = self.engine.expand(results[0].addresses)
        self.assertEqual(expanded[0].text.strip(), "It weighs 4 kilograms.")

    def test_duplicate_expansions_are_deduplicated(self):
        address = self.fragments[0].address
        self.assertEqual(self.engine.expand([address, address]), [self.fragments[0]])

    def test_unknown_address_fails_explicitly(self):
        with self.assertRaises(AddressNotFoundError):
            self.engine.expand(["src:missing:000001"])

    def test_assembly_respects_token_budget(self):
        _, assembled, metrics = prepare_asm(self.source, "telescope", 7)
        self.assertLessEqual(assembled["token_count"], 7)
        self.assertEqual(assembled["question_tokens"], len(tokenize("telescope")))
        self.assertEqual(metrics["addresses_created"], len(self.fragments))
        self.assertEqual(assembled["tokenizer"], "ASM word/punctuation tokenizer v1")
        for field in ("source_fragmentation_time_ms", "representation_indexing_time_ms", "retrieval_time_ms", "expansion_time_ms", "context_assembly_time_ms"):
            self.assertGreaterEqual(metrics[field], 0)

    def test_tokenizer_counts_words_and_punctuation(self):
        self.assertEqual(tokenize("ASM works!"), ["ASM", "works", "!"])


if __name__ == "__main__":
    unittest.main()
