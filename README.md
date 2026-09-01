# PDFtranslate

Universal local PDF translation core for academic reading workflows.

`PDFtranslate` keeps PDF parsing/typesetting, Codex execution, and desktop integrations separate so the same core can be used from Zotero, Obsidian, the command line, or another local desktop tool.

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

The MVP architecture is implemented:

- `pdftranslate-pdf` — end-to-end PDF translation command.
- `pdftranslate-bridge` — loopback OpenAI-compatible service backed by the authenticated local Codex CLI.
- `pdftranslate-codex` — direct stdin/stdout fallback adapter.
- **Zotero adapter** — right-click a local PDF or literature item, run PDFtranslate, and import the translated PDF back as a child attachment.
- **Obsidian adapter** — command-palette, ribbon, and PDF context-menu entry points that save translated PDFs inside the current vault.

The PDF command defaults to bridge mode: PDFMathTranslate Next can issue several concurrent segment requests while PDFtranslate batches them into fewer `codex exec` calls.

PDFtranslate interoperates with PDFMathTranslate Next/BabelDOC instead of vendoring or rewriting their PDF layout engine.

## Security boundary

- Codex authentication remains owned by the installed Codex CLI.
- PDFtranslate never reads, copies, commits, or uploads `~/.codex/auth.json`.
- No OpenAI API key is required for the local ChatGPT-managed Codex login path.
- `codex exec` translation runs are ephemeral, use temporary working directories, and request a read-only sandbox.
- User Codex config/rules are ignored inside the translation subprocess so unrelated repository instructions cannot alter the translation backend.
- The persistent bridge accepts IPv4 loopback connections only and uses a random in-memory local bearer token unless the user explicitly supplies a local-only token.
- Private PDFs, generated PDFs, `.env` files, keys, Codex auth files, and generated plugin bundles are gitignored.
- Zotero and Obsidian adapters store only local workflow settings; they do not contain model credentials.

## Install the local core

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

Install Codex CLI separately and sign in through its normal login flow.

Check the machine:

```bash
pdftranslate-pdf --check
```

The check verifies that:

- a `codex` executable can be found;
- `codex login status` reports an authenticated local session;
- `pdf2zh-next` is installed.

It does **not** read or print `~/.codex/auth.json`.

## First local smoke test

Use a short public/sample PDF page range before a full paper:

```bash
pdftranslate-pdf paper.pdf --pages 1-2 --mode dual --output-dir translated
```

Default bridge flow:

```text
PDF2zh workers (default 8)
        -> 127.0.0.1 local bridge
        -> batching window (default 100 ms)
        -> up to 4 segments / Codex batch
        -> one Codex worker by default
```

Useful controls:

```bash
pdftranslate-pdf paper.pdf \
  --batch-size 4 \
  --batch-window-ms 100 \
  --bridge-workers 1 \
  --pdf-workers 8
```

If bridge mode encounters a platform-specific issue, the direct fallback remains available:

```bash
pdftranslate-pdf paper.pdf --pages 1 --transport direct
```

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

Machine-readable result for desktop adapters:

```bash
pdftranslate-pdf paper.pdf --mode dual --json
```

The JSON contains `input_pdf`, `mono_pdf`, and `dual_pdf` paths.

## Zotero adapter

Source: `adapters/zotero/`

The adapter invokes only the local `pdftranslate-pdf --json` command. It does not manage Codex credentials.

Build locally:

```bash
python scripts/build_zotero_xpi.py
```

Output:

```text
dist/PDFtranslate-zotero.xpi
```

GitHub Actions also builds the XPI as the `PDFtranslate-zotero` artifact.

The executable can be supplied to the Zotero process through:

```text
PDFTRANSLATE_PDF_EXECUTABLE=/absolute/path/to/pdftranslate-pdf
```

Optional output mode override:

```text
PDFTRANSLATE_OUTPUT_MODE=dual
PDFTRANSLATE_OUTPUT_MODE=mono
PDFTRANSLATE_OUTPUT_MODE=both
```

See `adapters/zotero/README.md` for the current adapter scope.

## Obsidian adapter

Source: `adapters/obsidian/`

The plugin is desktop-only and calls `pdftranslate-pdf` with Node `execFile`, not a shell command string. Outputs are constrained to a configured folder inside the active vault.

Build locally:

```bash
cd adapters/obsidian
npm install
npm run build
```

Manual plugin files:

```text
main.js
manifest.json
```

GitHub Actions builds these files as the `PDFtranslate-obsidian` artifact.

See `adapters/obsidian/README.md` for settings and current scope.

## Codex model override

By default the authenticated Codex CLI uses its normal default model. An explicit override is optional:

```bash
pdftranslate-pdf paper.pdf --model MODEL_NAME
```

or:

```text
PDFTRANSLATE_CODEX_MODEL
```

No model name is hard-coded into the repository.

## Standalone local bridge

For a long-lived local service or future adapters:

```bash
pdftranslate-bridge --port 8765
```

It prints a local JSON record containing its `base_url` and a randomly generated local bearer token. That bridge token is only for local process isolation; it is **not** an OpenAI API key, ChatGPT password, or Codex authentication token.

Endpoints:

```text
GET  /health
GET  /v1/models
POST /v1/chat/completions
```

## Validation status

Automated CI currently covers:

- Python 3.11 / 3.12 / 3.13 core tests;
- Codex bridge batching/ID matching with a fake backend;
- loopback/authentication HTTP behavior;
- Zotero manifest, packaging structure, and no-credential invariants;
- Obsidian manifest, path confinement, no-shell/no-credential invariants;
- Obsidian TypeScript type-check and production esbuild on Node 22.

CI intentionally does **not** receive a personal Codex login or subscription credential. Therefore the remaining validation boundary is a real local smoke test on a machine where Codex CLI is already signed in, followed by one Zotero and one Obsidian end-to-end test.

## Repository layout

```text
src/pdftranslate/
  codex_cli.py       # direct stdin/stdout fallback
  bridge.py          # persistent localhost + request batching
  pdf_runner.py      # PDF2zh Next orchestration

adapters/
  zotero/
  obsidian/

docs/
  architecture.md
  phase1.md
  bridge.md

tests/
```

## Upstream projects

This project is designed to interoperate with, but not vendor, PDFMathTranslate Next, BabelDOC, Zotero, Obsidian, and OpenAI Codex CLI. Their licenses and terms remain independent.
