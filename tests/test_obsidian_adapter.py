from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "obsidian"


class ObsidianAdapterTests(unittest.TestCase):
    def test_manifest_is_desktop_only(self) -> None:
        manifest = json.loads((ADAPTER / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"], "pdftranslate")
        self.assertTrue(manifest["isDesktopOnly"])

    def test_adapter_uses_execfile_and_local_pdftranslate(self) -> None:
        source = (ADAPTER / "src" / "main.ts").read_text(encoding="utf-8")
        self.assertIn("execFile", source)
        self.assertIn("pdftranslate-pdf", source)
        self.assertIn("--json", source)
        self.assertIn("FileSystemAdapter", source)
        self.assertNotIn("exec(", source)
        self.assertNotIn("shell: true", source)

    def test_adapter_contains_no_model_credentials(self) -> None:
        source = (ADAPTER / "src" / "main.ts").read_text(encoding="utf-8")
        forbidden = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "auth.json",
            "ChatGPT password",
        ]
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_output_directory_is_constrained_to_vault(self) -> None:
        source = (ADAPTER / "src" / "main.ts").read_text(encoding="utf-8")
        self.assertIn("isInside", source)
        self.assertIn("Output folder cannot leave the current Obsidian vault", source)

    def test_json_parser_is_utf8_explicit_and_contract_checked(self) -> None:
        source = (ADAPTER / "src" / "main.ts").read_text(encoding="utf-8")
        self.assertIn("encoding: 'utf8'", source)
        self.assertIn("parseTranslationResult(stdout, stderr)", source)
        self.assertIn("input_pdf must be a non-empty string", source)
        self.assertIn("mono_pdf and dual_pdf cannot both be null", source)
        self.assertNotIn("JSON.parse(stdout.trim())", source)

    def test_json_failures_include_both_process_streams(self) -> None:
        source = (ADAPTER / "src" / "main.ts").read_text(encoding="utf-8")
        self.assertIn("PDFtranslate JSON parse failed:", source)
        self.assertIn("PDFtranslate JSON contract violation:", source)
        self.assertIn("streamDiagnostic('stdout', stdout)", source)
        self.assertIn("streamDiagnostic('stderr', stderr)", source)
        self.assertIn("Recovered final JSON object from noisy stdout", source)


if __name__ == "__main__":
    unittest.main()
