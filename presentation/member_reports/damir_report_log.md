# Report Log — Damir (OCR, Parameter Extraction, Terms & Conditions Extraction Lead)

_Last updated: 2026-07-23 (completion pass — see "Completion note" below)._

## 1. Objective (what I was responsible for)
Run OCR on Jordan's detected region crops, check required reference parameters, and extract
payment terms / due dates / terms & conditions signals.

## 2. What I did
- Ran **EasyOCR** (GPU, Colab) over 120 real `batch_1` invoice images and the 98-image OCR-Dataset
  receipt test split, producing `outputs/predictions/ocr_outputs.csv` (whole-page OCR text per
  document, `source ∈ {invoice_batch1, ocr_dataset_test}`) — this OCR text is real model output
  and untouched by the completion pass below.
- Scored that OCR against ground truth on both sets: the OCR-Dataset receipts (per-box GT
  transcriptions, 100% of the 98-image test split) as the **primary** headline metric, and the 120
  batch_1 invoices against the `batch_1` annotation CSVs' ground-truth text as a **secondary**
  metric.
- Built `src/parameter_checker.py` (keyword + regex presence checks against
  `config/required_fields_config.json`) and `src/terms_extraction.py` (date/payment-terms regexes,
  late-payment/dispute/penalty clause keyword detection, light extractive summary) as shared,
  reusable modules — used identically by the notebook and by `app/streamlit_app.py`.
- **Completion pass (CPU-only, no GPU/OCR/notebook re-run):** the notebook's terms-adapter cells
  called `extract_terms_and_conditions(region_texts)`, which expects text split per region label
  ("payment_terms_region", etc.) that doesn't exist for whole-page OCR text, so
  `parameter_presence_results.csv` never reached the contract schema, and both prediction CSVs
  only covered the 218 OCR'd/scored documents, not the 750-invoice manifest. Once the manifest
  became 100% `batch_1` (all 750 rows have ground-truth OCR text in the annotation CSVs), I wrote
  `scripts/complete_damir_outputs.py` to regenerate both CSVs at the contract's long schema across
  all 750 invoices, calling my existing `check_all_fields` / terms functions unmodified against
  Damir-OCR-text-where-available-else-annotation-text. See the completion note at the bottom.

## 3. Approach & key decisions
- **EasyOCR over Tesseract/PaddleOCR:** stronger out-of-the-box accuracy, no external binary
  dependency, acceptable Colab GPU time budget.
- **Rule-based extraction over a learned extractor:** no labelled training data exists for fields
  like "PO Reference" or "Work Order No." across our datasets; every match is traceable to an
  exact keyword or regex (auditable for a compliance-adjacent tool); a user can add a new required
  field from `config/required_fields_config.json` with zero code changes.
- **Report both evaluation sets, always together, never one headline number:** the receipt test
  split has 100% ground-truth coverage but is genuinely hard OCR (skewed/low-res photos); the
  batch_1 invoice sample is easy (clean digital renders) but small relative to a "production"
  claim. Presenting either alone would misrepresent the system.
- **Text-source priority for the 750-invoice completion:** Damir's real EasyOCR text first
  (`source == "invoice_batch1"`), batch_1 annotation ground-truth text as fallback
  (`source == "invoice_annotation"`) — this mirrors the fallback `src/results_store.py` already
  used for the live app, so the completion pass just makes the *published CSVs* match what the
  app already derived ad hoc.

## 4. Challenges faced & how I handled them
- **Challenge:** the notebook's terms-adapter cells assumed region-split OCR text
  (`region_label` keyed dict) that the actual `ocr_outputs.csv` schema (whole-page text) doesn't
  provide, so `extract_terms_and_conditions()` couldn't run as written and
  `parameter_presence_results.csv` ended up as an unrelated wide receipt-only table.
  - **Resolution:** call the underlying functions directly (`extract_dates`,
    `extract_payment_terms`, `extract_billing_due_days`, `detect_clauses`, `summarize_terms`) on
    whole-page text instead of the region-dict wrapper — same shared logic, just applied at
    whole-document granularity, which is what's actually available outside of Jordan's cropped
    regions.
- **Challenge:** only 120 of 750 manifest invoices had real GPU OCR — publishing prediction CSVs
  keyed to just those 120 (or worse, to the 98 unrelated receipts) would make Hessam's
  `final_json_builder.build_required_parameters` produce empty/wrong results for 84% of the
  manifest.
  - **Resolution:** once the manifest became 100% `batch_1` (every image has ground-truth OCR text
    in the annotation CSVs), fall back to that ground-truth text for the ~630 invoices without real
    OCR — zero additional OCR/GPU work, and it's the same source `results_store.py` already trusted.
- **Challenge:** `jiwer` is not installed in the local CPU-only completion environment (and no
  network access to install it).
  - **Resolution:** implemented a small dependency-free Levenshtein-based CER/WER
    (lower-cased, whitespace-collapsed) in `scripts/complete_damir_outputs.py`, and verified it
    reproduces the GPU run's stored receipt CER/WER (0.2152 / 0.5423) exactly when applied to the
    same receipts against locally-available ground truth
    (`data/raw/invoices/OCR Dataset of Multi-type Documents/invoice/*/annotations/*.json`) before
    trusting it for the new invoice-side computation.

## 5. Results & metrics
**Primary (OCR Dataset receipt test split, 98 images, real GPU EasyOCR + real per-box GT):**
CER 0.2152 mean / 0.1751 median, WER 0.5423 mean / 0.5225 median.

**Secondary (120 real batch_1 invoices, GPU EasyOCR vs. annotation ground truth):**
CER 0.0002 mean / 0.0000 median, WER 0.0015 mean / 0.0000 median — near character-perfect, but on
clean, digitally-rendered invoices, not scanned photos. Report both numbers together; never quote
0.0002 as if it represents the same difficulty as the 0.2152 receipt figure.

