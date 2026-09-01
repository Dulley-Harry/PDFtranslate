# PDFtranslate v1.0.0

First stable release of PDFtranslate.

## Highlights

- Local academic PDF translation through an authenticated OpenAI Codex CLI session; no OpenAI API key is required for the ChatGPT-managed Codex login path.
- PDFMathTranslate Next / BabelDOC integration for bilingual and Chinese-only PDF output.
- Persistent loopback bridge that batches PDF translation segments into fewer `codex exec` calls.
- Conservative default batching (`4` segments, `1` Codex worker) validated on real scientific PDFs.
- Windows proxy inheritance for Codex subprocesses without disabling TLS verification.
- Zotero desktop adapter:
  - right-click translation;
  - automatic bilingual PDF import as a child attachment;
  - Zotero 8/9 manifest compatibility;
  - automatic update manifest support.
- Obsidian desktop adapter:
  - command-palette, ribbon, and PDF context-menu entry points;
  - translated PDFs remain inside the active vault;
  - robust UTF-8 JSON result parsing with contract validation and diagnostics.
- Reproducible Obsidian builds through `package-lock.json` + `npm ci`.
- Python 3.11, 3.12, and 3.13 CI coverage.

## Real-machine validation completed

The v1.0 line has been exercised end-to-end on Windows with a signed-in Codex Desktop CLI:

- CLI text translation: PASS
- Full PDF translation: PASS
- Zotero 9.0.6 install and right-click PDF translation: PASS
- Zotero translated attachment import: PASS
- Obsidian desktop plugin install: PASS
- Obsidian PDF translation into the active vault: PASS
- Obsidian opening the generated bilingual PDF: PASS

## Release assets

- `PDFtranslate-zotero.xpi` — Zotero desktop plugin.
- `PDFtranslate-obsidian.zip` — Obsidian desktop plugin (`main.js` + `manifest.json`).
- `pdftranslate-1.0.0-py3-none-any.whl` — Python wheel.
- `pdftranslate-1.0.0.tar.gz` — Python source distribution.
- `SHA256SUMS.txt` — checksums for release artifacts.

## Compatibility

- Python: 3.11–3.13
- PDFMathTranslate Next: `>=2.9.0,<3.0`
- Zotero: 8.x and 9.0.x
- Obsidian: desktop only

Zotero 10 is not declared compatible in v1.0.0 because that release line has not yet been validated in a real Zotero 10 desktop session.

## Security boundary

PDFtranslate does not read, copy, commit, or upload Codex authentication files. Authentication remains owned by the installed Codex CLI. The localhost bridge binds to loopback only and uses an in-memory local bearer token by default.
