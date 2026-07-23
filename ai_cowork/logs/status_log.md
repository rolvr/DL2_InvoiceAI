# Status Log

Append-only, newest entries at the bottom. Each entry: timestamp, what happened, and the
immediate next action. On resume, read the last few entries, then verify against the
filesystem (see `../ORCHESTRATION.md`).

---

### 2026-07-21 ~15:50 EDT — Repository scaffolded
- Full repo scaffold created (folders, config, scripts, 14 `src/` modules, 6 notebooks, 5
  member READMEs, Streamlit app, presentation docs, agent prompts).
- Logic-heavy `src/` modules (iou, parameter_checker, terms_extraction, final_json_builder)
  functionally sanity-tested and passing.
- Git initialized on `main`; created `dev` + 5 `feature/*` branches, all at the root commit
  `Scaffold invoice-image-processing repository`.
- **Next:** deploy member agents in dependency order, starting with Rolando.

### 2026-07-21 16:00 EDT — Rolando (data ingestion) deployed
- Launched a background Sonnet 5 agent as Rolando on branch `feature/rolando-data-ingestion`.
- Brief: read agent prompt + interface contract, use `src/` modules, install only lightweight
  ingestion deps, attempt real Kaggle download and fall back to a clearly-labeled synthetic
  invoice sample if `kaggle.json` is missing, EXECUTE the notebook, produce all 4 contractual
  outputs + mirrors, verify with `validate_dataset_paths.py`, commit to its feature branch,
  don't touch other members' folders.
- Wave 2 (Diana + Jordan) is held until Rolando completes and its outputs are verified.
- **Next:** on Rolando completion notification → verify outputs → update job_log → deploy
  Diana and Jordan in parallel.

### 2026-07-21 16:02 EDT — Orchestration/resume tooling added
- Added `ai_cowork/ORCHESTRATION.md` (resume guide + deployment pipeline + re-deploy protocol),
  this `status_log.md`, and `ai_cowork/logs/job_log.md` (structured per-job status), so a new
  session can recover state and re-brief/re-deploy agents after an interruption.
- Key resume rule documented: background subagents do NOT survive a session; re-deploy fresh
  agents for any job not verifiably complete on disk.
- **Next:** unchanged — awaiting Rolando completion.

### 2026-07-21 16:05 EDT — Report-log deliverable added for all members
- Added `presentation/member_reports/` with `_TEMPLATE.md`, a README, and a per-member stub
  (rolando/diana/jordan/damir/hessam). Each agent must document what they did + challenges faced,
  as source material for the group report and slide deck.
- Wired the requirement into all five `ai_cowork/agents/*_agent_prompt.md` briefs and into
  `job_log.md` (report log must be filled in before a job is marked complete). Hessam's brief now
  also owns final report + deck assembly from these logs.
- Sent a mid-run message to the active Rolando agent to add its `rolando_report_log.md` as a
  required deliverable.
- **Next:** unchanged — awaiting Rolando completion, then verify (outputs + report log) and deploy
  Diana + Jordan.

### 2026-07-21 16:20 EDT — Rolando COMPLETE and verified; execution model set to sequential
- Rolando agent finished (commit `2f64e7c` on feature/rolando-data-ingestion). Independently
  verified: `validate_dataset_paths.py` Rolando rows OK; manifest 38 rows / correct schema / POSIX
  paths / splits train22-val8-test6-excluded2; both figures present; report log filled in.
- **Data is SYNTHETIC** — no kaggle.json anywhere. Rolando generated a labeled synthetic invoice
  set and (good catch) fixed a Windows-backslash path bug that would have broken Colab/Linux.
  Consequence for the team: Diana will find no real stamps/signatures, Jordan has no real region
  ground truth — both must use synthetic labeled fallbacks. All downstream metrics are
  pipeline-validity checks, not real-world performance.
- **Decision: run remaining agents SEQUENTIALLY** (not parallel). One shared working tree makes
  concurrent git unsafe, and worktree isolation would hide the gitignored synthetic data. Verified
  gitignored manifest/images persist across branch checkouts.
