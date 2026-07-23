# app/

The final Streamlit demo (`streamlit_app.py`), owned by Hessam.

## Run it

```bash
pip install -r ../requirements.txt   # from repo root: pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## What it does

Three views, navigable from the sidebar (which also hosts the user-configurable verdict
policy builder — visual mark / reference number / date range / payment-terms rules):

- **Live Demo** — pick a sample from `sample_invoices/` or upload your own. Runs Jordan's
  region detector and Diana's stamp/signature detector live (real trained YOLO weights from
  `models/`, CPU), then EasyOCR (CPU) to extract text so the reference/date/payment-terms
  rules have real signal too, not just the visual one. Shows the annotated image, the verdict
  + per-rule breakdown, and download buttons for a signals JSON and a self-contained HTML report.
- **Batch Gallery** — the current policy applied across all 750 invoices, with ready-count /
  pass-rate metrics, a pass/fail filter, a drilldown per invoice, and a passing-set CSV export.
  Per-invoice signals are cached (`st.cache_data`) so toggling a policy rule re-renders in well
  under a second.
- **Model Report** — the real held-out metrics (Diana's stamp/signature P/R/IoU, Jordan's
  per-class region IoU, Damir's OCR CER/WER) plus the obligation-readiness-by-policy summary.

## Status note

Region and stamp/signature detection now use real trained weights (`models/region_detector`,
`models/stamp_detector` — the same file also holds the signature class — loaded via
`ultralytics.YOLO`) called directly from `streamlit_app.py`'s `run_live()`, not through the
still-placeholder `src/layout_detection.py` / `src/stamp_signature_detection.py` wrappers
(those remain Jordan's/Diana's to fill in; the app doesn't depend on them). CPU-only — no GPU
required anywhere in the app.

## sample_invoices/

A few representative invoice images for quick manual demo/testing without needing the full
dataset downloaded — pickable directly from the Live Demo view's sample selector (no file
dialog needed). See `sample_invoices/README.md` for what each one demonstrates.
