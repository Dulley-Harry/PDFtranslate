from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "adapters" / "zotero" / "addon"
UPDATES = ROOT / "adapters" / "zotero" / "updates.json"


class ZoteroAdapterTests(unittest.TestCase):
    def test_manifest_is_valid_and_targets_zotero_8_9(self) -> None:
        manifest = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))
        zotero = manifest["applications"]["zotero"]
        self.assertEqual(manifest["manifest_version"], 2)
        self.assertEqual(zotero["id"], "pdftranslate@dulley-harry.github.io")
        self.assertEqual(
            zotero["update_url"],
            "https://raw.githubusercontent.com/Dulley-Harry/PDFtranslate/main/"
            "adapters/zotero/updates.json",
        )
        self.assertEqual(zotero["strict_min_version"], "8.0")
        self.assertEqual(zotero["strict_max_version"], "9.0.*")

    def test_update_manifest_tracks_the_same_plugin_id(self) -> None:
        updates = json.loads(UPDATES.read_text(encoding="utf-8"))
        addon = updates["addons"]["pdftranslate@dulley-harry.github.io"]
        self.assertEqual(addon["updates"], [])

    def test_adapter_calls_only_local_pdftranslate_cli(self) -> None:
        source = (ADDON / "content" / "plugin.js").read_text(encoding="utf-8")
        self.assertIn("pdftranslate-pdf", source)
        self.assertIn('"--json"', source)
        self.assertIn("PDFTRANSLATE_PDF_EXECUTABLE", source)
        self.assertNotIn("OPENAI_API_KEY", source)
        self.assertNotIn("ANTHROPIC_API_KEY", source)
        self.assertNotIn("auth.json", source)

    def test_addon_can_be_packaged_with_manifest_at_xpi_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "adapter.xpi"
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in ADDON.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(ADDON).as_posix())
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("bootstrap.js", names)
            self.assertIn("content/plugin.js", names)
            self.assertIn("locale/en-US/pdftranslate.ftl", names)
            self.assertIn("locale/zh-CN/pdftranslate.ftl", names)


if __name__ == "__main__":
    unittest.main()
