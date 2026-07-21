# Project Plan

## 1. Goal

Process an invoice image through a detection + OCR pipeline and answer, per invoice:

1. Is there a stamp? Is there a signature? (kept as two separate detectors/labels)
2. Are the important invoice regions detected (header, seller/buyer info, line items,
   totals, payment terms, terms & conditions, reference numbers, ...)?
3. Is the line-items table present? Is the total amount region present?
4. Is terms & conditions present, and what does it say (late payment / dispute / penalty
   language, due date)?
5. Are required reference parameters present (PO number, order number, contract number,
   project reference, insurance policy number, bill of lading number)?
6. Can this invoice become a structured digital obligation record for Pistac.io? What's
   missing if not?

Output: one JSON record per invoice (schema in `model_interface_contract.md`), surfaced through
a Streamlit demo.

## 2. Why this is a Deep Learning II project, not just an OCR project

The grading-relevant path is: preprocessing → CNN → SSD-style object detection with bounding
boxes → IoU evaluation → region classification. OCR is deliberately the *last* step and only
runs on crops produced by the detector, not on the whole page. Jordan's IoU evaluation and
Diana's stamp/signature detector are the core CV deliverables; Damir's OCR/parameter work is
downstream consumption of those detections.

## 3. Team & ownership

| Member | Owns | Must not touch |
|---|---|---|
| Rolando | `members/rolando_data_ingestion/`, `data/`, `scripts/download_datasets.py`, `scripts/prepare_folders.py`, `scripts/validate_dataset_paths.py` | other members' notebooks/outputs |
| Diana | `members/diana_stamp_signature/`, `models/stamp_detector/`, `models/signature_detector/` | other members' notebooks/outputs |
| Jordan | `members/jordan_region_iou/`, `models/region_detector/`, `src/iou.py`, `src/layout_detection.py` | other members' notebooks/outputs |
| Damir | `members/damir_ocr_terms/`, `src/ocr.py`, `src/parameter_checker.py`, `src/terms_extraction.py` | other members' notebooks/outputs |
| Hessam | `members/hessam_pm_integration/`, `app/`, `src/final_json_builder.py`, `src/streamlit_helpers.py`, integration + presentation | reworking others' modeling choices without discussion |

Shared, everyone may propose edits via PR: `src/config.py`, `src/data_loader.py`,
`src/image_preprocessing.py`, `src/annotation_utils.py`, `src/visualization.py`,
`config/*.json`.

## 4. Implementation choices / assumptions (documented per "no clarification" rule)

- **Detector architecture**: SSD is the course-required concept and is documented throughout
  (architecture diagrams, presentation, report). For the actual trained artifact, a lightweight
  **Ultralytics YOLOv8n** model is the implementation fallback if full SSD training is too slow
  for the class timeline — this is an explicit, documented substitution, never described as SSD.
  Whichever is used, the notebook must still explain SSD, bounding-box regression, and IoU.
- **Frameworks**: TensorFlow/Keras and PyTorch are both listed in `requirements.txt`; each
  member picks whichever they're more comfortable with per-notebook. No cross-notebook
  framework lock-in is required since integration happens at the CSV/JSON layer, not the
  model-object layer.
- **OCR engine**: EasyOCR is the default (better out-of-the-box accuracy, no external binary
  dependency); PyTesseract is kept as a fallback/comparison option in `src/ocr.py`.
- **Missing region labels**: The public datasets do not label `terms_and_conditions_region`,
  `payment_terms_region`, `reference_numbers_region`, `line_items_table`, or
  `total_amount_region` directly. Per the annotation strategy, Diana/Jordan will hand-annotate
  a subset of **50–150 invoice images** using LabelImg or makesense.ai (both free, offline-
  capable, produce simple bbox exports) and export to the shared CSV schema in
  `data/annotations/`. This is tracked as a risk — see `runbook.md`.
- **Dataset scale**: Full-dataset training is not required or expected to fit the course
  timeline. Notebooks default to a subset (e.g., a few hundred images) and document how to
  scale up if compute allows.
- **Repository is Colab-first**: every member notebook is written to run top-to-bottom in
  Google Colab (Drive mount + `pip install -r requirements.txt` + Kaggle API cell), and also
  runs locally against the same `data/` folder layout.
- **No absolute local paths anywhere**; all paths go through `pathlib` and `src/config.py`.

## 5. Git workflow

Branches:

- `main` — always demo-able
- `dev` — integration branch, everyone merges here first
- `feature/rolando-data-ingestion`
- `feature/diana-stamp-signature`
- `feature/jordan-region-iou`
- `feature/damir-ocr-terms`
- `feature/hessam-integration-streamlit`

Flow: each member commits to their own feature branch → opens PR into `dev` → Hessam (or peer)
reviews that the output-contract files were produced in the right place with the right schema →
merge into `dev`. Hessam periodically merges `dev` into `main` once the integration notebook
and Streamlit app run cleanly against current `dev` outputs.

## 6. Milestones (indicative — adjust to actual course calendar)

1. **Week 1** — repo scaffold (this), dataset download scripts verified, Rolando produces
   `invoice_manifest.csv` on a sample.
2. **Week 2** — Diana + Jordan produce first-pass detectors (even if weak) and predictions
   CSVs + metrics JSON on the sample set; annotation subset started if needed.
3. **Week 3** — Damir consumes Jordan/Diana outputs, produces OCR + parameter presence +
   terms extraction outputs.
4. **Week 4** — Hessam integrates everything into final JSON + Streamlit app; presentation
   materials drafted.
5. **Week 5** — polish, report, rehearsal, final submission.

## 7. Known risks

- Public datasets lack several required region labels → custom annotation subset required
  (see `runbook.md` "Manual annotation" section). This is the single biggest schedule risk.
- SignverOD / StaVer datasets are not invoice-specific; stamp/signature detectors trained on
  them may need light fine-tuning or domain adaptation to generalize to invoice scans.
- OCR quality on low-resolution or skewed scans can be poor; Rolando's deskew/denoise
  preprocessing step is load-bearing for Damir's OCR accuracy.
- Kaggle API rate limits / auth setup in Colab is a common first-day blocker — see
  `dataset_sources.md` for the exact `kaggle.json` setup steps.