- **Git consolidation:** committed orchestrator infra + report-log system to `main` (227df3f) and
  merged into `dev` + all 5 feature branches, so report-log stubs/template are present on every
  branch and won't disappear on checkout. Confirmed 8 infra files on each branch (9 on rolando).
- **Next:** deploy Diana (sequential). On completion → verify → merge to dev consideration →
  deploy Jordan.

### 2026-07-21 16:22 EDT — Diana (stamp/signature) deployed
- Launched Sonnet 5 agent as Diana on feature/diana-stamp-signature. Brief accounts for synthetic
  regime: real SignverOD/StaVer unavailable → overlay synthetic stamp + signature marks onto the
  actual manifest invoice images (document_id-consistent) with recorded ground-truth boxes, train/
  demonstrate detection, compute per-class precision/recall/IoU via src/iou.py, keep labels exactly
  "stamp"/"signature", not every invoice gets a mark (tests true negatives). Commit scoped to its
  own files; fill diana_report_log.md.
- **Next:** await Diana completion → verify → deploy Jordan.

### 2026-07-21 17:00 EDT — Diana COMPLETE (synthetic) and verified
- Diana agent finished (commit `8da2511` on feature/diana-stamp-signature). Independently verified
  on disk: predictions CSV (43 rows, real YOLOv8n confidences, correct separate stamp/signature
  labels), metrics JSON (stamp P/R 1.0/1.0 IoU 0.96; signature P/R 0.91/1.0 IoU 0.87), detection
  figure (1.2MB), GT annotations CSV, real 6.2MB `best.pt` weights in both model dirs + READMEs,
  report log filled. Good work — high metrics reflect easy synthetic marks, documented as such.

### 2026-07-21 17:15 EDT — HUMAN manual data download detected; HOLD in effect
- User instructed (previous turn): they will manually download the real data sources and place them
  in data/raw; WAIT for the human to confirm completion before launching the next agents.
- Orchestrator disk survey confirms real data is now present: `data/raw/invoices/{batch_1,2,3}`
  ≈8,190 real invoice JPGs + 3 annotation CSVs (38 synthetic_invoice_* leftovers still at root);
  `data/raw/signatures/` = SignverOD (~2,765 imgs + train/test CSVs + labelmap + tfrecords);
  `data/raw/stamps/` = StaVer (1,227 PNG + 400 GT txt).
- **HOLDING.** Neither Diana's report nor this survey counts as the human's go-signal. No agent will
  be launched/re-run until the human explicitly confirms.
- Housekeeping done while idle: verified Diana, updated job_log + status_log on `main`. Left Diana's
  synthetic work committed on its branch (not merged to dev — will be superseded by a real-data run).
- **Planned once human confirms:** (1) optionally clean the 38 synthetic_invoice_* leftovers from
  data/raw/invoices root so they don't pollute the real manifest; (2) re-run Rolando on the real
  invoice batches → new real manifest; (3) re-run Diana on real SignverOD/StaVer; (4) then Jordan →
  Damir → Hessam on real data. Confirm approach with human before executing.
- **Next:** await human "download complete / go" message.

### 2026-07-21 17:41 EDT — Human confirmed download; Rolando RE-RUN on real data deployed
- Human gave go. Orchestrator committed housekeeping, removed the 38 `synthetic_invoice_*`
  leftovers from `data/raw/invoices/`, then deployed a fresh Rolando agent to redo ingestion on
  the real invoice batches (750-image stratified cap, unique batch-prefixed doc_ids, document the
  annotation-CSV schema).

### 2026-07-21 18:10 EDT — Rolando real re-run COMPLETE + verified (committed 869c68b)
- The Rolando agent launched `nbconvert` in the background and its turn ended before finishing;
  its transcript was later NOT resumable. Orchestrator waited for the notebook process to exit
  (background waiter), then independently verified: real manifest 750 rows (0 synthetic, unique
  doc_ids like `batch1-0011`, POSIX paths, split 524/120/106, real dims 1654×2339), figures + QA
  report regenerated. Orchestrator then finished the leftover steps: appended the real-data
  re-run section to `rolando_report_log.md` (incl. annotation-CSV schema), ran validate (Rolando
  rows OK), removed a stray root `yolov8n.pt` (+ gitignored `*.pt`), and committed scoped (869c68b).
