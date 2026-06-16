# Claude instructions for resident-expenses

This project handles a comunidad de vecinos' financial data. The following rules are not negotiable.

## Hard rule: never read real financial data

Never directly read the source PDFs, the `data/` JSON files, or the stdout/printed output
of any tool that reads them, **unless the user explicitly authorizes it for a specific
task**. Default to delegating reading to code and verifying via synthetic fixtures or the
user opening the HTML report. Sanitized pastes (real values replaced with
format-preserving fakes) are always allowed.

The canonical pipeline input is hand-correctable JSON under `data/` (one `<year>.json`
per exercise). It contains real financial data and is gitignored.

## Architecture (data flow)

1. **Extract** (manual, per source PDF): `just extract-pdf <pdf>` → text
   (`extract/pdf_text.py` + `extract/ocr.py`, via the external `ocrmypdf`/Tesseract `-l spa`;
   scanned PDFs have no text layer, so OCR is required).
2. **Author** (manual, per exercise): hand-write `data/<year>.json` from the extracted text
   — one transaction object per ledger line. The report's alerts pinpoint any cell to fix.
3. **Report** (`uv run resident-expenses report`): `data_json.py` loads the JSON →
   `reconcile.py` runs checks → `report/render.py` emits one self-contained `report.html`.

`config.json` (gitignored) needs only `building_name`, `currency`, and `data_dir`.
Located via `--config` > `RESIDENT_EXPENSES_CONFIG` > `./config.json`.

## Transaction shape: label, category, sign

Each transaction is `{date, label, category, amount}` with an optional `kind`. Income vs.
expense follows the **amount's sign by default** (income positive, expense negative; `0`
counts as income) — `Transaction.kind` in `models.py` falls back to the sign when not given.
An explicit `"kind": "income"|"expense"` is the **section override**, used only for a
ledger reversal whose sign disagrees with its section: e.g. a refund inside the INGRESOS
section is a negative amount that is still income. `data_json.py` stores the amount verbatim
and validates `kind`.

`label` is the transaction's **title: the concept/description column, verbatim** from the
ledger line. `category` is its own JSON field — **hand-curated** in `data/<year>.json` to
merge the title variants into groups, without touching the title. The report colors/groups
by `category`; the core treats it as opaque. No category names belong in committed code.

Contribution lines (`Abono de <name>`) keep the owner's real name verbatim as the title.
Names therefore appear in the (StatiCrypt-encrypted) report, consistent with the source
cuentas.

## Alert kinds

`AlertKind` (in `models.py`): `SUMMARY_MISMATCH` (computed totals vs. the totals stated in
the data file's `summary`) and `MISSING_TRANSACTION` (a row flagged as recorded but never
occurred). To add a kind: extend the enum, emit `Alert(...)` from a check in `reconcile.py`;
the report renders them uniformly.

## Console output policy

`resident-expenses` prints only operational metadata (counts, file paths, structural
errors). Never amounts, category labels, dwelling identities, or per-row data.

## Testing

All tests use synthetic fixtures in `tmp_path` or inline. `just check` = ruff + mypy + pytest.

## Publishing

The publish toolchain lives in `web/` (a small npm project: `staticrypt` + `gh-pages`,
pinned, installed by `just install`). `just publish` runs `web/`'s `npm run deploy`, which
encrypts `report.html` with the shared `STATICRYPT_PASSWORD` (StatiCrypt) into
`web/dist/index.html`, then `gh-pages` force-pushes **only that directory** to the
`gh-pages` branch — GitHub Pages serves it. Because only `web/dist/` is published, the
plaintext report and `data/` can never reach the public branch; nothing sensitive is ever
committed to `main` either (`report.html`, `data/`, `web/dist/`, `web/node_modules/` are all
gitignored). StatiCrypt config is disabled (`-c false`), so each publish uses a fresh random
salt — fine since the report is republished wholesale.
