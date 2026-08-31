# Architecture

## Principle

PDFtranslate is a local translation core. Applications are adapters, not owners of translation logic.

```text
+-------------------+       +--------------------+
| Zotero adapter    |       | Obsidian adapter   |
+---------+---------+       +----------+---------+
          |                            |
          +-------------+--------------+
                        |
                        v
                +---------------+
                | PDFtranslate  |
                | local core    |
                +-------+-------+
                        |
          +-------------+-------------+
          |                           |
          v                           v
+--------------------+       +-------------------+
| PDFMathTranslate   |       | Codex CLI adapter |
| Next / BabelDOC    |       | `codex exec`      |
+--------------------+       +-------------------+
```

## Core responsibilities

The core owns:

- translation job configuration;
- Codex executable discovery;
- safe Codex subprocess invocation;
- stdin/stdout translation contract;
- retry and timeout policy;
- future cache management;
- future localhost job API.

The core does not own:

- Zotero item selection or attachment import;
- Obsidian vault UI or commands;
- PDF layout algorithms;
- Codex authentication files.

## Codex contract

The initial executable is `pdftranslate-codex`.

Input:

```text
UTF-8 source text on stdin
```

Output:

```text
UTF-8 translated text only on stdout
```

Errors go to stderr and return a non-zero exit code.

Authentication is delegated to the installed Codex CLI. PDFtranslate must never read, copy, upload or rewrite `~/.codex/auth.json`.

## PDF layer

PDF layout should remain upstream-owned. The preferred initial integration is PDFMathTranslate Next's generic CLI translator, configured to invoke `pdftranslate-codex`.

This keeps formulas, tables, document layout, caching and PDF generation in the PDFMathTranslate Next / BabelDOC pipeline while PDFtranslate supplies only the model translation step.

## Application adapters

### Zotero

Expected adapter responsibilities:

1. Resolve the selected item's local PDF path.
2. Submit the PDF to the local PDFtranslate job runner.
3. Show progress/cancellation.
4. Attach the generated PDF back to the source Zotero item.

### Obsidian

Expected adapter responsibilities:

1. Resolve the current PDF or selected vault PDF path.
2. Submit the PDF to the same local PDFtranslate job runner.
3. Show progress/cancellation.
4. Write the generated PDF beside the source or into a configured output directory.

Neither adapter should invoke Codex directly.

## Planned milestones

### Phase 0 — Codex adapter

- `pdftranslate-codex`
- environment/login check
- stdin/stdout contract
- read-only Codex sandbox

### Phase 1 — PDF runner

- PDFMathTranslate Next integration
- mono/bilingual output modes
- progress events
- cache/retry policy
- end-to-end CLI command

### Phase 2 — Local service

- loopback-only HTTP service
- job creation/status/cancel endpoints
- shared result cache

### Phase 3 — Zotero adapter

- right-click Translate PDF
- progress UI
- automatic attachment import

### Phase 4 — Obsidian adapter

- command palette / PDF context action
- progress UI
- output to vault
