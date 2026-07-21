# Orchestration & Resume Guide

**Read this FIRST when a new Claude Code session starts on this project.** It is the entry
point for the orchestrator (Hessam / Opus) to recover state after an interruption, session
limit, or crash, and to re-brief and re-deploy member agents.

The orchestrator role: act as Hessam — plan the work, deploy Sonnet 5 member agents (one per
teammate) to build their notebooks, verify their outputs against `../model_interface_contract.md`,
and integrate. Member agents are launched with the Agent tool (`model: sonnet`) using the
briefs in `agents/*.md`.

---

## How to resume after a session break (do this in order)

1. **Read the two logs** to see the intended vs. actual state:
   - `logs/job_log.md` — the structured status of each member job (pending / in-progress /
     blocked / complete), its branch, and which outputs are verified.
   - `logs/status_log.md` — the chronological narrative of what has happened.

2. **Trust the filesystem + git over the logs.** A job marked "in-progress" may have finished,
   partially finished, or died when the previous session ended. Verify actual state:
   - Run `python scripts/validate_dataset_paths.py` — it reports exactly which member outputs
     exist on disk (this is the ground truth for "did this stage actually complete").
   - Run `git branch -a` and `git log --oneline --all -15` to see what each feature branch
     has committed.
   - Spot-check the actual output files named in `../model_interface_contract.md` (open the
     CSVs/JSON, confirm schema + non-empty).

3. **Reconcile the logs.** Update `job_log.md` and append a `status_log.md` entry describing
   what you found on resume (e.g. "Rolando job was marked in-progress; on inspection
   invoice_manifest.csv exists with 320 rows and validate passes → marking complete").

4. **IMPORTANT — background agents do NOT survive a session.** A subagent launched with the
   Agent tool in a previous session cannot be reattached from a new session; its agentId is
   dead. For any job that is not verifiably complete on disk, **re-deploy a fresh agent** using
   that member's brief in `agents/<member>_agent_prompt.md`. Do not wait on a previous
   session's agent — it is gone. Re-deploying is safe because agents are idempotent: they
   rebuild their own notebook/outputs and commit to their own feature branch.

5. **Deploy in dependency order** (see below), verify each stage's outputs before starting the
   stage that depends on it, and keep the two logs updated as you go.

---

## Deployment pipeline & dependency order

```
[1] Rolando  (feature/rolando-data-ingestion)      data/processed/invoice_manifest.csv + preprocessing
        │  everyone below depends on the manifest
        ├──────────────┬───────────────────────────────
        ▼              ▼
[2] Diana        [3] Jordan   (parallel — both only need Rolando's manifest)
    stamp/sig        region/IoU
        │              │
        └──────┬───────┘
               ▼
[4] Damir   (feature/damir-ocr-terms)   needs Jordan's region_predictions + Diana's stamp/sig preds
               ▼
[5] Hessam  (feature/hessam-integration-streamlit)   needs ALL of the above; runs last
```

- **Rolando must complete and be verified before anything else starts.**
- Diana and Jordan can be deployed in parallel once Rolando is verified.
- Damir starts once Jordan's `region_predictions.csv` exists (Diana's helps but a stub works).
- Hessam runs last, after all four upstream stages are verified.

## How to (re-)deploy a member agent

Launch the Agent tool with `model: sonnet` and a prompt that tells the agent to read and follow
`ai_cowork/agents/<member>_agent_prompt.md`. The standard brief pattern (see how Rolando was
deployed, recorded in `status_log.md`):
- Give the absolute repo path: `C:\Users\hessa\OneDrive\Dropbox Backup\WorkSpace\GBC_AIML_Dev_2026\Deep Learning II\invoice-image-processing`
- Tell it to read its agent prompt + `model_interface_contract.md` + the relevant `src/` modules first.
- Tell it to actually EXECUTE its notebook and produce real output files (not just write code).
- Tell it to install only the dependencies its stage needs (keep it fast).
- Tell it to work on its own `feature/*` branch, commit there, and NOT touch other members' folders.
- Tell it to report back: what it produced, verification result, blockers, and anything downstream agents need.
- Have it run `python scripts/validate_dataset_paths.py` and confirm its rows show OK before declaring done.

After an agent completes: verify its outputs yourself, update `job_log.md` + `status_log.md`,
then deploy the next stage.

## Key facts

- Repo path: `C:\Users\hessa\OneDrive\Dropbox Backup\WorkSpace\GBC_AIML_Dev_2026\Deep Learning II\invoice-image-processing`
- Branches: `main`, `dev`, and `feature/{rolando-data-ingestion, diana-stamp-signature, jordan-region-iou, damir-ocr-terms, hessam-integration-streamlit}`. Members work on their feature branch → PR into `dev` → Hessam merges `dev` → `main`.
- Output contract (what each agent must produce): `../model_interface_contract.md`.
- Member briefs: `agents/*.md`. Per-member run details: `../members/*/README.md`.
- Data risk: if Kaggle `kaggle.json` credentials are absent, Rolando falls back to synthetic
  placeholder invoices (documented in its data quality report). Downstream results are only as
  real as the data — swap in the real Kaggle dataset when credentials are available and re-run.

## When you (the resuming orchestrator) finish a wave

Always leave the repo in a resumable state before ending a turn/session:
1. Update `logs/job_log.md` status for every job you touched.
2. Append a `logs/status_log.md` entry with timestamp, what happened, and the immediate next action.
3. If safe (no member agent mid-write), commit the orchestration files so they persist.