- **Annotation CSV = real ground truth:** `data/raw/invoices/batch_N/batch_N/batchN_*.csv` columns
  `File Name, Json Data{invoice,items,subtotal,payment_instructions}, OCRed Text`. Damir should use
  these (real OCR + structured extraction targets). Jordan: no pixel bboxes here → still needs a
  heuristic/synthetic region-box approach on the real images.

### 2026-07-21 18:15 EDT — PAUSING for session usage limit
- Repo left resumable: on branch `main`, clean tree, real manifest on disk + durable in Rolando's
  branch member-outputs mirror. Logs updated. Diana's synthetic run parked on its branch.
- **NEXT ACTION ON RESUME → re-run Diana on REAL data.** Use the resume prompt below.

### 2026-07-22 — MAJOR PIVOT: local agents → member-run Colab; + Streamlit app build
Big changes this session (the 07-21 resume prompt below is now SUPERSEDED — do not follow it):

**1. Abandoned local CPU agent runs; members run their own Colab (GPU) notebooks.** Local machine
is CPU-only; Diana's local re-run was aborted mid-training. Built a `colab/` delivery surface:
`colab/notebooks/00_preflight + 01..05_<member>_colab.ipynb`, `colab/colab_bootstrap.py`
(mount/paths/deps/verify/publish, tolerant path resolvers), `src/compute_profile.py`
(local_cpu vs colab_gpu), `colab/bundle/` generators. Notebooks read datasets from Google Drive
(no Kaggle token shared). Committed: a67fa99, 6868571, b0334bf, 94a2c1d, e495aa6.

**2. Dataset discoveries (see `ai_cowork/plans/` + git log):**
- `data/raw/invoices/OCR Dataset of Multi-type Documents/` = SROIE-style receipts: 973 imgs,
  **100% annotation, 52,331 real polygon boxes + entities**. Jordan + Damir now use THIS (real
  boxes) instead of the heuristic plan.
- Batch annotation CSVs exist ONLY for batch_1 (1,413 imgs). Rolando resampled **annotation-aware**
  → manifest GT coverage 26.3% → **100%** (750 rows, split 525/120/105). `batch_3/` duplicates
  batches 1-2 (true unique = 5,201, not 8,181) — excluded to avoid leakage.
- Drive bundle staged at `C:\Users\hessa\DL2_InvoiceAI_upload` (~147 MB) + datasets copied in by
  the human; preflight passed 26/0/1 (1 warning = stale extra images, harmless).

**3. Streamlit app final phase — DESIGNED + PARTIALLY BUILT (NOT VERIFIED).**
Full design in `ai_cowork/plans/streamlit_app_verdict_engine_plan.md`. Core reframing: the
ready/not-ready verdict is a **user-configurable rule engine** (visual mark / reference no. /
invoice-date range / payment-terms days; per-rule toggle; all enabled AND-ed; **fail-closed** on
missing signals). Scope: single invoice + whole batch. Execution: hybrid (gallery reads
pre-computed; upload runs live models if weights in `models/`).
- Built + tested: `src/verdict_engine.py` (**9/9 unit tests pass**, `tests/test_verdict_engine.py`).
- Built, imports clean, NOT run: `src/results_store.py`, `src/policy_store.py`,
  `src/streamlit_helpers.py` (signal derivation), `app/streamlit_app.py` (3-view app),
  `config/required_fields_config.json` (+ Work Order No.).
- **NOT verified: the app has never been launched.** **NOT done:** per-invoice HTML report,
  `presentation/demo_script.md` update, `app/sample_invoices/`, live-inference test (no weights yet).
- **NOT committed:** all app-build files are uncommitted in the working tree on `main`.
- Key correctness note baked into the app: Damir's `parameter_presence_results.csv` /
  `terms_extraction_results.csv` are keyed to the OCR-DATASET RECEIPTS, not the 750 invoices, so
  reference/date/terms signals are DERIVED at integration from invoice OCR text + batch_1
  annotation `OCRed Text` (`src/results_store.invoice_ocr_text` + `src/streamlit_helpers`).

