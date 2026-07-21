# AI Usage Log — ai_cowork

Detailed log of AI-assisted work on this project. See `../../ai_usage_log.md` for the
top-level pointer required by course policy.

| Date | Actor | Scope | Notes |
|---|---|---|---|
| 2026-07-21 | Claude (master planner / repository architect) | Scaffolded the entire repository: 40+ files including folder structure, `.gitignore`, `requirements.txt`, `README.md`, `project_plan.md`, `model_interface_contract.md`, `dataset_sources.md`, `runbook.md`, `config/*.json`, `scripts/*.py` (4 dataset/annotation scripts), `src/*.py` (14 utility modules — data/OCR/parameter/terms/IoU/visualization logic fully implemented; model-inference interfaces left as documented placeholders for Diana/Jordan to fill), 6 Jupyter notebooks (project overview + one per member, each with Colab setup, imports, per-task scaffolding, and export cells), 5 member `README.md` files, `app/streamlit_app.py` (fully wired demo UI), presentation outline + demo script, and the 5 per-member Sonnet 5 agent prompts in `ai_cowork/agents/`. | No model training, no dataset downloads, and no data analysis were performed — this was structural/scaffolding work only. Implementation choices requiring judgment (SSD-vs-YOLO fallback, OCR engine default, manual annotation strategy, dataset sampling) are documented in `../../project_plan.md` §4. |

## How to log your own AI-assisted work

Append a row per session: date, which member/agent, what was AI-generated vs. human-reviewed,
and any notable judgment calls the AI made. Keep entries factual and specific enough that a
grader could understand what was and wasn't AI-authored.
