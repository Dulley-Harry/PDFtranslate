"""Run PDFMathTranslate Next with the local Codex CLI adapter."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import sys
from typing import Any

from .codex_cli import CodexAdapterError, codex_status, find_codex


class PDFRunnerError(RuntimeError):
    """Raised when the PDF translation pipeline cannot be started or completed."""


@dataclass(frozen=True)
class PDFTranslationResult:
    input_pdf: str
    mono_pdf: str | None
    dual_pdf: str | None


def _pdf2zh_version() -> str:
    try:
        return importlib.metadata.version("pdf2zh-next")
    except importlib.metadata.PackageNotFoundError as exc:
        raise PDFRunnerError(
            "pdf2zh-next is not installed. Install PDFtranslate with the PDF extra: "
            "pip install -e '.[pdf]'"
        ) from exc


def _load_pdf2zh() -> tuple[Any, Any, Any, Any, Any]:
    _pdf2zh_version()
    try:
        from pdf2zh_next.config.model import PDFSettings
        from pdf2zh_next.config.model import SettingsModel
        from pdf2zh_next.config.model import TranslationSettings
        from pdf2zh_next.config.translate_engine_model import CLISettings
        from pdf2zh_next.high_level import do_translate_async_stream
    except Exception as exc:  # pragma: no cover - depends on optional heavy dependency
        raise PDFRunnerError(f"Failed to import PDFMathTranslate Next: {exc}") from exc
    return PDFSettings, SettingsModel, TranslationSettings, CLISettings, do_translate_async_stream


def build_wrapper_command(
    *,
    codex_path: str | None,
    model: str | None,
    timeout: int,
) -> str:
    """Build the command PDF2zh's CLITranslator will execute for each segment."""
    args = [
        sys.executable,
        "-m",
        "pdftranslate.codex_cli",
        "--source-language",
        "English",
        "--target-language",
        "Simplified Chinese",
        "--timeout",
        str(timeout),
    ]
    if codex_path:
        args.extend(["--codex-path", codex_path])
    if model:
        args.extend(["--model", model])
    return shlex.join(args)


def build_settings(
    *,
    output_dir: Path,
    mode: str,
    pages: str | None,
    codex_path: str | None,
    model: str | None,
    codex_timeout: int,
    ignore_cache: bool,
    enhance_compatibility: bool,
    translate_table_text: bool,
    debug: bool,
) -> Any:
    """Create a PDF2zh Next SettingsModel without editing user config files."""
    PDFSettings, SettingsModel, TranslationSettings, CLISettings, _ = _load_pdf2zh()

    wrapper_command = build_wrapper_command(
        codex_path=codex_path,
        model=model,
        timeout=codex_timeout,
    )

    # PDF2zh invokes the configured CLI once per translation unit.  Phase 1 is
    # deliberately single-worker to avoid multiplying Codex sessions and usage.
    translation = TranslationSettings(
        lang_in="en",
        lang_out="zh",
        output=str(output_dir),
        qps=1,
        pool_max_workers=1,
        min_text_length=5,
        ignore_cache=ignore_cache,
        no_auto_extract_glossary=True,
    )
    pdf = PDFSettings(
        pages=pages,
        no_dual=mode == "mono",
        no_mono=mode == "dual",
        enhance_compatibility=enhance_compatibility,
        translate_table_text=translate_table_text,
        watermark_output_mode="no_watermark",
    )
    engine = CLISettings(
        clitranslator_command=wrapper_command,
        # PDF2zh currently caps this field at 300 seconds. Leave headroom for
        # Python process startup around the Codex timeout.
        clitranslator_timeout=min(300, max(codex_timeout + 30, 60)),
    )
    return SettingsModel(
        translation=translation,
        pdf=pdf,
        translate_engine_settings=engine,
        report_interval=0.5,
        basic={"debug": debug},
    )


def _format_progress(event: dict[str, Any]) -> str | None:
    if event.get("type") != "progress":
        return None
    stage = event.get("stage") or event.get("phase") or event.get("name") or "working"
    value = event.get("overall_progress", event.get("progress"))
    if isinstance(value, dict):
        current = value.get("current")
        total = value.get("total")
        if isinstance(current, (int, float)) and isinstance(total, (int, float)) and total:
            value = current / total
    if isinstance(value, (int, float)):
        percent = value * 100 if 0 <= value <= 1 else value
        return f"{stage}: {percent:.0f}%"
    return str(stage)


