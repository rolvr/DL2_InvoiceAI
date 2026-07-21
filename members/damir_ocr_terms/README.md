# Damir — OCR, Parameter Extraction, Terms & Conditions Extraction Lead

**Notebook:** `04_damir_ocr_parameter_terms_extraction.ipynb`
**Branch:** `feature/damir-ocr-terms`

## Role

Run OCR **only** on the regions Jordan detected (not the whole invoice page), check for
required reference parameters, and extract payment terms / due dates / terms & conditions
signals (late payment, dispute, penalty language).

## What this notebook does

1. Loads region predictions from Jordan and stamp/signature predictions from Diana.
2. Crops detected regions from invoice images.
3. Runs OCR (EasyOCR by default, PyTesseract as fallback — see `src/ocr.py`).
4. Extracts text specifically from: `reference_numbers_region`, `payment_terms_region`,
   `terms_and_conditions_region`, `total_amount_region`, `invoice_number_region`,
   `due_date_region`.
5. Loads required fields from `config/required_fields_config.json` and checks each one
   (PO Reference, Order Number, Contract Number, Project Reference, Insurance Policy
   Number, Bill of Lading Number) — plus any user-defined custom fields.
6. Extracts payment terms and due dates.
7. Extracts terms & conditions context and flags late-payment/dispute/penalty language.
8. Saves everything to CSV/JSON.

## Input files

- `outputs/predictions/region_predictions.csv` (Jordan)
- `outputs/predictions/stamp_signature_predictions.csv` (Diana)
- `config/required_fields_config.json`

## Output files

- `outputs/predictions/ocr_outputs.csv`
- `outputs/predictions/parameter_presence_results.csv`
- `outputs/predictions/terms_extraction_results.csv`
- `outputs/metrics/ocr_parameter_metrics.json`
- Mirrored copies in this folder's `outputs/`.

## How Hessam integrates this

Hessam's notebook joins these three CSVs on `document_id` to fill in `required_parameters`,
`payment_context`, and `terms_and_conditions` in the final JSON, and uses
`ocr_parameter_metrics.json` for the pipeline report.

## Run in Colab

Open from GitHub in Colab, run top-to-bottom. Requires Jordan's and Diana's outputs to exist
first — this notebook is a consumer, not a source, of region/stamp/signature detections.

## Ground rules

- OCR only detected crops — running OCR over the full page defeats the point of the
  detection-first pipeline design.
- Read the field list from `config/required_fields_config.json`, don't hardcode it, so
  custom fields added via the Streamlit sidebar stay in sync.
- Don't edit other members' folders under `members/`.
