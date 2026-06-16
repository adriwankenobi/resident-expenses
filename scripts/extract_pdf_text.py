"""Dump all-pages text of a PDF to stdout (OCR fallback for scans).

Sanitize the output before pasting it anywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

from resident_expenses.extract import OcrError, extract_pages


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: extract_pdf_text.py <path-to-pdf>", file=sys.stderr)
        raise SystemExit(2)
    path = Path(sys.argv[1])
    print(
        "Extracting text (will OCR with ocrmypdf if the PDF has no text layer; "
        "this can take a minute)...",
        file=sys.stderr,
    )
    try:
        pages = extract_pages(path)
    except OcrError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    for i, text in enumerate(pages, start=1):
        print(f"----- page {i} -----")
        print(text)


if __name__ == "__main__":
    main()
