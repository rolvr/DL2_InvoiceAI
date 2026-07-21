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

## Current wave

| # | Member | Branch | Status | Deployed (session) | Outputs verified? | Notes |
|---|---|---|---|---|---|---|
| 1 | Rolando (data ingestion) | feature/rolando-data-ingestion | ✅ **COMPLETE (REAL data)** | re-run 2026-07-21 17:41 EDT | ✅ yes (18:10) | **Real re-run committed 869c68b.** 750-img stratified manifest (unique batch-prefixed doc_ids e.g. `batch1-0011`, POSIX paths, 0 synthetic, split 524/120/106), real figures + QA report, report-log re-run section added (annotation-CSV schema documented). Note: agent returned before nbconvert finished; orchestrator verified outputs + did the finalize/commit (agent transcript not resumable). Earlier synthetic run = 2f64e7c (superseded). |
| 2 | Diana (stamp/signature) | feature/diana-stamp-signature | ⚠️ complete on SYNTHETIC — **NEEDS REAL RE-RUN (next)** | 2026-07-21 16:22 EDT | prior run ✅ | Synthetic run committed 8da2511 (YOLOv8n, metrics stamp IoU 0.96 / sig IoU 0.87). **RE-RUN on real SignverOD (`data/raw/signatures/`) + StaVer (`data/raw/stamps/`) is the NEXT deploy.** See resume prompt in status_log.md. |
| 3 | Jordan (region/IoU) | feature/jordan-region-iou | pending (after Diana real re-run — sequential) | — | — | Reads the 750-row REAL manifest. Region bboxes are NOT in the annotation CSVs (those are field-level JSON), so still needs a heuristic/synthetic region-box approach. |
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
