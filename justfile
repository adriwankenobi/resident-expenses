set dotenv-load := true

# Prepend Homebrew node so the web/ npm scripts bypass the system/nvm node,
# which is too old for staticrypt/gh-pages.
export PATH := "/usr/local/opt/node/bin:" + env_var('PATH')

default:
    @just --choose

# Install dependencies: Python (uv) + the web/ publish toolchain (npm).
install:
    uv sync
    cd web && npm install

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

# Encrypt report.html and publish it to GitHub Pages (gh-pages branch).
# Requires STATICRYPT_PASSWORD in the environment (e.g. in .env) and `just install`.
# The web/ scripts encrypt report.html into web/dist/index.html and push ONLY
# that file, so no plaintext report or data/ can ever reach the public branch.
publish:
    cd web && npm run deploy
    @echo "Published. Pages URL: https://adriwankenobi.github.io/resident-expenses/"
