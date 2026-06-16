from pathlib import Path

import pytest

from resident_expenses.extract import pdf_text
from resident_expenses.extract.pdf_text import OcrError, extract_pages, extract_text


def test_has_text_true_when_any_page_nonblank() -> None:
    assert pdf_text._has_text(["", "  ", "hello"]) is True


def test_has_text_false_when_all_blank() -> None:
    assert pdf_text._has_text(["", "  ", "\n"]) is False


def test_extract_pages_native_when_text_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_text, "_raw_pages", lambda path: ["page one", "page two"])

    def _boom(src: Path, dst: Path, language: str = "spa") -> None:
        raise AssertionError("OCR must not run when native text exists")

    monkeypatch.setattr(pdf_text, "run_ocr", _boom)
    assert extract_pages(Path("x.pdf")) == ["page one", "page two"]


def test_extract_pages_ocrs_when_native_blank(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[Path] = []

    def fake_raw(path: Path) -> list[str]:
        calls.append(path)
        return ["", ""] if len(calls) == 1 else ["OCR p1", "OCR p2"]

    monkeypatch.setattr(pdf_text, "_raw_pages", fake_raw)
    monkeypatch.setattr(
        pdf_text, "run_ocr", lambda src, dst, language="spa": dst.write_bytes(b"%PDF")
    )
    assert extract_pages(tmp_path / "scan.pdf") == ["OCR p1", "OCR p2"]
    assert len(calls) == 2


def test_extract_pages_native_only_when_ocr_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_text, "_raw_pages", lambda path: ["", ""])
    assert extract_pages(Path("scan.pdf"), ocr=False) == ["", ""]


def test_extract_text_joins_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_text, "_raw_pages", lambda path: ["a", "b"])
    assert extract_text(Path("x.pdf")) == "a\nb"


def test_extract_pages_propagates_ocr_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_text, "_raw_pages", lambda path: [""])

    def _missing(src: Path, dst: Path, language: str = "spa") -> None:
        raise OcrError("missing")

    monkeypatch.setattr(pdf_text, "run_ocr", _missing)
    with pytest.raises(OcrError):
        extract_pages(Path("scan.pdf"))
