# Model / Output Interface Contract

This is the single source of truth for **exactly which files each member reads and writes**.
If you change a schema here, ping the downstream consumer(s) listed before merging to `dev`.

## Data flow

```
Rolando ──manifest──▶ Diana ──stamp/sig preds──▶ Hessam
   │                     │
   └─────────────────────┼──▶ Jordan ──region preds──▶ Damir ──OCR/params/terms──▶ Hessam
                          └──────────────────────────────────────────────────────▶ Hessam
```

Damir depends on Jordan (region boxes to crop) and Diana (stamp/signature presence).
Hessam depends on all four.

## 1. Rolando → everyone

| File | Format | Key columns |
|---|---|---|
| `data/processed/invoice_manifest.csv` | CSV | `document_id, image_path, width, height, file_type, is_corrupt, split(train/val/test)` |
| `outputs/reports/data_quality_report.md` | Markdown | free-form: counts, corrupt/flagged images, dimension stats |
| `outputs/figures/sample_invoice_grid.png` | PNG | grid of sample raw images |
| `outputs/figures/preprocessing_examples.png` | PNG | before/after preprocessing |

`document_id` is the join key used by every downstream CSV.

## 2. Diana → Hessam (and Damir, for stamp/signature presence)

| File | Format | Key columns |
|---|---|---|
| `outputs/predictions/stamp_signature_predictions.csv` | CSV | `document_id, image_path, label(stamp\|signature), xmin, ymin, xmax, ymax, confidence` |
| `outputs/metrics/stamp_signature_metrics.json` | JSON | `{"stamp": {"precision":, "recall":, "mean_iou":}, "signature": {...}}` |
| `outputs/figures/stamp_signature_detection_examples.png` | PNG | example predictions drawn on images |
| `models/stamp_detector/` | weights + a short `README.md` describing framework/version | — |
| `models/signature_detector/` | weights + a short `README.md` | — |

`label` values must be exactly `stamp` or `signature` — never merged, never renamed.

## 3. Jordan → Damir, Hessam

| File | Format | Key columns |
|---|---|---|
| `outputs/predictions/region_predictions.csv` | CSV | `document_id, image_path, label(one of config/label_schema.json region_labels), xmin, ymin, xmax, ymax, confidence` |
| `outputs/metrics/region_iou_metrics.json` | JSON | `{"per_label": {"<label>": {"precision":, "recall":, "mean_iou":}}, "overall_mean_iou": }` |
| `outputs/figures/region_detection_examples.png` | PNG | example predictions drawn on images |
| `models/region_detector/` | weights + short `README.md` | — |

`src/iou.py` (Jordan-owned) is the single shared IoU implementation — Damir and Hessam should
import it rather than reimplementing.

## 4. Damir → Hessam

| File | Format | Key columns |
|---|---|---|
| `outputs/predictions/ocr_outputs.csv` | CSV | `document_id, region_label, raw_text, confidence` |
| `outputs/predictions/parameter_presence_results.csv` | CSV | `document_id, field_name, required(bool), present(bool), matched_text, match_method(keyword\|regex)` |
| `outputs/predictions/terms_extraction_results.csv` | CSV | `document_id, invoice_date, due_date, payment_terms, billing_due_days, late_payment_flag, dispute_flag, penalty_flag, extracted_text, summary` |
| `outputs/metrics/ocr_parameter_metrics.json` | JSON | OCR coverage + parameter-detection summary stats |

Reads `config/required_fields_config.json` for the field list (including any user-added
custom fields) and Jordan's `region_predictions.csv` to know which crops to OCR.

## 5. Hessam consumes all of the above and produces

| File | Format |
|---|---|
| `outputs/final_json/sample_invoice_outputs/<document_id>.json` | one JSON per processed invoice, schema below |
| `outputs/reports/final_pipeline_report.md` | integration report |
| `app/streamlit_app.py` | the demo, reads live from the same `outputs/` files or from an uploaded image run through the pipeline |
| `presentation/demo_script.md` | demo script |

### Final JSON schema (`src/final_json_builder.py` builds this)

```json
{
  "document_id": "",
  "source_image": "",
  "visual_elements": {
    "stamp_detected": false,
    "signature_detected": false,
    "stamp_confidence": null,
    "signature_confidence": null
  },
  "detected_regions": {
    "reference_numbers_region": false,
    "line_items_table": false,
    "total_amount_region": false,
    "payment_terms_region": false,
    "terms_and_conditions_region": false
  },
  "required_parameters": {},
  "payment_context": {
    "invoice_date": null,
    "due_date": null,
    "payment_terms": null,
    "billing_due_days": null
  },
  "terms_and_conditions": {
    "region_detected": false,
    "late_payment_clause_detected": false,
    "dispute_clause_detected": false,
    "penalty_clause_detected": false,
    "extracted_text": "",
    "summary": ""
  },
  "pistacio_readiness": {
    "can_create_digital_obligation_record": false,
    "missing_fields": [],
    "risk_flags": []
  },
  "model_metrics": {
    "region_mean_iou": null,
    "stamp_iou": null,
    "signature_iou": null
  }
}
```

## Rules

- `document_id` must be stable and identical across every CSV — it is the join key.
- Never write into another member's `members/<name>/` folder.
- Always write to **both** your `members/<you>/outputs/` folder (working copy) **and** the
  shared `outputs/` folder path listed above (integration copy) where a shared path is listed.
- Don't rename output files — Hessam's integration notebook and `streamlit_app.py` hardcode
  the paths in this contract.
