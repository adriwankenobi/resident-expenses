# resident-expenses

A single-user CLI for a comunidad de vecinos: it turns the administrator's scanned yearly
account PDFs into hand-correctable JSON and renders an interactive, self-contained HTML
report — publishable behind a shared password so every neighbor can read it.

## Install

```bash
just install
```

## Data flow

1. **Extract** text from a (scanned) PDF — OCRs automatically via `ocrmypdf` if there's no
   text layer (`brew install ocrmypdf tesseract-lang` first):
   ```bash
   just extract-pdf "/path/to/cuentas.pdf" > /tmp/cuentas.txt
   ```
2. **Author** `data/<year>.json` from the extracted text — one
   `{date, label, category, amount}` object per ledger line. The report's alerts pinpoint
   any cell that doesn't add up.
3. **Report** from the JSON:
   ```bash
   just report
   # or
   uv run resident-expenses report --config ./config.json --output ./report.html
   ```

## Configure

```bash
cp config.example.json config.json   # building_name, currency, data_dir
cp .env.example .env                 # RESIDENT_EXPENSES_CONFIG and STATICRYPT_PASSWORD
```
Config precedence: `--config` flag > `RESIDENT_EXPENSES_CONFIG` env var > `./config.json`.

## Publish (access control)

The report is a single HTML file. `just publish` encrypts it with a shared password
(StatiCrypt, AES-decrypted in the browser) into `report.encrypted.html`. Push only that
encrypted file to a GitHub Pages repo. Neighbors open the URL and enter the shared
password — no server, no accounts, nothing stored in plaintext.

## Develop

```bash
just check   # ruff + mypy + pytest
just test    # pytest only
```

See `CLAUDE.md` for the architecture and data-handling rules.
