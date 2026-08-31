# Phase 1: PDF2zh Next + Codex CLI integration

This phase wires the existing `pdftranslate-codex` stdin/stdout translator into PDFMathTranslate Next's generic `CLITranslator` backend.

## Runtime boundary

```text
input.pdf
  -> PDFMathTranslate Next / BabelDOC
  -> CLITranslator
  -> pdftranslate-codex
  -> codex exec
  -> translated text
  -> BabelDOC typesetting
  -> mono/dual PDF
```

The repository never stores Codex authentication. `codex exec` reuses the user's existing local Codex CLI login.

## Target

A local command should be able to run:

```bash
pdftranslate-pdf input.pdf --output-dir translated
```

and obtain a bilingual PDF plus, optionally, a Chinese monolingual PDF.

The Zotero and Obsidian adapters will call this same local command in later phases.
