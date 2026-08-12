# Invoice AI — FastAPI Service (run & deploy notes)

The FastAPI service wraps the invoice obligation-readiness pipeline and serves it over HTTP.
It reuses the repo's `src/` modules and the same trained detectors + EasyOCR the Streamlit demo
uses. This file is the quick reference for **running and containerizing** it (e.g. for the
Dockerfile teammate).

## Run locally

```bash
pip install -r requirements.txt          # the pipeline (numpy, opencv, ultralytics, easyocr, …)
pip install -r requirements-api.txt      # the API + test clients

uvicorn app.api:app --host 0.0.0.0 --port 8000
```

Interactive docs (Swagger UI): http://localhost:8000/docs

## Facts a Dockerfile needs

| Thing | Value |
|---|---|
| Python | 3.12 |
| ASGI entrypoint | `app.api:app` |
| Start command | `uvicorn app.api:app --host 0.0.0.0 --port 8000` |
| Exposed port | `8000` |
| Dependencies | `requirements.txt` + `requirements-api.txt` |
| Healthcheck | `GET /health` → `200` with `{"status":"ok", ...}` |
| Working dir | repo root (so `app/` and `src/` are both importable) |
| GPU | none — CPU-only |
| Model weights | `models/{region,stamp,signature}_detector/best.pt` — gitignored, mounted/copied at deploy time (see below) |

System packages: OpenCV needs `libgl1` and `libglib2.0-0` on slim Debian/Ubuntu base images.

## Endpoints

| Method & path | Purpose |
|---|---|
| `GET /` | Service metadata. |
| `GET /health` | Liveness + which detectors have weights on disk. |
| `GET /policies` | Preset readiness policies + configured required fields. |
| `POST /predict` | Upload an invoice image (multipart field `file`) → readiness JSON. Query params: `confidence` (0–1, default 0.25), `run_ocr` (bool, default true), `document_id` (optional). |

`POST /predict` returns: `detections`, `ocr`, `signals`, `completeness` (0–100 score + tier),
`verdicts` (Default / Strict / Lenient), and `meta`.

## Model weights & degraded mode

The trained `best.pt` weights are **not** in git (they're large binaries, gitignored). The service
starts and every endpoint responds **without** them — detections come back empty and verdicts
report `"unknown → treated as fail"` (fail-closed). For a real deployment, make the weights
available at `models/*/best.pt` — copy them into the image at build time, or (better) mount them
as a volume / pull from a release or model registry at container start, so the image stays small.
`GET /health` reports `{"region": true/false, ...}` so you can confirm they loaded.

## Test it

```bash
pytest -q                                 # automated tests
bash clients/curl_examples.sh invoice.png # curl
python clients/python_client.py health    # Python client
# Postman: import clients/InvoiceAI.postman_collection.json
```
