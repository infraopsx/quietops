"""Keep DEV competition article code fences compatible with its Markdown renderer."""
from pathlib import Path
import unittest


ARTICLE = Path(__file__).resolve().parents[1] / "submissions" / "dev-week3.md"


class TestSubmissionFormatting(unittest.TestCase):
    def test_fences_are_balanced_and_use_backticks(self):
        body = ARTICLE.read_text(encoding="utf-8")
        self.assertNotIn("~~~", body, "DEV template rendering may expose tilde fences")
        fences = [line for line in body.splitlines() if line.startswith("```")]
        self.assertGreaterEqual(len(fences), 6)
        self.assertEqual(len(fences) % 2, 0)
        for start, end in zip(fences[::2], fences[1::2]):
            self.assertRegex(start, r"^```(?:bash|text)$")
            self.assertEqual(end, "```")

    def test_live_demo_and_source_remain_present(self):
        body = ARTICLE.read_text(encoding="utf-8")
        self.assertIn("https://infraopsx.github.io/quietops/", body)
        self.assertIn("https://github.com/infraopsx/quietops/actions/workflows/live-gemma.yml", body)


if __name__ == "__main__":
    unittest.main()
