# Persistent Codex bridge

## Why it exists

PDFMathTranslate Next can translate many layout segments concurrently. Its generic CLI backend starts a command for each segment, which is simple but expensive when the command is `codex exec`.

The persistent bridge changes only the transport layer:

```text
PDF2zh Next
  -> OpenAI-compatible requests
  -> 127.0.0.1 ephemeral server
  -> in-memory queue
  -> short batching window
  -> one or more Codex batch workers
  -> structured translations returned to original requests
```

PDF parsing, formulas, figures, tables, caching and final typesetting remain owned by PDFMathTranslate Next/BabelDOC.

## Protocol

The service implements the subset needed by the PDF2zh OpenAI client:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

A normal chat-completions request is queued as one independent translation job. Jobs arriving within the configured batching window are combined into a single `codex exec` prompt. Each job is assigned an opaque random ID, and the Codex response is constrained to a JSON schema. The bridge validates that every expected ID appears exactly once before returning results to callers.

## Authentication model

The bridge has two unrelated authentication layers:

1. **Codex authentication** — completely owned by the locally installed Codex CLI. PDFtranslate does not read the credential file.
2. **Local bridge token** — a random bearer token generated in memory so unrelated local clients do not accidentally call the bridge. It is not an OpenAI credential.

The auto-started bridge used by `pdftranslate-pdf` listens on `127.0.0.1` with an ephemeral OS-assigned port and an in-memory random token.

## Defaults

```text
PDF workers:       8
batch size:        8
batch window:      100 ms
Codex workers:     1
Codex timeout:     240 s
```

These are conservative initial values. The PDF workers create enough simultaneous requests for useful batching, while a single Codex worker avoids uncontrolled consumption of subscription capacity.

## Failure model

- malformed HTTP requests -> `400`
- missing/wrong local bearer token -> `401`
- Codex/backend batch failure -> `502`
- unexpected local server failure -> `500`

A batch result is rejected if it omits an expected ID, returns an unexpected ID, duplicates an ID, or returns an empty translation.

## Security rules

- loopback bind only;
- no direct access to `~/.codex/auth.json`;
- temporary working directory for each `codex exec`;
- ephemeral Codex session;
- read-only sandbox;
- user config/rules ignored inside the translation subprocess;
- document text explicitly treated as untrusted source material in the batching prompt.
