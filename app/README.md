# app/

The final Streamlit demo (`streamlit_app.py`), owned by Hessam.

## Run it

```bash
pip install -r ../requirements.txt   # from repo root: pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## What it does

Upload an invoice image and it runs the full pipeline: preprocessing → region detection
(Jordan's model) → stamp/signature detection (Diana's model) → OCR on detected regions
(Damir) → required-parameter + terms/payment extraction (Damir) → final Pistac.io-readiness
JSON, downloadable from the UI.

## Status note

Region and stamp/signature detection are wired through `src/layout_detection.py` and
`src/stamp_signature_detection.py`, which are placeholders until Jordan's and Diana's trained
models are plugged in (`load_region_detector`/`predict_regions` and
`load_stamp_detector`/`load_signature_detector`/`predict_stamp_signature`). Until then the app
runs end-to-end but reports "not detected" for those stages — OCR, parameter checking, and
JSON export are already fully functional.

## sample_invoices/

Drop a few representative invoice images here for quick manual demo/testing without needing
the full dataset downloaded.
