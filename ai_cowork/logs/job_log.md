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
| 1 | Rolando (data ingestion) | feature/rolando-data-ingestion | in-progress | 2026-07-21 16:00 EDT | not yet | Background Sonnet 5 agent. Must complete + verify before wave 2. May use synthetic data fallback if no kaggle.json. |
| 2 | Diana (stamp/signature) | feature/diana-stamp-signature | pending (blocked on #1) | — | — | Deploy after Rolando verified. Can run parallel with #3. |
| 3 | Jordan (region/IoU) | feature/jordan-region-iou | pending (blocked on #1) | — | — | Deploy after Rolando verified. Can run parallel with #2. Likely needs manual annotation subset (see runbook.md). |
| 4 | Damir (OCR/terms) | feature/damir-ocr-terms | pending (blocked on #3) | — | — | Needs Jordan's region_predictions.csv (+ Diana's stamp/sig preds). |
| 5 | Hessam (integration/Streamlit) | feature/hessam-integration-streamlit | pending (blocked on #1-4) | — | — | Runs last; integrates all outputs into final JSON + demo. |

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
