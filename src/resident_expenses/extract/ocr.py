"""Shared OCR helper: add a text layer to a (scanned) PDF via OCRmyPDF.

Requires the external ``ocrmypdf`` binary (``brew install ocrmypdf tesseract-lang``).
"""

from __future__ import annotations

import subprocess as subprocess
from pathlib import Path


class OcrError(Exception):
    """Raised when OCR is needed but ocrmypdf is missing or fails."""


def run_ocr(src: Path, dst: Path, *, language: str = "spa") -> None:
    """OCR ``src`` into a searchable PDF at ``dst`` (overwriting any text layer)."""
    try:
        subprocess.run(
            ["ocrmypdf", "--force-ocr", "-l", language, str(src), str(dst)],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise OcrError(
            "ocrmypdf not found — install it with `brew install ocrmypdf tesseract-lang`"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise OcrError(f"ocrmypdf failed (exit {exc.returncode})") from exc
