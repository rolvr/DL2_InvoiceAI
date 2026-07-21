# Rolando — Data Ingestion, Dataset Management, Data Preparation Lead

**Notebook:** `01_rolando_data_ingestion_preparation.ipynb`
**Branch:** `feature/rolando-data-ingestion`

## Role

Get the raw invoice data into a clean, validated, split, and preprocessed state that every
other member builds on. This is the foundation of the whole pipeline — if the manifest or
preprocessing here is wrong, every downstream detector and OCR step inherits the problem.

## What this notebook does

1. Downloads/loads the primary invoice dataset (`data/raw/invoices/`).
2. Validates folder paths and reads every image file.
3. Builds `invoice_manifest.csv` (document_id, path, dimensions, file type, corrupt flag, split).
4. Flags/removes corrupt images.
5. Splits into train/val/test.
6. Applies preprocessing: grayscale, resize, denoise, threshold, deskew.
7. Saves processed images and sample visualizations.
8. Writes `data_quality_report.md`.

## Input files

- Kaggle datasets configured in `../../dataset_sources.md`, pulled via
  `python scripts/download_datasets.py --dataset invoices` (run from repo root).

## Output files (both copies — see `../../model_interface_contract.md`)

- `data/processed/invoice_manifest.csv`
- `outputs/reports/data_quality_report.md`
- `outputs/figures/sample_invoice_grid.png`
- `outputs/figures/preprocessing_examples.png`
- Mirrored copies also saved to `outputs/` in this folder.

## How Hessam integrates this

Hessam's notebook reads `invoice_manifest.csv` as the master list of `document_id`s to build
final JSON records for, and uses `data_quality_report.md` in the final pipeline report. Diana,
Jordan, and Damir all resolve image paths through this manifest via `src/data_loader.py`.

## Run in Colab

Open the notebook from GitHub in Colab, run top-to-bottom. The first cell handles repo
clone/dependency install/Kaggle credential upload; the rest runs unmodified locally too.

## Ground rules

- Don't hardcode absolute paths — use `src/config.py`'s `PATHS`.
- Don't edit other members' folders under `members/`.
- Keep `document_id` values stable — every other CSV joins on this column.
