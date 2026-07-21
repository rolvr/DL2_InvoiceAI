# Dataset Sources

All datasets are pulled via the Kaggle API. Run `python scripts/download_datasets.py --dataset all`
after configuring credentials (see below), or download an individual dataset with `--dataset <name>`.

## Kaggle API setup (one-time)

1. Log into Kaggle → Account → "Create New API Token" → downloads `kaggle.json`.
2. **Local machine**: place it at `~/.kaggle/kaggle.json` (Linux/Mac) or
   `C:\Users\<you>\.kaggle\kaggle.json` (Windows), and ensure it's not world-readable
   (`chmod 600 ~/.kaggle/kaggle.json` on Linux/Mac).
3. **Google Colab**: upload `kaggle.json` at the start of the notebook, then run:
   ```python
   import os, pathlib, shutil
   pathlib.Path("/root/.kaggle").mkdir(exist_ok=True)
   shutil.move("kaggle.json", "/root/.kaggle/kaggle.json")
   os.chmod("/root/.kaggle/kaggle.json", 0o600)
   ```
   Every member notebook's "Colab setup cell" includes this snippet.
4. Never commit `kaggle.json` — it is excluded via `.gitignore`.

## Datasets

### 1. Primary invoice dataset — High-Quality Invoice Images for OCR
- Kaggle: https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr
- CLI slug: `osamahosamabdellatif/high-quality-invoice-images-for-ocr`
- Target: `data/raw/invoices/`
- Purpose: primary invoice images — layout diversity, field extraction, structured output.
- Owner: Rolando (ingestion), used by everyone downstream.

### 2. Secondary OCR/bounding-box dataset — OCR Dataset of Multi-type Documents
- Kaggle: https://www.kaggle.com/datasets/senju14/ocr-dataset-of-multi-type-documents
- CLI slug: `senju14/ocr-dataset-of-multi-type-documents`
- Target: `data/raw/invoices_ocr_multitype/`
- Purpose: bounding-box OCR annotations; filter to invoice/document categories where available.
  Used to supplement region-detection training data (Jordan) and OCR validation (Damir).

### 3. Signature dataset — SignverOD
- Kaggle: https://www.kaggle.com/datasets/victordibia/signverod
- CLI slug: `victordibia/signverod`
- Target: `data/raw/signatures/`
- Purpose: signature detection with bounding boxes, for IoU evaluation.
- Owner: Diana. Label must be `signature` — a distinct label from `stamp`.

### 4. Stamp dataset — Stamp Verification StaVer Dataset
- Kaggle: https://www.kaggle.com/datasets/rtatman/stamp-verification-staver-dataset
- CLI slug: `rtatman/stamp-verification-staver-dataset`
- Target: `data/raw/stamps/`
- Purpose: stamp detection on scanned/generated invoice-like documents.
- Owner: Diana. Label must be `stamp` — a distinct label from `signature`.

### 5. Optional fallback — Invoice-OCR
- Kaggle: https://www.kaggle.com/datasets/senju14/invoice-ocr
- CLI slug: `senju14/invoice-ocr`
- Target: `data/raw/invoices_fallback/`
- Purpose: fallback OCR/text-extraction source if the primary invoice dataset's structure
  proves difficult to work with. Not downloaded by `--dataset all`; fetch explicitly with
  `--dataset invoice_ocr_fallback` if needed.

## Custom annotation subset (not on Kaggle)

Several required region labels (`terms_and_conditions_region`, `payment_terms_region`,
`reference_numbers_region`, `line_items_table`, `total_amount_region`) are **not** present in
any of the datasets above. Diana/Jordan will hand-annotate a 50–150 image subset using LabelImg
or makesense.ai and export to `data/annotations/layout_bboxes.csv` in the schema:

```
document_id,image_path,label,xmin,ymin,xmax,ymax,split,annotation_source
```

See `runbook.md` → "Manual annotation" for the step-by-step process.
