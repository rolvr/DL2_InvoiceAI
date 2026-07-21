# Runbook

## 0. Setup (once)

```bash
git clone <repo-url>
cd invoice-image-processing
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Configure Kaggle credentials — see `dataset_sources.md`.

## 1. Get the data

```bash
python scripts/download_datasets.py --dataset all
python scripts/prepare_folders.py            # ensures data/interim, processed, annotations exist
python scripts/validate_dataset_paths.py      # sanity-checks that expected folders/files exist
```

Each dataset can also be pulled individually: `--dataset invoices|ocr_multitype|signatures|stamps`.

## 2. Run the pipeline, in order (each stage depends on the previous member's outputs)

Run notebooks either in Google Colab (open from GitHub, run top-to-bottom — each has a Colab
setup cell that mounts Drive / installs requirements / configures Kaggle) or locally with
Jupyter.

1. `members/rolando_data_ingestion/01_rolando_data_ingestion_preparation.ipynb`
   → produces `data/processed/invoice_manifest.csv` and quality report/figures.
2. `members/diana_stamp_signature/02_diana_stamp_signature_detection.ipynb`
   → produces stamp/signature predictions, metrics, model weights.
3. `members/jordan_region_iou/03_jordan_region_detection_iou.ipynb`
   → produces region predictions, IoU metrics, model weights.
4. `members/damir_ocr_terms/04_damir_ocr_parameter_terms_extraction.ipynb`
   → consumes Jordan's + Diana's outputs, produces OCR/parameter/terms results.
5. `members/hessam_pm_integration/05_hessam_integration_streamlit_demo.ipynb`
   → validates all prior outputs exist, builds final JSON per invoice, writes the report.

Run `scripts/validate_dataset_paths.py` (or the equivalent check cell in Hessam's notebook)
before step 5 to catch missing upstream outputs early.

## 3. Run the Streamlit demo

```bash
streamlit run app/streamlit_app.py
```

Upload an invoice image; the app runs preprocessing → region/stamp/signature detection → OCR
→ parameter/terms checks → shows the final Pistac.io-readiness JSON, with a download button.

## 4. Manual annotation (only needed if `data/annotations/layout_bboxes.csv` is missing region
   labels for `terms_and_conditions_region`, `payment_terms_region`, `reference_numbers_region`,
   `line_items_table`, `total_amount_region`)

1. Pick 50–150 representative invoice images from `data/raw/invoices/` (Rolando's manifest
   makes this easy — sample across the `split` column).
2. Install and open **LabelImg** (`pip install labelImg`, then run `labelImg`) or use
   **makesense.ai** (no install, browser-based) — either produces per-image bounding boxes.
3. Use the label list in `config/label_schema.json` → `region_labels` as your class list.
4. Export/convert annotations to the shared CSV schema (use
   `scripts/convert_annotations.py` if your tool exports Pascal VOC XML or YOLO txt):
   ```
   document_id,image_path,label,xmin,ymin,xmax,ymax,split,annotation_source
   ```
5. Save to `data/annotations/layout_bboxes.csv` (merge with any existing rows rather than
   overwriting). Jordan's notebook reads this file directly.

## 5. Common issues

| Symptom | Fix |
|---|---|
| `kaggle: command not found` / 401 errors | Re-check `~/.kaggle/kaggle.json` placement and permissions; see `dataset_sources.md`. |
| Downloaded zip didn't unzip | Re-run `download_datasets.py` — it retries unzip separately from download; check disk space. |
| Jordan/Damir notebook can't find upstream CSV | Confirm the upstream member ran their notebook's final export cell and wrote to the exact path in `model_interface_contract.md`, not just their local `members/<name>/outputs/` copy. |
| Streamlit app shows all-missing JSON | It falls back to "not detected" when a stage's output file is absent — run the missing member's notebook first, or check `outputs/reports/final_pipeline_report.md` for what Hessam's validation step flagged. |
| OCR text is garbage | Usually a preprocessing/skew issue — check Rolando's `preprocessing_examples.png`; try `deskew` step before re-running Damir's OCR. |
