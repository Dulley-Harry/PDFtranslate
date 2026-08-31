# PDFtranslate

Universal local PDF translation bridge for academic reading workflows.

## Goal

`PDFtranslate` is designed as a local translation core that can be called from Zotero, Obsidian, the command line, or other desktop tools.

The intended pipeline is:

```text
Zotero / Obsidian / CLI
          |
          v
     PDFtranslate
          |
          v
PDFMathTranslate Next + BabelDOC
          |
          v
     Codex CLI
   (`codex exec`)
          |
          v
 translated / bilingual PDF
```

The Codex path uses the locally installed and authenticated Codex CLI. It does not emulate the ChatGPT web application and does not require an OpenAI API key for the Codex CLI path.

## Design rules

- Keep the translation core independent from Zotero and Obsidian.
- Treat Zotero and Obsidian integrations as thin adapters.
- Reuse PDFMathTranslate Next / BabelDOC for PDF parsing, formulas, tables and typesetting instead of reimplementing PDF layout.
- Keep Codex invocation local and explicit through `codex exec`.
- Never read or copy `~/.codex/auth.json`.
- Never commit private PDFs, translated papers, API keys, or authentication material.
- Do not copy code from unlicensed reference repositories.

## Phase 0

The first milestone provides a small Codex CLI translator executable that reads source text from stdin and writes only the translation to stdout. This is intentionally compatible with PDFMathTranslate Next's generic CLI translator model.

Planned interfaces:

```text
core/
  Codex CLI adapter
  translation job contract
  cache / retry policy

adapters/
  zotero/
  obsidian/

future:
  localhost service
  Windows/macOS/Linux shell integration
```

## Status

Early development. Public repository; API and file layout may change before the first release.

## Upstream projects

This project is intended to interoperate with, but not vendor, the following projects:

- PDFMathTranslate Next
- BabelDOC
- Zotero
- Obsidian
- OpenAI Codex CLI

Their licenses and terms remain independent.
