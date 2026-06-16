set dotenv-load := true

default:
    @just --choose

# Install dependencies via uv.
install:
    uv sync

# Run lint + types + tests.
check:
    uv run ruff check src tests
    uv run ruff format --check src tests
    uv run mypy
    uv run pytest

# Run tests only.
test:
    uv run pytest

# Build report.html from the data/ JSON files.
report:
    uv run resident-expenses report

# Extract all-pages text from a (scanned) PDF, OCR-ing if needed. Sanitize before use.
extract-pdf path:
    uv run scripts/extract_pdf_text.py "{{path}}"

# Encrypt report.html with a shared password and publish the encrypted file.
# Requires STATICRYPT_PASSWORD in the environment (e.g. in .env).
publish:
    npx staticrypt report.html -p "$STATICRYPT_PASSWORD" --short -o report.encrypted.html
    @echo "Encrypted report written to report.encrypted.html — push it to your GitHub Pages repo."
