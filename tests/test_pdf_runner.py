from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

from pdftranslate.bridge import DEFAULT_BATCH_SIZE
from pdftranslate.pdf_runner import PDFTranslationResult
from pdftranslate.pdf_runner import _resolve_output_path
from pdftranslate.pdf_runner import build_wrapper_command
from pdftranslate.pdf_runner import main
from pdftranslate.pdf_runner import parse_args


class WrapperCommandTests(unittest.TestCase):
    def test_pdf_runner_uses_the_safe_bridge_batch_default(self) -> None:
        self.assertEqual(parse_args([]).batch_size, DEFAULT_BATCH_SIZE)

    def test_wrapper_runs_same_python_module(self) -> None:
        command = build_wrapper_command(
            codex_path=None,
            model=None,
            timeout=240,
        )
        parts = shlex.split(command)
        self.assertEqual(parts[0], sys.executable)
        self.assertEqual(parts[1:3], ["-m", "pdftranslate.codex_cli"])
        self.assertIn("--timeout", parts)
        self.assertIn("240", parts)

    def test_wrapper_can_forward_codex_path_and_model(self) -> None:
        command = build_wrapper_command(
            codex_path="/opt/codex bin/codex",
            model="example-model",
            timeout=120,
        )
        parts = shlex.split(command)
        self.assertIn("--codex-path", parts)
        self.assertIn("/opt/codex bin/codex", parts)
        self.assertIn("--model", parts)
        self.assertIn("example-model", parts)


class OutputPathTests(unittest.TestCase):
    def test_relative_output_is_resolved_under_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir).resolve()
            resolved = _resolve_output_path("paper-dual.pdf", output_dir)
            self.assertEqual(resolved, str((output_dir / "paper-dual.pdf").resolve()))

    def test_absolute_output_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            absolute = (Path(temp_dir) / "paper-mono.pdf").resolve()
            resolved = _resolve_output_path(absolute, Path("elsewhere"))
            self.assertEqual(resolved, str(absolute))


class ResultContractTests(unittest.TestCase):
    def test_result_contract_supports_dual_only(self) -> None:
        result = PDFTranslationResult(
            input_pdf="paper.pdf",
            mono_pdf=None,
            dual_pdf="paper-dual.pdf",
        )
        self.assertEqual(result.dual_pdf, "paper-dual.pdf")
        self.assertIsNone(result.mono_pdf)

    def test_json_mode_keeps_dependency_noise_off_stdout(self) -> None:
        async def fake_translate(*_args, **_kwargs):
            print("dependency progress")
            return PDFTranslationResult(
                input_pdf="paper.pdf",
                mono_pdf=None,
                dual_pdf="paper-dual.pdf",
            )

        stdout = StringIO()
        stderr = StringIO()
        with patch("pdftranslate.pdf_runner.translate_pdf", new=fake_translate):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["paper.pdf", "--json"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["dual_pdf"], "paper-dual.pdf")
        self.assertNotIn("dependency progress", stdout.getvalue())
        self.assertIn("dependency progress", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
