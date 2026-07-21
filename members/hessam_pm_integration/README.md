# Hessam — Project Manager, Solution Architect, Integration Lead, Streamlit App Lead

**Notebook:** `05_hessam_integration_streamlit_demo.ipynb`
**Branch:** `feature/hessam-integration-streamlit`

## Role

Own the overall architecture, integrate every member's outputs into a single structured
JSON record per invoice, build the Streamlit demo, and prepare the final report and
presentation materials.

## What this notebook does

1. Validates all member outputs exist (`scripts/validate_dataset_paths.py`).
2. Loads Rolando's manifest, Diana's stamp/signature predictions, Jordan's region
   predictions + IoU metrics, and Damir's OCR/parameter/terms outputs.
3. Builds the final invoice JSON per `document_id` (schema in
   `../../model_interface_contract.md`), including the `pistacio_readiness` verdict.
4. Verifies/refines `app/streamlit_app.py`.
5. Writes `outputs/reports/final_pipeline_report.md`.
6. Maintains `presentation/demo_script.md` and `presentation/slides_outline.md`.

## Input files

All member outputs — see the table in `../../model_interface_contract.md` §5.

## Output files

- `outputs/final_json/sample_invoice_outputs/*.json`
- `outputs/reports/final_pipeline_report.md`
- `app/streamlit_app.py`
- `presentation/demo_script.md`
- Mirrored report copy in this folder's `outputs/`.

## Integration checklist (run before merging `dev` into `main`)

- [ ] `scripts/validate_dataset_paths.py` reports no missing member outputs.
- [ ] Final JSON produced for every `document_id` in the manifest, matches the schema exactly.
- [ ] `streamlit run app/streamlit_app.py` runs with no errors and shows real detections
      (not just the "not detected" placeholder state) once Jordan's/Diana's models are wired in.
- [ ] `final_pipeline_report.md` reflects current metrics.
- [ ] Presentation materials reference actual results, not placeholders.

## Run in Colab

Open from GitHub in Colab, run top-to-bottom. Should be run last, after all four other
member notebooks.

## Ground rules

- Don't rework another member's modeling choices without discussing it with them first —
  this notebook integrates, it doesn't replace their work.
- Keep the JSON schema exactly as specified in `model_interface_contract.md` — the
  Streamlit app and grading rubric both depend on it being stable.
