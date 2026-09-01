from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from pdftranslate.codex_cli import build_codex_command
from pdftranslate.codex_cli import build_prompt
from pdftranslate.codex_cli import codex_subprocess_env
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


class CodexEnvironmentTests(unittest.TestCase):
    def test_existing_proxy_environment_is_preserved(self) -> None:
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://existing:8080"}, clear=True):
            with patch(
                "pdftranslate.codex_cli._read_windows_proxy",
                return_value="127.0.0.1:7897",
            ):
                env = codex_subprocess_env()
        self.assertEqual(env["HTTPS_PROXY"], "http://existing:8080")
        self.assertNotIn("HTTP_PROXY", env)

    def test_enabled_single_windows_proxy_is_forwarded_to_codex(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "pdftranslate.codex_cli._read_windows_proxy",
                return_value="127.0.0.1:7897",
            ):
                env = codex_subprocess_env()
        self.assertEqual(env["HTTP_PROXY"], "http://127.0.0.1:7897")
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:7897")
        self.assertEqual(env["ALL_PROXY"], "http://127.0.0.1:7897")

    def test_protocol_specific_windows_proxy_is_normalized(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "pdftranslate.codex_cli._read_windows_proxy",
                return_value="http=proxy.local:8080;https=secure.local:8443",
            ):
                env = codex_subprocess_env()
        self.assertEqual(env["HTTP_PROXY"], "http://proxy.local:8080")
        self.assertEqual(env["HTTPS_PROXY"], "http://secure.local:8443")


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