async def translate_pdf(
    input_pdf: Path,
    *,
    output_dir: Path,
    mode: str = "dual",
    pages: str | None = None,
    codex_path: str | None = None,
    model: str | None = None,
    codex_timeout: int = 240,
    ignore_cache: bool = False,
    enhance_compatibility: bool = False,
    translate_table_text: bool = True,
    debug: bool = False,
) -> PDFTranslationResult:
    """Translate one PDF and return produced output paths."""
    if not input_pdf.is_file() or input_pdf.suffix.lower() != ".pdf":
        raise PDFRunnerError(f"Input PDF does not exist or is not a PDF: {input_pdf}")
    if mode not in {"dual", "mono", "both"}:
        raise PDFRunnerError("mode must be one of: dual, mono, both")
    if not 1 <= codex_timeout <= 270:
        raise PDFRunnerError("codex timeout must be between 1 and 270 seconds")

    output_dir.mkdir(parents=True, exist_ok=True)
    settings = build_settings(
        output_dir=output_dir,
        mode=mode,
        pages=pages,
        codex_path=codex_path,
        model=model,
        codex_timeout=codex_timeout,
        ignore_cache=ignore_cache,
        enhance_compatibility=enhance_compatibility,
        translate_table_text=translate_table_text,
        debug=debug,
    )
    _, _, _, _, do_translate_async_stream = _load_pdf2zh()

    finish_event: dict[str, Any] | None = None
    async for event in do_translate_async_stream(settings, input_pdf):
        if not isinstance(event, dict):
            continue
        progress = _format_progress(event)
        if progress:
            print(f"[PDFtranslate] {progress}", file=sys.stderr, flush=True)
        if event.get("type") == "error":
            raise PDFRunnerError(str(event.get("error") or "PDF2zh translation failed"))
        if event.get("type") == "finish":
            finish_event = event
            break

    if finish_event is None:
        raise PDFRunnerError("PDF2zh finished without a result event")
    result = finish_event.get("translate_result")
    if result is None:
        raise PDFRunnerError("PDF2zh result event did not contain translate_result")

    mono = getattr(result, "mono_pdf_path", None)
    dual = getattr(result, "dual_pdf_path", None)
    return PDFTranslationResult(
        input_pdf=str(input_pdf.resolve()),
        mono_pdf=str(Path(mono).resolve()) if mono else None,
        dual_pdf=str(Path(dual).resolve()) if dual else None,
    )


def check_environment(*, codex_path: str | None = None) -> dict[str, Any]:
    """Check local prerequisites without reading credential files directly."""
    resolved_codex = find_codex(codex_path)
    authenticated, codex_detail = codex_status(resolved_codex)
    result = {
        "codex_path": resolved_codex,
        "codex_authenticated": authenticated,
        "codex_status": codex_detail,
    }
    try:
        result["pdf2zh_next_version"] = _pdf2zh_version()
        result["pdf2zh_next_available"] = True
    except PDFRunnerError as exc:
        result["pdf2zh_next_available"] = False
        result["pdf2zh_next_error"] = str(exc)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate a PDF with PDFMathTranslate Next and local Codex CLI."
    )
    parser.add_argument("input_pdf", nargs="?", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("translated"))
    parser.add_argument("--mode", choices=("dual", "mono", "both"), default="dual")
    parser.add_argument("--pages", help="PDF2zh page expression, e.g. 1,2,4-6")
    parser.add_argument("--codex-path")
    parser.add_argument("--model", default=os.environ.get("PDFTRANSLATE_CODEX_MODEL") or None)
    parser.add_argument("--codex-timeout", type=int, default=240)
    parser.add_argument("--ignore-cache", action="store_true")
    parser.add_argument("--enhance-compatibility", action="store_true")
    parser.add_argument("--no-table-text", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--check", action="store_true", help="Check local prerequisites and exit")
    parser.add_argument("--json", action="store_true", help="Emit final result as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.check:
            status = check_environment(codex_path=args.codex_path)
            print(json.dumps(status, ensure_ascii=False, indent=2 if not args.json else None))
            return 0 if status.get("codex_authenticated") and status.get("pdf2zh_next_available") else 2

        if args.input_pdf is None:
            raise PDFRunnerError("input_pdf is required unless --check is used")
        result = asyncio.run(
            translate_pdf(
                args.input_pdf,
                output_dir=args.output_dir,
                mode=args.mode,
                pages=args.pages,
                codex_path=args.codex_path,
                model=args.model,
                codex_timeout=args.codex_timeout,
                ignore_cache=args.ignore_cache,
                enhance_compatibility=args.enhance_compatibility,
                translate_table_text=not args.no_table_text,
                debug=args.debug,
            )
        )
        payload = asdict(result)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            if result.dual_pdf:
                print(f"Bilingual PDF: {result.dual_pdf}")
            if result.mono_pdf:
                print(f"Chinese PDF: {result.mono_pdf}")
        return 0
    except (PDFRunnerError, CodexAdapterError) as exc:
        print(f"pdftranslate-pdf: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
