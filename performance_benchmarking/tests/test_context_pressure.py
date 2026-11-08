import unittest

from asm.engine import ASMEngine, tokenize
from benchmarks.run_context_pressure import build_source


class ContextPressureFixtureTests(unittest.TestCase):
    def test_fixture_is_deterministic_and_larger_than_largest_configured_budget(self):
        source = build_source()
        self.assertEqual(source, build_source())
        self.assertGreater(len(tokenize(source)), 8192)

    def test_multihop_evidence_is_spread_across_the_source(self):
        source = build_source()
        positions = [
            source.index("Project Orion was initially assigned Component Delta."),
            source.index("Component Delta was replaced by Component Sigma in the final deployment."),
            source.index("Component Delta requires 8 GB of memory; this is a superseded specification."),
            source.index("Component Sigma, the current component assigned to Project Orion, requires 16 GB of memory."),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(positions[0] / len(source), 0.05)
        self.assertGreater(positions[-1] / len(source), 0.9)

    def test_evidence_fragments_remain_addressable_verbatim(self):
        source = build_source()
        engine = ASMEngine()
        fragments = engine.ingest(source)
        first_fact_fragment = engine.resolve(fragments[2].address).text
        self.assertEqual(first_fact_fragment.strip(),
                         "Project Orion was initially assigned Component Delta.")
        self.assertIn(first_fact_fragment, source)
        fragment_texts = [fragment.text.strip() for fragment in fragments]
        self.assertIn("Component Delta was replaced by Component Sigma in the final deployment.", fragment_texts)
        self.assertIn("Component Sigma, the current component assigned to Project Orion, requires 16 GB of memory.",
                      fragment_texts)


if __name__ == "__main__":
    unittest.main()
