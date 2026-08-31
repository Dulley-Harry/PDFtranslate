# Obsidian adapter

Desktop-only Obsidian plugin that sends the active PDF to the local `pdftranslate-pdf` command.

It does not contain, request, or store an OpenAI API key, ChatGPT password, Codex token, or `auth.json` content. Authentication stays inside the local Codex CLI used by the PDFtranslate core.

## User flow

- Open a PDF in Obsidian and run **PDFtranslate: Translate active PDF with PDFtranslate** from the command palette; or
- click the Languages ribbon icon; or
- right-click a PDF file and choose **Translate PDF with PDFtranslate**.

The adapter runs:

```text
pdftranslate-pdf <absolute-pdf-path> --mode <mode> --output-dir <vault-output-dir> --json
```

It uses Node `execFile`, not a shell command string, so PDF filenames are passed as arguments rather than interpreted as shell syntax.

## Settings

Only local workflow settings are stored:

- `PDFtranslate executable` — defaults to `pdftranslate-pdf`; the initial default can also come from `PDFTRANSLATE_PDF_EXECUTABLE`.
- `Output folder` — defaults to `PDFtranslate` inside the current vault. Absolute paths and `..` traversal outside the vault are rejected.
- `Output mode` — bilingual, Chinese-only, or both.
- `Open translated PDF` — optional.

## Build

```bash
cd adapters/obsidian
npm install
npm run build
```

For manual installation copy these generated/runtime files into:

```text
<Vault>/.obsidian/plugins/pdftranslate/
```

Required files:

```text
main.js
manifest.json
```

The repository CI builds the adapter on Node 22 without using any Codex login or subscription quota.

## Scope

- Desktop Obsidian only (`isDesktopOnly: true`).
- File-system vaults only.
- One active translation job per Obsidian plugin instance.
- Translated outputs remain inside the configured vault folder so Obsidian's file watcher can index them.
