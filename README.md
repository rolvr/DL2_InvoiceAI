# Invoice Region Detection and Business Parameter Extraction Using CNN, SSD, IoU, OCR, and Streamlit

Deep Learning II group project (George Brown College). The system takes an invoice image and
determines whether it is ready to become a structured digital obligation record — detecting
visual elements (stamp, signature), locating business-critical regions (line items, totals,
payment terms, terms & conditions, reference numbers), running OCR only on those detected
regions, checking for required reference parameters, and extracting payment terms / due dates
into a final JSON record for a Pistac.io-style workflow.

This is a computer-vision object-detection project first, an OCR project second. The pipeline
is: **image preprocessing → CNN feature learning → SSD-style region/object detection with
bounding boxes → IoU evaluation → OCR on detected crops → parameter/terms extraction → Streamlit
demo.**

## Team

| Member | Role | Notebook |
|---|---|---|
| Hessam | PM, Solution Architect, Integration Lead, Streamlit Lead | `members/hessam_pm_integration/05_hessam_integration_streamlit_demo.ipynb` |
| Rolando | Data Ingestion, Dataset Management, Data Preparation | `members/rolando_data_ingestion/01_rolando_data_ingestion_preparation.ipynb` |
| Diana | Annotation, Stamp Detection, Signature Detection | `members/diana_stamp_signature/02_diana_stamp_signature_detection.ipynb` |
| Jordan | Invoice Region Detection, SSD/CNN, IoU Evaluation | `members/jordan_region_iou/03_jordan_region_detection_iou.ipynb` |
| Damir | OCR, Parameter Extraction, Terms & Conditions | `members/damir_ocr_terms/04_damir_ocr_parameter_terms_extraction.ipynb` |

See `project_plan.md` for scope, timeline, git workflow and assumptions;
`model_interface_contract.md` for exactly what file each member reads/writes;
`dataset_sources.md` for the Kaggle datasets used; `runbook.md` for how to run everything
end-to-end, in Colab or locally.

## Quickstart

```bash
pip install -r requirements.txt

# Configure Kaggle API credentials first (see dataset_sources.md), then:
python scripts/download_datasets.py --dataset all
python scripts/prepare_folders.py
python scripts/validate_dataset_paths.py

# Run the Streamlit demo (after member notebooks have produced outputs/*):
streamlit run app/streamlit_app.py
```

## Repository layout

```
invoice-image-processing/
├── config/                # required_fields_config.json, label_schema.json
├── scripts/                # dataset download / folder prep / validation / annotation conversion
├── data/                   # raw (gitignored), interim, processed, annotations (CSV), ocr_text
├── members/                # one folder per teammate — their notebook + README + outputs/
├── notebooks/               # mirrored copies of the 5 member notebooks for submission
├── src/                     # shared, importable utility modules used by all notebooks
├── models/                  # trained detector weights (gitignored binaries, tracked README)
├── outputs/                 # shared integration point: metrics, figures, predictions, final_json, reports
├── app/                     # streamlit_app.py — the final demo
├── presentation/           # slide outline + demo script
└── ai_cowork/               # Opus master plan + per-member AI agent prompts + AI usage log
```

## Core detection labels

Regions: `invoice_header, seller_info, buyer_info, invoice_number_region, date_region,
due_date_region, reference_numbers_region, line_items_table, subtotal_region, tax_region,
total_amount_region, payment_terms_region, terms_and_conditions_region, bank_details_region`

Visual elements (kept as two **separate** labels, never merged): `stamp`, `signature`

## AI usage

This repository was scaffolded with AI assistance (Claude, acting as master planner/architect).
See `ai_usage_log.md` and `ai_cowork/logs/ai_usage_log.md` for a record of AI-assisted work,
as required by course policy.
