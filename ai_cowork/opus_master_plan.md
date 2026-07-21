# Opus Master Plan

This file records the scaffolding decisions made when the repository was set up by Claude
acting as master planner/repository architect, so the team understands what was generated,
what's a placeholder, and what still needs real work.

## What was generated (2026-07-21)

- Full folder structure per the spec (`config/`, `scripts/`, `data/`, `members/*`,
  `notebooks/`, `src/`, `models/*`, `outputs/*`, `app/`, `presentation/`, `ai_cowork/`).
- `requirements.txt`, `.gitignore`, `README.md`, `project_plan.md`,
  `model_interface_contract.md`, `dataset_sources.md`, `runbook.md`, `ai_usage_log.md`.
- `config/required_fields_config.json`, `config/label_schema.json` — exact content per spec
  (plus an added empty `custom_fields` list in the former, to support user-added fields
  without editing the default list).
- `scripts/download_datasets.py`, `scripts/prepare_folders.py`,
  `scripts/validate_dataset_paths.py`, `scripts/convert_annotations.py` — all functional,
  not placeholders (though obviously untested against the live Kaggle API in this session).
- `src/*.py` — 14 modules. Data/utility modules (`config`, `data_loader`,
  `image_preprocessing`, `annotation_utils`, `iou`, `parameter_checker`,
  `terms_extraction`, `final_json_builder`, `visualization`) are fully implemented and
  ready to use. Model-dependent modules (`layout_detection.py`,
  `stamp_signature_detection.py`) are thin interface placeholders — `NotImplementedError`
  stubs with the exact input/output contract each member's trained model must satisfy.
  `ocr.py` is fully implemented (EasyOCR + PyTesseract backends) since OCR doesn't require
  project-specific training. `streamlit_helpers.py` wires all of the above together with
  TODOs marking exactly where Jordan's and Diana's models plug in.
- Six notebooks (`00_project_overview` + the 5 member notebooks), each with: title/role/
  objective/inputs/outputs markdown header, Colab setup cell, dataset path setup cell,
  imports cell, one section per task in that member's spec (with runnable scaffolding code
  and `# TODO` markers exactly where model training/inference needs to be filled in), and a
  final export cell that writes every contractual output file to both the shared `outputs/`
  location and that member's own `members/<name>/outputs/` folder. Mirrored into `notebooks/`.
- Five member `README.md` files (role, notebook, inputs, outputs, how Hessam integrates,
  ground rules).
- `app/streamlit_app.py` — fully wired UI (upload, sidebar controls, all result sections,
  JSON download) that runs end-to-end today; it will show "not detected" for regions/stamp/
  signature until `src/layout_detection.py` and `src/stamp_signature_detection.py` are
  filled in with real trained models.
- `presentation/slides_outline.md`, `presentation/demo_script.md`.
- This file plus the five agent prompts in `ai_cowork/agents/`.

## Implementation choices made without asking (documented per instructions)

See `../project_plan.md` §4 for the full list. Summary: SSD is the documented/required
concept, YOLOv8 (ultralytics) is the allowed implementation fallback if SSD training doesn't
fit the timeline; EasyOCR is the default OCR engine; a 50-150 image manual annotation subset
is assumed necessary for the 5 region labels no public dataset covers; dataset scale defaults
to a sample subset rather than full-dataset training.

## What is NOT done yet (real modeling/data work, by design)

- No datasets have actually been downloaded in this session (would require live Kaggle
  credentials).
- No models have been trained. `models/*_detector/` folders are empty except for READMEs.
- No manual annotation has been performed — `data/annotations/*.csv` are header-only
  templates.
- The five member notebooks are not lint on live data; they were written to be structurally
  correct (valid JSON, valid nbformat, importable code) but the TODO-marked cells need each
  member's actual model/data work before they'll produce real outputs.

## Next steps for the team

1. Each member configures Kaggle credentials and runs `scripts/download_datasets.py` for
   their relevant dataset(s).
2. Rolando runs notebook 1 first — everyone else depends on `invoice_manifest.csv`.
3. Diana and Jordan can work in parallel once Rolando's manifest exists; both will likely
   need the manual annotation pass (see `../runbook.md`) before the region/stamp/signature
   labels that aren't in the public datasets can be trained against real ground truth.
4. Damir starts once Jordan (and ideally Diana) have at least placeholder predictions to
   consume.
5. Hessam integrates continuously, not just at the end — running
   `scripts/validate_dataset_paths.py` regularly to catch missing outputs early.
