# Job Log — Member Agent Deployment Status

Structured resume state for the orchestrator. **On a new session, read this, then VERIFY
against the filesystem** (`python scripts/validate_dataset_paths.py` + `git log --all`) because
a job's real state may differ from what's recorded here if a previous session was interrupted.

Status values: `pending` · `in-progress` · `blocked` · `needs-verify` · `complete` · `failed`

> Note: subagent IDs are session-scoped and are recorded only for the CURRENT session's
> notifications. After a session break they are dead — re-deploy a fresh agent for any job not
> verified `complete` on disk. Do not treat a recorded agentId as reattachable from a new session.

## ⏸️ PAUSED for session limit (2026-07-21 ~18:15 EDT) — RESUME HERE

Human confirmed the manual download; real data is in and **Rolando has been RE-RUN on real data
(done + committed).** Session is pausing at the usage limit. **Next action on resume: re-run Diana
on the REAL SignverOD/StaVer data** (see the resume prompt at the bottom of `status_log.md`), then
Jordan → Damir → Hessam. Follow the sequential execution model. Verify each stage on disk before
starting the next.

Real data on disk (verified): `data/raw/invoices/batch_{1,2,3}/batch_{1,2,3}/batch{N}_{1,2,3}/*.jpg`
≈8,181 real invoice JPGs (synthetic leftovers removed) + per-batch annotation CSVs
(`File Name, Json Data{invoice,items,subtotal,payment_instructions}, OCRed Text` — REAL OCR +
structured field ground truth, a big upgrade for Damir); `data/raw/signatures/` = SignverOD;
`data/raw/stamps/` = StaVer. Real manifest = `data/processed/invoice_manifest.csv` (750-image
stratified sample, gitignored but persists on disk; also durably committed as the member-outputs
mirror on `feature/rolando-data-ingestion`).

## Current wave (updated 2026-07-22 — execution model CHANGED, see below)

**Execution model as of 2026-07-22: members run their OWN Colab (GPU) notebooks** (`colab/notebooks/`)
and publish to Google Drive; the human copies results into local `outputs/` for orchestrator
verification. The old "local sequential Sonnet agents" model is retired (local machine is CPU-only).

| # | Member | Colab notebook | Status | Results on local disk? | Verified? | Notes |
|---|---|---|---|---|---|---|
| 1 | Rolando (ingestion) | `01_..._colab.ipynb` | ✅ **DONE (real, annotation-aware)** | ✅ manifest | ✅ yes | 750-row manifest, **GT coverage 100%** (was 26.3%), split 525/120/105. His Colab notebook is OPTIONAL (manifest already built locally). |
| 2 | Diana (stamp/signature) | `02_..._colab.ipynb` | 🔄 **RUNNING on Colab** | ❌ not yet | ❌ | Human will copy `stamp_signature_predictions.csv` + metrics into `outputs/`. ⚠️ the file at that path now is the OLD SYNTHETIC one (2026-07-21) — must be overwritten. |
| 3 | Jordan (region/IoU) | `03_..._colab.ipynb` | 🔄 **RUNNING on Colab** | ❌ not yet | ❌ | Now uses the OCR Dataset (real 52,331 boxes), labels company/date/address/total/other_text; invoice-keyed rows via `source="invoice"`. |
| 4 | Damir (OCR/params/terms) | `04_..._colab.ipynb` | ✅ **DONE on Colab (human-reported)** | ❌ **NOT copied down yet** | ❌ **NOT verified** | Files absent from local `outputs/`, member mirrors, and the Drive upload folder as of this check. Human copies into `outputs/` for verification once #2 and #3 also finish. NB: his param/terms CSVs are RECEIPT-keyed — invoice verdict signals are derived at integration (see status_log + plan). |
| 5 | Hessam (integration/Streamlit) | — (local) | 🔶 **App PARTIALLY BUILT, NOT verified** | code in tree, uncommitted | ❌ | `src/verdict_engine.py` (9/9 tests pass) + results_store/policy_store/streamlit_helpers/app written but app NOT launched; report/demo/sample-invoices pending. Full design: `ai_cowork/plans/streamlit_app_verdict_engine_plan.md`. |

### Streamlit app build — detailed status (2026-07-22)
DONE + verified: `src/verdict_engine.py` (rule engine; **9/9 unit tests** in `tests/test_verdict_engine.py`).
DONE, imports clean, NOT run: `src/results_store.py`, `src/policy_store.py`, `src/streamlit_helpers.py`
(signal derivation), `app/streamlit_app.py` (3 views + sidebar policy builder),
`config/required_fields_config.json` (+ Work Order No.), `config/verdict_policies.json` (created on save).
NOT verified: app never launched. NOT done: per-invoice HTML report, `presentation/demo_script.md`
update, `app/sample_invoices/`, live-inference test (needs `best.pt` in `models/`).
NOT committed: all app-build files uncommitted on `main`.

## Report log deliverable (every member — feeds the report & slide deck)

In addition to their data/model outputs, each agent must fill in their report log under
`presentation/member_reports/<member>_report_log.md` (what they did, decisions, **challenges
faced**, metrics, handoff notes). Verify this is filled in — not still the stub — before marking a
job `complete`. Hessam's final stage assembles the group report + slides from these logs.

## Required outputs per job (verify these exist + match schema before marking complete)

- **Rolando:** `data/processed/invoice_manifest.csv`, `outputs/reports/data_quality_report.md`, `outputs/figures/sample_invoice_grid.png`, `outputs/figures/preprocessing_examples.png`
- **Diana:** `outputs/predictions/stamp_signature_predictions.csv`, `outputs/metrics/stamp_signature_metrics.json`, `outputs/figures/stamp_signature_detection_examples.png`, `models/stamp_detector/`, `models/signature_detector/`
- **Jordan:** `outputs/predictions/region_predictions.csv`, `outputs/metrics/region_iou_metrics.json`, `outputs/figures/region_detection_examples.png`, `models/region_detector/`
- **Damir:** `outputs/predictions/ocr_outputs.csv`, `outputs/predictions/parameter_presence_results.csv`, `outputs/predictions/terms_extraction_results.csv`, `outputs/metrics/ocr_parameter_metrics.json`
- **Hessam:** `outputs/final_json/sample_invoice_outputs/*.json`, `outputs/reports/final_pipeline_report.md`, validated `app/streamlit_app.py`, `presentation/demo_script.md`

(Full schemas in `../model_interface_contract.md`.)
