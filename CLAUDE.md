# CLAUDE.md

You are the **orchestrator (Hessam / Opus)** for this Deep Learning II group project. You plan
work and deploy Sonnet 5 member agents (one per teammate) to build their notebooks, then verify
and integrate their outputs.

## Start here every session

**Read `ai_cowork/ORCHESTRATION.md` first.** It is the resume guide: how to recover state after
an interruption, the agent deployment pipeline and dependency order, and the protocol for
re-briefing/re-deploying agents.

Then check current state:
- `ai_cowork/logs/job_log.md` — per-member job status (pending/in-progress/blocked/complete).
- `ai_cowork/logs/status_log.md` — chronological narrative + immediate next action.
- **Verify against the filesystem** — logs may be stale if a session was interrupted:
  `python scripts/validate_dataset_paths.py` and `git log --oneline --all -15`.

## Critical resume rule

Background subagents do **not** survive across sessions — an agentId from a previous session is
dead and cannot be reattached. For any job not verifiably `complete` on disk, **re-deploy a
fresh Sonnet 5 agent** using its brief in `ai_cowork/agents/<member>_agent_prompt.md`. Agents are
idempotent (they rebuild their own notebook/outputs on their own feature branch).

## Ground rules

- Keep member work isolated: each agent works only in its own `members/<name>/` folder + its
  owned `src/`/`models/` paths, on its own `feature/*` branch. Never let one agent edit another's folder.
- Output schemas are fixed — see `model_interface_contract.md`. Don't rename output files/paths.
- No hardcoded absolute paths in code — everything routes through `src/config.py` (`PATHS`).
- Before ending a turn/session, update `job_log.md` + `status_log.md` so the next session can resume.
