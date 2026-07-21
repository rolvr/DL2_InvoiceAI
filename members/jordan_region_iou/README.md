# Jordan — Invoice Region Detection, SSD/CNN Object Detection, IoU Evaluation Lead

**Notebook:** `03_jordan_region_detection_iou.ipynb`
**Branch:** `feature/jordan-region-iou`

## Role

Detect the business-critical invoice regions (line items table, totals, payment terms,
terms & conditions, reference numbers, seller/buyer info, etc.) using SSD-style object
detection, and evaluate predictions against ground truth using IoU. This is the core
Deep Learning II deliverable of the project — CNN feature learning, bounding-box regression,
and IoU evaluation.

## What this notebook does

1. Loads processed invoice images from Rolando.
2. Loads or creates bounding-box annotations for the 14 region labels in
   `config/label_schema.json` (`data/annotations/layout_bboxes.csv`) — see
   `../../runbook.md` "Manual annotation" if these don't exist yet for your images.
3. Detects the priority regions: `reference_numbers_region`, `line_items_table`,
   `total_amount_region`, `payment_terms_region`, `terms_and_conditions_region`,
   `seller_info`, `buyer_info` (plus any of the other 7 region labels feasible in scope).
4. Trains or demonstrates SSD-style detection (SSD, or the documented YOLOv8 fallback —
   see `../../model_interface_contract.md` and `../../requirements.txt`).
5. Implements/uses IoU evaluation (`src/iou.py` — the project's single shared implementation).
6. Saves `region_predictions.csv`, `region_iou_metrics.json`, and example figures.

## Input files

- `data/processed/invoice_manifest.csv` (Rolando)
- `data/annotations/layout_bboxes.csv`
- `config/label_schema.json`

## Output files

- `outputs/predictions/region_predictions.csv`
- `outputs/metrics/region_iou_metrics.json`
- `outputs/figures/region_detection_examples.png`
- `models/region_detector/`
- Mirrored copies in this folder's `outputs/`.

## How Hessam / Damir integrate this

Damir reads `region_predictions.csv` to know which crops to run OCR on. Hessam reads both
the predictions and `region_iou_metrics.json` (feeds `model_metrics.region_mean_iou`) for the
final JSON and pipeline report.

## Run in Colab

Open from GitHub in Colab, run top-to-bottom. Requires Rolando's manifest and the region
annotation CSV to exist first.

## Ground rules

- `src/iou.py` is the canonical IoU implementation — everyone imports it, no reimplementing.
- If using the YOLO fallback instead of true SSD, say so explicitly in your notebook markdown
  and the presentation — don't call it SSD.
- Don't edit other members' folders under `members/`.
