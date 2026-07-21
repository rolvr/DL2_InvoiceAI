# Job Log — Member Agent Deployment Status

Structured resume state for the orchestrator. **On a new session, read this, then VERIFY
against the filesystem** (`python scripts/validate_dataset_paths.py` + `git log --all`) because
a job's real state may differ from what's recorded here if a previous session was interrupted.

Status values: `pending` · `in-progress` · `blocked` · `needs-verify` · `complete` · `failed`

> Note: subagent IDs are session-scoped and are recorded only for the CURRENT session's
> notifications. After a session break they are dead — re-deploy a fresh agent for any job not
> verified `complete` on disk. Do not treat a recorded agentId as reattachable from a new session.

## Current wave

| # | Member | Branch | Status | Deployed (session) | Outputs verified? | Notes |
|---|---|---|---|---|---|---|
| 1 | Rolando (data ingestion) | feature/rolando-data-ingestion | **complete** | 2026-07-21 16:00 EDT | ✅ yes (16:20) | Committed 2f64e7c. 38-row manifest (36 clean/2 corrupt; train22/val8/test6), POSIX paths, both figures, report log filled. **SYNTHETIC data** (no kaggle.json). Caught+fixed a backslash-path portability bug. |
| 2 | Diana (stamp/signature) | feature/diana-stamp-signature | in-progress | 2026-07-21 16:22 EDT | not yet | Deployed (sequential). SignverOD/StaVer unavailable (no creds) → synthetic stamp/signature overlay on manifest images. |
| 3 | Jordan (region/IoU) | feature/jordan-region-iou | pending (blocked on #2 finishing — sequential) | — | — | Deploy after Diana done. Needs region ground-truth (none public) → synthetic labeled set + inference on manifest images. |
| 4 | Damir (OCR/terms) | feature/damir-ocr-terms | pending (blocked on #3) | — | — | Needs Jordan's region_predictions.csv (+ Diana's stamp/sig preds). |
| 5 | Hessam (integration/Streamlit) | feature/hessam-integration-streamlit | pending (blocked on #1-4) | — | — | Runs last; integrates all outputs into final JSON + demo + report/deck assembly. |

**Execution model (important):** agents run **SEQUENTIALLY**, one at a time, in the single shared
working tree — NOT in parallel. Concurrent agents would corrupt git state (shared index/checkouts),
and git-worktree isolation would hide the gitignored synthetic data (manifest + images) they depend
on. Gitignored data persists on disk across branch checkouts, so a sequential agent on any branch
sees it. Orchestrator home branch = `main`; the infra + report-log stubs were committed to `main`
and merged into `dev` + all feature branches so checkouts don't remove them. Each agent commits
ONLY its own files to its feature branch (scoped, no `git add -A`); orchestrator merges each
feature branch → `dev` at integration time.

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
