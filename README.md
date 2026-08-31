# PDFtranslate

Universal local PDF translation bridge for academic reading workflows.

`PDFtranslate` keeps the PDF/layout engine separate from desktop integrations so the same translation core can be called from Zotero, Obsidian, the command line, or other local tools.

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
  pdftranslate-codex
          |
          v
       codex exec
          |
          v
 translated / bilingual PDF
```

## Current status

Phase 1 implements the first end-to-end local path:

- `pdftranslate-codex`: stdin -> authenticated local Codex CLI -> translated stdout.
- `pdftranslate-pdf`: PDF -> PDFMathTranslate Next/BabelDOC -> Codex CLI -> translated PDF.
- Default PDF output mode is bilingual (`dual`).
- PDF2zh translation concurrency is deliberately fixed to one worker in this phase.
- Zotero and Obsidian adapters are not yet wired to the core.

The project interoperates with PDFMathTranslate Next rather than vendoring or modifying its source.

## Install for local development

Python 3.11-3.13 is supported by this repository. The PDF backend is an optional dependency.

```bash
git clone https://github.com/Dulley-Harry/PDFtranslate.git
cd PDFtranslate
python -m venv .venv
```

Activate the virtual environment, then install:

```bash
python -m pip install -U pip
python -m pip install -e ".[pdf]"
```

Install Codex CLI separately and sign in through the normal Codex login flow.

## Check the environment

```bash
pdftranslate-pdf --check
```

The check verifies that:

- a `codex` executable can be found;
- `codex login status` reports an authenticated session;
- `pdf2zh-next` is installed.

It does **not** read or print `~/.codex/auth.json`.

## Phase 1 smoke test

Start with one or two pages while the CLI integration is being validated:

```bash
pdftranslate-pdf paper.pdf --pages 1-2 --mode dual --output-dir translated
```

To request both Chinese-only and bilingual outputs:

```bash
pdftranslate-pdf paper.pdf --pages 1-2 --mode both --output-dir translated
```

For machine-readable integration with a future Zotero/Obsidian adapter:

```bash
pdftranslate-pdf paper.pdf --pages 1 --mode dual --json
```

The final JSON contains `input_pdf`, `mono_pdf`, and `dual_pdf` paths.

## Codex model override

By default the local Codex CLI chooses its normal default model. An explicit override can be supplied when needed:

```bash
pdftranslate-pdf paper.pdf --pages 1 --model MODEL_NAME
```

or through:

```text
PDFTRANSLATE_CODEX_MODEL
```

No model name is hard-coded into the repository.

## Security boundary

- Codex authentication remains owned by the local Codex CLI.
- PDFtranslate never reads, copies, commits, or uploads `~/.codex/auth.json`.
- `codex exec` is launched ephemerally in a temporary directory with a read-only sandbox.
- User Codex config and exec-policy rules are ignored for the translation subprocess so repository/user rules cannot unexpectedly alter the translation job.
- Private PDFs, generated PDFs, `.env` files, keys, and Codex auth files are gitignored.
- No API key is required for the local ChatGPT-managed Codex login path.

## Phase 1 performance limitation

PDFMathTranslate Next's generic CLI translator invokes the configured command for individual translation units. Therefore the initial Phase 1 path may launch many short-lived `codex exec` processes for a full paper. This is intentionally a correctness/smoke-test implementation, not the final high-throughput design.

The next core milestone is a persistent localhost Codex bridge that batches multiple PDF2zh translation units into fewer Codex calls. Zotero and Obsidian will then call the same persistent core.

## Repository layout

```text
src/pdftranslate/
  codex_cli.py       # stdin/stdout Codex adapter
  pdf_runner.py      # PDF2zh Next orchestration

docs/
  architecture.md
  phase1.md

tests/
```

## Upstream projects

This project is designed to interoperate with, but not vendor, PDFMathTranslate Next, BabelDOC, Zotero, Obsidian, and OpenAI Codex CLI. Their licenses and terms remain independent.
