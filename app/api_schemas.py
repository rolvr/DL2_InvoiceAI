"""
api_schemas.py — Pydantic response models for the Invoice AI FastAPI service.

These drive the auto-generated OpenAPI docs at /docs and validate what the API returns.
Dynamic-keyed blocks (completeness has_<field>, signals.references) are typed loosely on purpose.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str
    models: dict[str, bool] = Field(..., description="Which detectors have weights on disk")
    ocr_engine: str
    device: str = "cpu"


class PolicyRule(BaseModel):
    kind: str
    name: str
    enabled: bool
    # rule-specific fields (mode / fields / start / end / op / days) come through as extras
    model_config = {"extra": "allow"}


class PolicyModel(BaseModel):
    name: str
    rules: list[PolicyRule]


class PoliciesResponse(BaseModel):
    presets: list[PolicyModel]
    required_fields: list[str]


class RegionDetection(BaseModel):
    region_label: str
    confidence: float
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class VisualDetection(BaseModel):
    label: str
    confidence: float
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class DetectionsBlock(BaseModel):
    regions: list[RegionDetection]
    visual_marks: list[VisualDetection]
    region_model_available: bool
    stamp_signature_model_available: bool
    notes: list[str] = []


class OCRBlock(BaseModel):
    ran: bool
    text: Optional[str] = None
    char_count: int = 0


class Signals(BaseModel):
    stamp_detected: Optional[bool] = None
    signature_detected: Optional[bool] = None
    references: Optional[dict[str, bool]] = None
    invoice_date: Optional[str] = None
    billing_due_days: Optional[int] = None


class VerdictRule(BaseModel):
    name: str
    enabled: bool
    status: str
    explanation: str
    passed: bool


class Verdict(BaseModel):
    ready: bool
    n_pass: int
    n_enabled: int
    rules: list[VerdictRule]


class PredictMeta(BaseModel):
    confidence_threshold: float
    ocr_ran: bool
    device: str = "cpu"
    degraded: bool
    processing_time_ms: float


class PredictResponse(BaseModel):
    document_id: str
    filename: str
    image: dict[str, int]
    detections: DetectionsBlock
    ocr: OCRBlock
    signals: Signals
    completeness: dict[str, Any]
    verdicts: dict[str, Verdict]
    meta: PredictMeta
