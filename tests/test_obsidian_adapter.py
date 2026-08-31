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


if __name__ == "__main__":
    unittest.main()
