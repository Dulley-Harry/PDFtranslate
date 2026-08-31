# PDFtranslate

Universal local PDF translation core for academic reading workflows.

`PDFtranslate` keeps PDF parsing/typesetting, model execution, and desktop integrations separate so the same core can be used from Zotero, Obsidian, the command line, or another local tool.

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
localhost OpenAI-compatible bridge
          |
          v
batched `codex exec`
          |
          v
 translated / bilingual PDF
```

## Current status

Version 0.2 introduces the persistent local Codex bridge:

- `pdftranslate-pdf` — end-to-end PDF translation command.
- `pdftranslate-bridge` — loopback OpenAI-compatible service backed by Codex CLI.
- `pdftranslate-codex` — direct stdin/stdout fallback adapter.
- The PDF command defaults to **bridge mode**, allowing PDF2zh to issue several concurrent segment requests while PDFtranslate batches them into fewer Codex calls.
- Zotero and Obsidian UI adapters are the next layer; they will call this same local core.

PDFtranslate interoperates with PDFMathTranslate Next rather than vendoring or modifying its source.

## Install for local development

Python 3.11-3.13 is supported.

```bash
git clone https://github.com/Dulley-Harry/PDFtranslate.git
cd PDFtranslate
python -m venv .venv
```

Activate the virtual environment, then install the PDF backend:

```bash
python -m pip install -U pip
python -m pip install -e ".[pdf]"
```

Install Codex CLI separately and sign in through the normal Codex login flow.

## Check the environment

```bash
pdftranslate-pdf --check
```

This checks:

- a `codex` executable can be found;
- `codex login status` reports an authenticated local session;
- `pdf2zh-next` is installed.

It does **not** read or print `~/.codex/auth.json`.

## Translate a PDF

Start with a short page range for the first machine-specific smoke test:

```bash
pdftranslate-pdf paper.pdf --pages 1-2 --mode dual --output-dir translated
```

Bridge mode is now the default. Typical flow:

```text
PDF2zh workers (default 8)
        -> localhost bridge
        -> short batching window (default 100 ms)
        -> up to 8 segments / Codex batch
        -> one Codex worker by default
```

Useful controls:

```bash
pdftranslate-pdf paper.pdf \
  --batch-size 8 \
  --batch-window-ms 100 \
  --bridge-workers 1 \
  --pdf-workers 8
```

If bridge mode encounters a platform-specific issue, the Phase 1 direct path remains available:

```bash
pdftranslate-pdf paper.pdf --pages 1 --transport direct
```

Direct mode is slower for full papers because it can start a separate Codex process for individual PDF2zh translation units.

## Output modes

Bilingual PDF only (default):

```bash
pdftranslate-pdf paper.pdf --mode dual
```

Chinese-only PDF:

```bash
pdftranslate-pdf paper.pdf --mode mono
```

Both:

```bash
pdftranslate-pdf paper.pdf --mode both
```

For a future Zotero/Obsidian adapter, use machine-readable output:

```bash
pdftranslate-pdf paper.pdf --mode dual --json
```

The final JSON contains `input_pdf`, `mono_pdf`, and `dual_pdf` paths.

## Codex model override

By default the authenticated Codex CLI uses its normal default model. An explicit override is optional:

```bash
pdftranslate-pdf paper.pdf --model MODEL_NAME
```

or set:

```text
PDFTRANSLATE_CODEX_MODEL
```

No model name is hard-coded into the repository.

## Standalone local bridge

The bridge can also be kept running for future desktop adapters:

```bash
pdftranslate-bridge --port 8765
```

It prints one local JSON record containing its `base_url` and a randomly generated local bearer token. The service only accepts IPv4 loopback binds (`127.x.x.x` / `localhost`).

To choose a stable local-only token yourself:

```text
PDFTRANSLATE_LOCAL_API_KEY
```

This bridge token is only for local process isolation. It is **not** an OpenAI API key, ChatGPT password, or Codex authentication token.

Endpoints:

```text
GET  /health
GET  /v1/models
POST /v1/chat/completions
```

## Security boundary

- Codex authentication remains owned by the installed Codex CLI.
- PDFtranslate never reads, copies, commits, or uploads `~/.codex/auth.json`.
- No OpenAI API key is required for the local ChatGPT-managed Codex login path.
- Every `codex exec` translation run is ephemeral, uses a temporary working directory, and requests a read-only sandbox.
- User Codex config/rules are ignored for the translation subprocess so unrelated repository instructions cannot alter the translation backend.
- The bridge binds to loopback only and uses a per-process random bearer token unless the user explicitly supplies a local token.
- Private PDFs, generated PDFs, `.env` files, keys, and Codex auth files are gitignored.

## Repository layout

```text
src/pdftranslate/
  codex_cli.py       # direct stdin/stdout fallback
  bridge.py          # persistent localhost + request batching
  pdf_runner.py      # PDF2zh Next orchestration

docs/
  architecture.md
  phase1.md
  bridge.md

tests/
```

## Upstream projects

This project is designed to interoperate with, but not vendor, PDFMathTranslate Next, BabelDOC, Zotero, Obsidian, and OpenAI Codex CLI. Their licenses and terms remain independent.
