"""Reproducible rule-only benchmark; no claims about Gemma accuracy."""
import unittest
from quietops.cluster import analyze


def noisy_fixture():
    lines = []
    for i in range(15):
        lines.extend([f"worker{i} | WARNING retry queue slot {i}"] * (20 - i))
    lines.append("postgres | FATAL database corruption detected")
    return "\n".join(lines)


class TestRareCriticalSignals(unittest.TestCase):
    def test_frequency_baseline_misses_rare_fatal(self):
        raw = noisy_fixture()
        # A frequency-only top-12 selection misses the single fatal message.
        frequencies = {}
        for line in raw.splitlines():
            frequencies[line] = frequencies.get(line, 0) + 1
        baseline = sorted(frequencies, key=lambda line: -frequencies[line])[:12]
        self.assertFalse(any("corruption detected" in line for line in baseline))

    def test_critical_fatal_is_retained_and_cited(self):
        digest = analyze(noisy_fixture(), max_events=12)
        self.assertEqual(digest.unique_events, 16)
        self.assertEqual(len(digest.events), 12)
        critical = [e for e in digest.events if "corruption detected" in e.samples[0]]
        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0].count, 1)
        self.assertEqual(critical[0].severity, "error")

    def test_noncritical_frequency_ranking_is_preserved(self):
        raw = "\n".join(["worker | WARNING retrying queue"] * 12 +
                        ["api | ERROR upstream connection refused"] * 3 +
                        ["nginx | WARNING slow request"] * 1)
        digest = analyze(raw, max_events=2)
        self.assertEqual([e.count for e in digest.events], [12, 3])

    def test_critical_in_budget_is_not_added_twice(self):
        raw = "postgres | FATAL database corruption detected\napi | WARNING slow request"
        digest = analyze(raw, max_events=2)
        self.assertEqual(len(digest.events), 2)


if __name__ == "__main__":
    unittest.main()
