from __future__ import annotations

from pathlib import Path
import unittest

from pdftranslate.codex_cli import build_codex_command
from pdftranslate.codex_cli import build_prompt
from pdftranslate.codex_cli import parse_translation_output


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

    def test_prompt_requests_schema_only_translation(self) -> None:
        prompt = build_prompt(
            "Example sentence.",
            source_language="English",
            target_language="Simplified Chinese",
        )
        self.assertIn("required structured-output field", prompt)


class CodexCommandTests(unittest.TestCase):
    def test_command_uses_ephemeral_read_only_automation(self) -> None:
        command = build_codex_command(
            "/usr/bin/codex",
            schema_path=Path("/tmp/schema.json"),
            model=None,
        )
        self.assertIn("--ephemeral", command)
        self.assertIn("read-only", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--output-schema", command)
        self.assertEqual(command[-1], "-")
        self.assertNotIn("auth.json", " ".join(command))

    def test_model_override_is_explicit(self) -> None:
        command = build_codex_command(
            "codex",
            schema_path=Path("schema.json"),
            model="example-model",
        )
        self.assertIn("--model", command)
        self.assertIn("example-model", command)


class StructuredOutputTests(unittest.TestCase):
    def test_parse_translation(self) -> None:
        self.assertEqual(
            parse_translation_output('{"translation":"中文译文"}'),
            "中文译文",
        )

    def test_reject_empty_translation(self) -> None:
        with self.assertRaises(Exception):
            parse_translation_output('{"translation":""}')


if __name__ == "__main__":
    unittest.main()
