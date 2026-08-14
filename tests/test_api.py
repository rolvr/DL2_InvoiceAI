"""
test_api.py — tests for the Invoice Obligation-Readiness FastAPI service.

Two layers:
  * HTTP-level tests use Starlette/FastAPI's TestClient (no running server needed). They are
    skipped automatically if fastapi isn't installed, so the file never errors on collection.
  * Pipeline-level tests exercise app/pipeline.py directly (the same code the endpoint calls),
    with the detectors/OCR monkeypatched — so the happy path is covered without trained weights.

Run:  pip install -r requirements-api.txt && pytest -q
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app import inference, pipeline


# ---------------------------------------------------------------------------
# helpers / fixtures
# ---------------------------------------------------------------------------
def _png_bytes(w: int = 200, h: int = 260, color: str = "white") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def blank_png() -> bytes:
    return _png_bytes()


@pytest.fixture
def client():
    """FastAPI TestClient — skipped if fastapi/starlette aren't installed."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from app.api import app
    return TestClient(app)


@pytest.fixture
def fake_ocr_and_detectors(monkeypatch):
    """Patch the heavy stages so the happy path runs without weights/easyocr."""
    text = ("ACME SUPPLIES LTD  INVOICE NO: INV-2026-0098  Date: 2026-03-14  "
            "PO Number: PO-55231  Total Due: $4,250.00  Payment terms: Net 30")
    monkeypatch.setattr(inference, "run_ocr", lambda img, **k: text)
    monkeypatch.setattr(inference, "run_detectors", lambda img, conf=0.25: {
        "stamp_sig_rows": [{"label": "signature", "confidence": 0.9,
                            "xmin": 1, "ymin": 1, "xmax": 2, "ymax": 2}],
        "region_rows": [{"region_label": "total", "confidence": 0.8,
                         "xmin": 1, "ymin": 1, "xmax": 2, "ymax": 2},
                        {"region_label": "company", "confidence": 0.8,
                         "xmin": 1, "ymin": 1, "xmax": 2, "ymax": 2}],
        "vision_available": True, "region_available": True, "notes": [],
    })
    return text


# ---------------------------------------------------------------------------
# HTTP-level tests (TestClient)
# ---------------------------------------------------------------------------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["models"]) == {"region", "stamp_signature"}


def test_policies(client):
    r = client.get("/policies")
    assert r.status_code == 200
    body = r.json()
    names = {p["name"] for p in body["presets"]}
    assert {"Default", "Strict", "Lenient"} <= names
    assert "PO Reference" in body["required_fields"]


def test_predict_degraded_blank_image(client, blank_png):
    r = client.post("/predict", params={"run_ocr": "false"},
                    files={"file": ("blank.png", blank_png, "image/png")})
    assert r.status_code == 200
    body = r.json()
    # No weights on disk -> every verdict fails-closed, degraded True.
    assert body["meta"]["degraded"] is True
    assert body["detections"]["region_model_available"] is False
    for v in body["verdicts"].values():
        assert v["ready"] is False


def test_predict_rejects_non_image(client):
    r = client.post("/predict",
                    files={"file": ("x.txt", b"not an image", "text/plain")})
    assert r.status_code == 400


def test_predict_happy_path_via_http(client, blank_png, fake_ocr_and_detectors):
    r = client.post("/predict", files={"file": ("acme.png", blank_png, "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["completeness"]["tier"] == "Ready"
    assert body["verdicts"]["Default"]["ready"] is True
    assert body["signals"]["references"]["PO Reference"] is True


# ---------------------------------------------------------------------------
# Pipeline-level tests (no server / no FastAPI needed)
# ---------------------------------------------------------------------------
def test_pipeline_fail_closed(blank_png):
    res = pipeline.predict_from_bytes(blank_png, filename="blank.png", run_ocr=False)
    assert res["meta"]["degraded"] is True
    assert res["signals"]["references"] is None
    assert all(not v["ready"] for v in res["verdicts"].values())


def test_pipeline_happy_path(blank_png, fake_ocr_and_detectors):
    res = pipeline.predict_from_bytes(blank_png, filename="acme.png", run_ocr=True)
    assert res["completeness"]["score"] == 100
    assert res["signals"]["invoice_date"] == "2026-03-14"
    assert res["signals"]["billing_due_days"] == 30
    assert res["verdicts"]["Strict"]["ready"] is True


def test_pipeline_bad_bytes_raises():
    with pytest.raises(pipeline.ImageDecodeError):
        pipeline.predict_from_bytes(b"not-an-image", filename="x.png")
