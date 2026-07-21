# Diana — Annotation, Stamp Detection, Signature Detection Lead

**Notebook:** `02_diana_stamp_signature_detection.ipynb`
**Branch:** `feature/diana-stamp-signature`

## Role

Detect **stamp** and **signature** as two separate object classes on invoice images, and
evaluate detection quality with precision/recall/IoU per class.

## Critical rule

`stamp` and `signature` must always be two separate labels — never merged into one class
(e.g. "authorization mark"), never renamed. Everything downstream (final JSON schema,
Streamlit UI, Pistac.io readiness logic) assumes this split.

## What this notebook does

1. Loads SignverOD (signatures, `data/raw/signatures/`) and StaVer (stamps, `data/raw/stamps/`).
2. Normalizes labels to exactly `stamp` / `signature`.
3. Prepares bounding-box annotations in the shared schema (`data/annotations/stamp_signature_bboxes.csv`).
4. Trains or demonstrates object detection for both classes.
5. Computes precision, recall, and IoU **separately** for stamp and for signature.
6. Saves example images with predicted boxes drawn.
7. Saves predictions to CSV and metrics to JSON.

## Input files

- `data/processed/invoice_manifest.csv` (Rolando)
- SignverOD / StaVer raw datasets — see `../../dataset_sources.md`

## Output files

- `outputs/predictions/stamp_signature_predictions.csv`
- `outputs/metrics/stamp_signature_metrics.json`
- `outputs/figures/stamp_signature_detection_examples.png`
- `models/stamp_detector/`, `models/signature_detector/`
- Mirrored copies in this folder's `outputs/`.

## How Hessam integrates this

`stamp_signature_predictions.csv` feeds `visual_elements.stamp_detected` /
`signature_detected` in the final JSON; `stamp_signature_metrics.json` feeds
`model_metrics.stamp_iou` / `signature_iou`. Damir also reads this file to know whether a
stamp/signature was found, without re-detecting it.

## Run in Colab

Open from GitHub in Colab, run top-to-bottom. Needs `data/raw/signatures/` and
`data/raw/stamps/` populated first (`scripts/download_datasets.py --dataset signatures` and
`--dataset stamps`).

## Ground rules

- Never merge stamp and signature into one label.
- Don't edit other members' folders under `members/`.
- Use `src/iou.py` for IoU — don't reimplement it.
