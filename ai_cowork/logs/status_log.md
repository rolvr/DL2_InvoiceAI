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
