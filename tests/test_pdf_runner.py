from __future__ import annotations

from pathlib import Path
import shlex
import sys
import tempfile
import unittest

from pdftranslate.pdf_runner import PDFTranslationResult
from pdftranslate.pdf_runner import _resolve_output_path
from pdftranslate.pdf_runner import build_wrapper_command


class WrapperCommandTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