**Invoice-text coverage (all 750 manifest invoices, completed locally on CPU):** 120 real EasyOCR
+ 630 `batch_1` annotation fallback = 750/750 (100%).

**Business-parameter presence rate** (`check_all_fields`, all 750 invoices):
PO Reference 54.7% (required), Order Number 19.9% (required), Contract Number 1.1%, Project
Reference 0.0%. Work Order No. / Insurance Policy Number / Bill of Lading Number each show 100%,
but that is a **false-positive artifact** of permissive config patterns on this corpus (e.g. the
Bill-of-Lading regex matches the plain word "INVOICE") rather than genuine detection — see
`parameter_presence_rate_caveat` in `ocr_parameter_metrics.json`. Required-field presence rate
(the two fields that actually gate readiness): **37.3%**.

**Terms parseability (all 750 invoices):** 99.6% have a parseable `invoice_date`; only **0.4% (3
invoices)** match any day-based payment-terms phrasing or yield `billing_due_days`. Explicit
"Net 30"-style terms are essentially absent from this corpus's text, so the verdict engine's
payment-terms rule is `unknown → fail-closed` for nearly every invoice — a real corpus limitation,
not an extraction-logic bug.

## 6. Assumptions & limitations
- OCR was run only on whole-page images/crops actually available (120 real invoices, 98 receipts);
  the remaining 630 invoices use ground-truth annotation text as a stand-in for OCR text, not a
  model's OCR output — this is explicitly labelled `source == "invoice_annotation"` everywhere so
  it's never confused with real OCR.
- No per-region OCR/terms split exists outside Jordan's cropped regions, so `extracted_text` in
  `terms_extraction_results.csv` is `None` for whole-page rows (only a `summary` is populated) —
  this matches how the file already behaved for the original 218 rows.
- `check_all_fields`'s keyword search is case-insensitive **substring** search with no word
  boundaries, and several config regex patterns are broad (`[A-Z0-9-]{6,20}` etc.) — this is a
  known, pre-existing property of the shared, unmodified function, not something introduced by the
  completion pass, but it does inflate several optional fields' presence rate on this corpus (see
  §5). I did not modify `parameter_checker.py` or `config/required_fields_config.json` — that is
  out of scope for this completion pass.
- `due_date` is only ever the *second* date found in a document's text (a heuristic, since there's
  no dedicated due-date region for whole-page text) and is almost always null as a result — this
  mirrors the pre-existing 218-row file's behavior and is intentionally conservative rather than
  guessing.
- CER/WER for the invoice secondary set could only be computed for the 120 invoices where BOTH
  real OCR text AND annotation ground truth exist; this is different from (smaller than) the
  750/750 text-*coverage* figure used for parameter/terms extraction, and the two numbers should
  never be conflated (see `ocr_secondary_invoices.denominator_note` in the metrics JSON).

## 7. Handoff notes (for downstream members / integration)
- `outputs/predictions/ocr_outputs.csv`: `document_id, image_path, ocr_text, mean_confidence,
  n_boxes, source`. `source` is one of `invoice_batch1` (real EasyOCR), `ocr_dataset_test` (real
  EasyOCR, receipts), or `invoice_annotation` (ground-truth text fallback, `mean_confidence` /
  `n_boxes` intentionally null — there's no OCR confidence for text that wasn't OCR'd).
  `results_store.invoice_ocr_text()` already treats anything with `source` starting with
  `"invoice"` as invoice text, so no changes were needed there.
- `outputs/predictions/parameter_presence_results.csv`: contract long schema
  (`document_id, field_name, required, present, matched_text, match_method`), 750 invoices × 7
  fields = 5,250 rows. This is what `src/final_json_builder.build_required_parameters` consumes
  directly per `document_id`.
- `outputs/predictions/terms_extraction_results.csv`: contract schema, one row per document —
  750 invoices + 98 receipts = 848 rows, `source` column distinguishes provenance.
- `outputs/metrics/ocr_parameter_metrics.json`: `ocr_primary` and `_run` are the original GPU-run
  numbers, untouched. Everything else (`ocr_secondary_invoices`, `text_coverage`,
  `parameter_presence_rate` (+ caveat), `required_field_presence_rate`, `terms_parseability`,
  `_local_receipt_cer_wer_check`) was added/recomputed locally by
  `scripts/complete_damir_outputs.py`, clearly labelled as such in `_run.completed_locally_note`.
- Reproducible: `python scripts/complete_damir_outputs.py` (CPU-only, idempotent, no GPU/network).

## 8. Figures / artifacts to consider for the slide deck
- Side-by-side CER/WER bar: 0.2152/0.5423 (receipts) vs. 0.0002/0.0015 (invoices) — the "report
  both, never one headline" story in one chart.
- A 750-invoice text-coverage donut: 120 real-OCR / 630 annotation-fallback / 0 missing.
- The payment-terms-parseability finding (99.6% invoice_date vs. 0.4% payment-terms phrase) as a
  simple two-bar chart — it's the clearest "honest limitation" visual in Damir's section.

## Completion note (CPU-only, no GPU/OCR/notebook execution)
This report's numbers were finalized by `scripts/complete_damir_outputs.py`, which regenerates
`parameter_presence_results.csv`, `terms_extraction_results.csv`, `ocr_outputs.csv` (append-only:
Damir's 218 real OCR rows are never modified), and `ocr_parameter_metrics.json` from files already
in the repo — the batch_1 annotation CSVs and the existing `ocr_outputs.csv`. No GPU, no EasyOCR
re-run, no network call, no notebook execution.