**4. Member notebook status (human-reported, 2026-07-22):**
- **Damir (04): DONE on Colab, NOT verified.** His result files are NOT yet on local disk (checked
  `outputs/`, member mirrors, and the Drive upload folder — absent). Human will copy them into
  `outputs/` for verification once the other two finish.
- **Diana (02) + Jordan (03): still running on Colab.** Human will copy all three members' results
  into `outputs/predictions|metrics/` together, then orchestrator verifies.
- ⚠️ `outputs/predictions/stamp_signature_predictions.csv` on disk right now is the OLD SYNTHETIC
  file (2026-07-21 17:19) — it MUST be overwritten by Diana's real Colab output before trusting it.

- **NEXT ACTIONS:** (a) when Diana+Jordan finish, human copies all outputs into `outputs/` →
  orchestrator verifies each against `model_interface_contract.md`; (b) launch the Streamlit app
  headless and fix runtime issues; (c) finish report/demo-script/sample-invoices; (d) copy trained
  `best.pt` weights from Drive into `models/` to enable live vision on uploads; (e) commit the app
  build.

---

## ▶️ RESUME PROMPT (paste to the next session after reset)

> Resume the invoice-image-processing orchestration (you are Hessam/Opus, the orchestrator).
> Read `ai_cowork/ORCHESTRATION.md`, `ai_cowork/logs/job_log.md`, and this status_log first, then
> VERIFY state on disk: `git branch --show-current` (expect `main`), `git log --oneline --all -12`,
> and `python scripts/validate_dataset_paths.py`. Confirm the real 750-row manifest
> (`data/processed/invoice_manifest.csv`, 0 synthetic refs) is present.
>
> Rolando is DONE on real data (commit 869c68b). Diana's only completed run is SYNTHETIC (commit
> 8da2511) and must be REDONE on real data. **Deploy the next agent: Diana, on the REAL datasets,
> SEQUENTIALLY (one agent at a time — do NOT parallelize; no worktree isolation).** Brief her from
> `ai_cowork/agents/diana_agent_prompt.md` PLUS these real-data specifics:
>   - Real SignverOD is in `data/raw/signatures/` (images/, train.csv, test.csv, categories.csv,
>     image_ids.csv, labelmap.txt, tfrecords/) — parse its real signature bounding-box annotations.
>   - Real StaVer stamp data is in `data/raw/stamps/StaVer/` (scans + ground-truth maps).
>   - Detect real `stamp` vs real `signature` as two separate labels; evaluate per-class
>     precision/recall/IoU via `src/iou.py`. Keep predictions keyed so Hessam can integrate.
>   - She may reuse her committed YOLOv8n pipeline/code from branch `feature/diana-stamp-signature`
>     (commit 8da2511) but must retrain/evaluate on the REAL data, not the synthetic overlays.
>   - Work on `feature/diana-stamp-signature`, scoped commits only (no `git add -A`), fill the
>     real-data section of `presentation/member_reports/diana_report_log.md`.
>   - Tell her to EXECUTE her notebook and to run `nbconvert` FOREGROUND (blocking) or otherwise
>     not return until it's finished — the previous agents returned before their background
>     notebook finished, forcing manual orchestrator finalize. She must complete validate + commit
>     herself.
> After Diana verifies on disk, continue sequentially: Jordan (region detection on real manifest;
> region bboxes not in annotation CSVs → heuristic/synthetic region boxes), then Damir (OCR +
> params + terms — now has REAL OCR/structured ground truth in the batch annotation CSVs described
> above), then Hessam (integration → final JSON → Streamlit → report/deck). Update job_log +
> status_log after each stage. Orchestrator home branch = `main`.
>
> Known gotcha: subagents that background their notebook run may return before it finishes — verify
> outputs on disk (don't trust the completion message alone), and their transcripts may be
> unresumable, so be ready to finish finalize/commit yourself as was done for Rolando.
