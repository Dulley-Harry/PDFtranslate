from __future__ import annotations

import unittest

from pdftranslate.codex_cli import build_prompt


class BuildPromptTests(unittest.TestCase):
    def test_prompt_marks_source_as_untrusted_and_preserves_placeholders(self) -> None:
        prompt = build_prompt(
            "TP53 {v1} PMID:12345",
            source_language="English",
            target_language="Simplified Chinese",
        )
        self.assertIn("untrusted plain text", prompt)
        self.assertIn("TP53 {v1} PMID:12345", prompt)
        self.assertIn("Simplified Chinese", prompt)

    def test_prompt_requests_translation_only(self) -> None:
        prompt = build_prompt(
            "Example sentence.",
            source_language="English",
            target_language="Simplified Chinese",
        )
        self.assertIn("Output the translation only", prompt)


if __name__ == "__main__":
    unittest.main()
