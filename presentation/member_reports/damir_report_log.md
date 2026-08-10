# Damir — OCR, Business Parameters & Terms · Report Log

> Destination in repo: `presentation/member_reports/damir_report_log.md`
> Numbers from the corrected notebook 04 (v3), EasyOCR over all 750 invoices, honest matching.

## Role
Read the text (OCR), then extract **business parameters** (PO/Order/Contract/Work-Order/Insurance/
BOL references) and **payment terms** (invoice date, due days, late-payment/dispute/penalty
clauses) — the signals the readiness verdict depends on.

## Model & method
- **EasyOCR** (deep-learning OCR) for text. Chosen over Tesseract for better out-of-the-box
  accuracy and no external binary; runs on GPU in Colab, CPU in the app.
- **Rule-based extraction** via the shared, unit-tested `src/parameter_checker.py` and
  `src/terms_extraction.py` — transparent, no training data needed, user-extendable via
  `config/required_fields_config.json`.

## OCR quality (primary eval — OCR-Dataset test split, 98 docs, 100% GT)
| Metric | Value |
|---|---|
| CER (mean / median) | 0.215 / 0.175 |
| WER (mean / median) | 0.543 / 0.523 |

Secondary invoice CER is ~0 but **circular** (the batch-1 "OCRed Text" GT was itself OCR-derived),
so it's reported only with that caveat, not as a headline.

## Invoice-level signals (all 750, honest)
| Signal | Rate |
|---|---|
| Any **required reference** (PO/Order/Contract) | **~0%** (0/750) |
| Parseable invoice **date** | 100% |
| **Payment terms** / billing due days | 0.8% |
| Late-payment / dispute / penalty **clauses** | 0% |

## What I found and fixed (this was the real readiness work)
The notebook shipped with two silent bugs that starved the readiness engine:
1. **Terms extraction returned nothing** — it called function names that don't exist in
   `terms_extraction.py`, so it silently returned `{}` (0% terms).
2. **Parameter checking used a crude fallback** — same wrong-name bug, so it never called the real
   `parameter_checker` and checked the wrong fields.
3. **Nothing was invoice-keyed** — only 98 receipts + 120 invoices were processed, not the 750.

Fixes: call the real modules, OCR **all 750 invoices keyed by `document_id`**, emit the exact
contract-schema CSVs, add a Drive OCR cache, and **tighten matching** (drop the 2-letter `"po"`
keyword and catch-all regex; require label + digits) with a `matched_text` audit.

## Honest headline
The original **59.2% / 63.3% readiness was a false positive** — the loose `"po"` keyword matched
words like "report"/"deposit" and catch-all patterns matched phone numbers. Corrected, required
references are **~0%**: these documents are retail-receipt-style scans that **don't carry
PO/contract references**. That's the receipts→invoices / procurement **domain gap**, not an OCR
failure. Payment terms are genuinely rare (0.8%) on this data.

## Handoff
`ocr_outputs.csv`, `parameter_presence_results.csv` (schema: document_id, field_name, required,
present, matched_text, match_method), `terms_extraction_results.csv` (invoice_date, due_date,
payment_terms, billing_due_days, late/dispute/penalty flags, extracted_text, summary), and
`ocr_parameter_metrics.json` — published to `outputs/damir/` and `inputs/upstream/damir/` for
Hessam's integration (notebooks 05/06).

## Q&A rehearsal
- **What are CER/WER?** Character / Word Error Rate for OCR — lower is better.
- **Why rule-based extraction on top of OCR?** Transparent and extendable (a new field is a config
  entry, no retraining); appropriate for a compliance gate where you must explain every decision.
- **Why report the denominator?** Only ~197 of 750 invoices have any GT text; a headline OCR score
  without the denominator would be misleading.
- **Which parameters are hardest?** All B2B references — they're essentially **absent** from this
  corpus; that's a data property, and forcing them would be fabrication.
- **What changed the 63.3%?** A string-matching bug; corrected matching + real per-invoice signals
  replaced it, and an audit confirmed the surviving matches are real identifiers.
