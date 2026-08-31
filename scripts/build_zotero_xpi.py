#!/usr/bin/env python3
"""Build the development Zotero XPI from adapters/zotero/addon."""

from __future__ import annotations

from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "adapters" / "zotero" / "addon"
DIST = ROOT / "dist"
OUTPUT = DIST / "PDFtranslate-zotero.xpi"


def main() -> int:
    if not (ADDON / "manifest.json").is_file():
        raise SystemExit(f"Zotero addon source not found: {ADDON}")
    DIST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ADDON.rglob("*")):
            if not path.is_file() or path.name in {".DS_Store", "Thumbs.db"}:
                continue
            archive.write(path, path.relative_to(ADDON).as_posix())
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
