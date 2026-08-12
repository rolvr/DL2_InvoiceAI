"""
api.py — FastAPI service that wraps the Invoice Obligation-Readiness pipeline.

Owner: (MLOps / productionization task). Run from the repo root with:

    uvicorn app.api:app --reload --host 0.0.0.0 --port 8000

then open http://localhost:8000/docs for interactive Swagger UI.

WHY THIS EXISTS
---------------
The team's pipeline already lives behind clean, importable ``src/`` modules (verdict_engine,
completeness, streamlit_helpers, config) and the Streamlit demo shows how to run the trained
YOLO detectors + EasyOCR on a single uploaded image. This service exposes that exact same
pipeline over HTTP so it can be called from anything — curl, Postman, a Python client, a
front-end, or another microservice — instead of only from the Streamlit UI.

It reuses the pipeline modules verbatim (no logic is re-implemented here):
  * app/inference.py       -> run_detectors() / run_ocr()  (mirrors streamlit_app.run_live*)
  * app/pipeline.py        -> predict_from_bytes()  (the framework-free core)
  * src/streamlit_helpers  -> signals_from_record()
  * src/completeness       -> score()
  * src/verdict_engine     -> evaluate(), preset_policies()
  * src/config             -> PATHS, load_required_fields()

ENDPOINTS
---------
  GET  /            service metadata
  GET  /health      liveness + which detectors have weights on disk
  GET  /policies    the preset readiness policies + the configured required reference fields
  POST /predict     upload an invoice image -> full detections + signals + completeness + verdicts

It fails-closed: with no trained weights in models/ (they are gitignored), detections come back
empty and the verdicts report "unknown -> treated as fail", which is the correct behaviour for a
readiness gate. Drop the trained best.pt files into models/{region,stamp,signature}_detector/ and
the same endpoints start returning real detections with no code change.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Make the repo root importable whether launched from repo root or elsewhere (mirrors streamlit_app).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import inference, pipeline  # noqa: E402
from app.api_schemas import (  # noqa: E402
    HealthResponse, PoliciesResponse, PredictResponse,
)
from src.config import load_required_fields  # noqa: E402
from src.verdict_engine import preset_policies  # noqa: E402

SERVICE_NAME = "invoice-obligation-readiness-api"
VERSION = "1.0.0"

app = FastAPI(
    title="Invoice Obligation-Readiness API",
    description=__doc__,
    version=VERSION,
)

# Allow curl/Postman/browser clients from anywhere (tighten in a real deployment).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Metadata / health
# ===========================================================================
@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "message": "Invoice Obligation-Readiness pipeline, served over HTTP.",
        "docs": "/docs",
        "endpoints": {
            "GET /health": "liveness + model availability",
            "GET /policies": "preset readiness policies + required fields",
            "POST /predict": "upload an invoice image (multipart 'file') -> readiness JSON",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=VERSION,
        models=inference.detectors_available(),
        ocr_engine="easyocr (CPU, lazy-loaded)",
        device="cpu",
    )


@app.get("/policies", response_model=PoliciesResponse, tags=["config"])
def policies() -> dict:
    presets = [p.to_dict() for p in preset_policies().values()]
    required = [f["field_name"] for f in load_required_fields()["default_required_fields"]]
    return {"presets": presets, "required_fields": required}


# ===========================================================================
# Prediction
# ===========================================================================
@app.post("/predict", response_model=PredictResponse, tags=["inference"])
async def predict(
    file: UploadFile = File(..., description="Invoice image (png/jpg/jpeg/tif/tiff)"),
    confidence: float = Query(0.25, ge=0.0, le=1.0, description="Detector confidence threshold"),
    run_ocr: bool = Query(True, description="Run EasyOCR (enables reference/date/terms signals)"),
    document_id: str | None = Query(None, description="Optional id; defaults to the filename stem"),
) -> dict:
    """Run the full pipeline on one uploaded invoice and return the obligation-readiness JSON.

    Thin HTTP wrapper around ``app.pipeline.predict_from_bytes`` (the same code path the tests
    and any script use). Pipeline: decode -> region + stamp/signature detection -> (optional) OCR
    -> derive signals -> completeness score -> evaluate every preset policy. Stages fail-closed.
    """
    raw = await file.read()
    try:
        return pipeline.predict_from_bytes(
            raw,
            filename=file.filename or "uploaded_image",
            confidence=confidence,
            run_ocr=run_ocr,
            document_id=document_id,
        )
    except pipeline.ImageDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Could not decode image: {e}")
