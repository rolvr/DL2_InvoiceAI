# data/

All dataset content lives here. **`raw/`, `interim/`, `processed/`, and `ocr_text/` are
gitignored** (large, license-bound, or regenerable) — only `annotations/` (small, hand-curated
CSVs) is tracked in git.

| Folder | Contents | Populated by |
|---|---|---|
| `raw/invoices/` | High-Quality Invoice Images for OCR (Kaggle) | `scripts/download_datasets.py --dataset invoices` |
| `raw/signatures/` | SignverOD (Kaggle) | `scripts/download_datasets.py --dataset signatures` |
| `raw/stamps/` | StaVer stamp dataset (Kaggle) | `scripts/download_datasets.py --dataset stamps` |
| `interim/` | Intermediate artifacts during preprocessing (e.g. corrupt-image scratch space) | Rolando's notebook |
| `processed/` | `invoice_manifest.csv` and preprocessed images ready for modeling | Rolando's notebook |
| `annotations/` | Shared bounding-box CSVs (`layout_bboxes.csv`, `stamp_signature_bboxes.csv`, `field_presence_labels.csv`) | Diana / Jordan, plus any manual annotation pass — see `../runbook.md` |
| `ocr_text/` | Raw OCR text dumps per document/region, if saved separately from the predictions CSVs | Damir's notebook |

See `../dataset_sources.md` for exact Kaggle dataset details and `../scripts/download_datasets.py`
for the download automation.
