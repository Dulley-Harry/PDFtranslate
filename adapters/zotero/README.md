# Zotero adapter

This adapter is intentionally thin. It does not contain a translation model or any API credentials.

From the Zotero library, select a regular item or a local PDF attachment and choose:

**Translate PDF with PDFtranslate**

The adapter:

1. resolves the selected local PDF;
2. runs `pdftranslate-pdf <file> --mode dual --output-dir <temp> --json`;
3. waits for the local PDFtranslate core to finish;
4. imports the translated PDF back into Zotero as a child attachment;
5. removes its temporary job directory.

## Prerequisite

Install the repository locally with the PDF backend and make `pdftranslate-pdf` discoverable on the Zotero process PATH.

If it is not on PATH, set the environment variable before launching Zotero:

```text
PDFTRANSLATE_PDF_EXECUTABLE=/absolute/path/to/pdftranslate-pdf
```

Optional output mode override:

```text
PDFTRANSLATE_OUTPUT_MODE=dual
PDFTRANSLATE_OUTPUT_MODE=mono
PDFTRANSLATE_OUTPUT_MODE=both
```

No Codex token, ChatGPT password, OpenAI API key, or `auth.json` content is stored by the Zotero adapter.

## Build XPI

From the repository root:

```bash
python scripts/build_zotero_xpi.py
```

The generated development XPI is written under `dist/`, which is gitignored.

## Current scope

- Zotero 8 and 9 desktop.
- Local PDF attachments only.
- Sequential processing when multiple items are selected.
- Core progress is not yet streamed into the Zotero progress window; the adapter currently shows item-level progress.
- A graphical settings pane is planned after the end-to-end local smoke test.
