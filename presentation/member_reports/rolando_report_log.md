# Rolando — Data Ingestion, Dataset Management & Data Preparation · Report Log

> The foundation of the pipeline: turn a messy tree of invoice scans into one clean, validated,
> split manifest every other member joins on. No ML model — this is data engineering, and that's
> the point to present well.

## Role
Produce `data/processed/invoice_manifest.csv` (`document_id, image_path, width, height, split,
has_ground_truth`) + a data-quality report and preprocessing figures. `document_id` is the join
key for every downstream CSV.

## Key decisions (explain the *why*)
- **Annotation-aware sampling.** Naive sampling gave only **~26% ground-truth coverage** because
  annotation CSVs exist *only for batch_1*. Resampling to prefer annotated images lifted coverage
  to **100%** — **750 rows, split 525/120/105**. Trade-off: less cross-batch visual variety in
  exchange for fully-labelled data — a real engineering choice worth defending.
- **Duplicate discovery (data-leakage catch).** `batch_3/` secretly re-contains copies of batches
  1 & 2, so the true unique count is **5,201, not 8,181**. Sampling the duplicates would have
  leaked the same invoice into both train and test. Catching this is a strong talking point.
- **Stratified split** by ground-truth availability so every split stays fully labelled.
- **Preprocessing** (grayscale, resize, denoise, threshold, **deskew**) — load-bearing for Damir's
  OCR accuracy downstream.

## Outputs (contract)
`data/processed/invoice_manifest.csv`, `outputs/reports/data_quality_report.md`,
`outputs/figures/sample_invoice_grid.png`, `outputs/figures/preprocessing_examples.png`
(published to Drive `inputs/` for downstream notebooks; mirrored to `outputs/rolando/`).

## Challenge found & fixed
The Colab "refresh `inputs/images/`" step was **additive** — it copied the current images on top
of whatever was already there instead of replacing, so re-runs left a stale mixed set (the preflight
saw 1,393 then 1,689 files instead of 750, and manifest-path checks failed). Fix: **wipe
`inputs/images/` before repopulating** (`shutil.rmtree(...)` then copy), so it always holds exactly
the 750 manifest images. Lesson: a "refresh" that doesn't clear first isn't a refresh.

## How downstream uses this
Diana, Jordan, and Damir resolve image paths through the manifest; Hessam reads it as the master
list of `document_id`s to build final JSON for. Garbage in, garbage out — the whole pipeline's
honesty rests on this manifest.

## Q&A rehearsal
- Why is data leakage dangerous, and how did the `batch_3` duplicates threaten it?
- Why prefer annotated images despite losing visual variety?
- What is the final GT coverage per split, and is the test split big enough to report on?
- What would you do differently with annotations available for all batches?
