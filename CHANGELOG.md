# Changelog

All notable changes to PDFtranslate are documented here.

## 1.0.0 - 2026-09-01

### Added

- End-to-end `pdftranslate-pdf` command for academic PDF translation.
- Local OpenAI-compatible batching bridge backed by authenticated `codex exec`.
- Direct stdin/stdout Codex fallback adapter.
- Zotero desktop adapter with right-click translation and translated attachment import.
- Obsidian desktop adapter with command-palette, ribbon, and PDF context-menu entry points.
- Zotero JSON update-manifest support.
- Reproducible Obsidian dependency lockfile and `npm ci` builds.
- GitHub release automation for Python, Zotero, and Obsidian artifacts.

### Changed

- Reduced the default bridge batch size from 8 to 4 after real-world long-document testing.
- Propagate an enabled Windows WinINET proxy to Codex subprocesses when proxy environment variables are not already set.
- Keep JSON-mode stdout machine-readable while routing dependency noise to stderr.
- Harden Obsidian JSON result parsing with UTF-8 decoding, result-contract validation, noisy-stdout recovery, and actionable diagnostics.

### Validated

- Python 3.11 / 3.12 / 3.13 automated test suite.
- Real Windows CLI translation with a signed-in Codex Desktop CLI.
- Real bilingual scientific PDF generation.
- Zotero 9.0.6 install, right-click translation, and translated attachment import.
- Obsidian desktop install, translation into the active vault, and opening the generated PDF.

### Security

- Codex authentication remains owned by the installed Codex CLI.
- No API key or Codex credential file is read, copied, committed, or uploaded by PDFtranslate.
- Persistent bridge access remains loopback-only with a local bearer token.
