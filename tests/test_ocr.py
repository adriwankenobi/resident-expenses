import subprocess
from pathlib import Path

import pytest

from resident_expenses.extract import ocr
from resident_expenses.extract.ocr import OcrError, run_ocr


def test_run_ocr_invokes_ocrmypdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, check, capture_output):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return None

    monkeypatch.setattr(ocr.subprocess, "run", fake_run)
    run_ocr(tmp_path / "in.pdf", tmp_path / "out.pdf", language="spa")
    assert captured["cmd"][0] == "ocrmypdf"
    assert "-l" in captured["cmd"]
    assert "spa" in captured["cmd"]


def test_run_ocr_missing_binary_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(cmd, check, capture_output):  # type: ignore[no-untyped-def]
        raise FileNotFoundError

    monkeypatch.setattr(ocr.subprocess, "run", boom)
    with pytest.raises(OcrError):
        run_ocr(tmp_path / "in.pdf", tmp_path / "out.pdf")


def test_run_ocr_failure_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(cmd, check, capture_output):  # type: ignore[no-untyped-def]
        raise subprocess.CalledProcessError(returncode=4, cmd=cmd)

    monkeypatch.setattr(ocr.subprocess, "run", boom)
    with pytest.raises(OcrError):
        run_ocr(tmp_path / "in.pdf", tmp_path / "out.pdf")
