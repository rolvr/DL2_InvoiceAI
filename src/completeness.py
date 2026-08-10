"""
completeness.py — graded obligation-readiness "completeness score".

A complement to the strict, pass/fail verdict_engine: instead of one hard gate (which is ~0% on a
corpus with no PO/contract references), this scores HOW MANY of the core fields required to form a
digital obligation record are actually present, against a standardized weighted rubric, and bins
each invoice into Ready / Needs review / Not ready.

Mirrors notebook 06 (colab/notebooks/06_readiness_completeness_colab.ipynb). Honest by design:
only detected evidence scores; unknowns count 0 (fail-closed); the reference slot is capped at
20/100 and only counts a digit-bearing invoice/document number (not a bare label), so it cannot
dominate. Every score carries a per-field breakdown.
"""

from __future__ import annotations

import re
from typing import Any

# --- Standardized, config-driven rubric (edit here) ---------------------------
WEIGHTS = {
    "total": 25,          # the obligation amount
    "date": 20,           # issue date
    "reference": 20,      # a unique identifier: PO/Order/Contract OR invoice/receipt/doc no.
    "counterparty": 20,   # seller / buyer identity
    "readable": 15,       # machine-readable OCR text
}
BONUS = {"payment_terms": 10, "visual_mark": 10}   # added on top; final score capped at 100
THRESHOLDS = {"ready": 80, "review": 60}           # >=80 Ready | 60-79 Needs review | <60 Not ready
OCR_CONF_MIN = 0.5

# A document/invoice/receipt number counts as a reference ONLY if it looks like a real identifier
# (>= 2 digits) — so "INVOICE NO: 95216794" matches but a bare label like "INVOICE: DATE" does not.
_DOCNO_RE = re.compile(
    r"\b(?:invoice|receipt|bill|doc(?:ument)?|ref(?:erence)?|inv)\b"
    r"[\s.:#-]*(?:no\.?|number|#)?[\s.:#-]*"
    r"([A-Z0-9][A-Z0-9/\-]{2,})", re.I)


def find_docno(text: str | None) -> str | None:
    """Return the first document/invoice identifier that carries >= 2 digits, else None."""
    if not text:
        return None
    for m in _DOCNO_RE.finditer(text):
        tok = m.group(1)
        if sum(ch.isdigit() for ch in tok) >= 2:
            return tok
    return None


def _num(v) -> bool:
    """True if v is a usable (non-empty, non-NaN) value."""
    if v is None:
        return False
    try:
        if isinstance(v, float) and v != v:   # NaN
            return False
    except Exception:
        pass
    return str(v).strip() != ""


def score(signals: dict[str, Any], region_labels: set[str] | None = None,
          ocr_text: str | None = None, mean_conf: float | None = None) -> dict[str, Any]:
    """Score one invoice's completeness.

    `signals` is the verdict-engine signals dict (stamp_detected, signature_detected, references,
    invoice_date, billing_due_days). `region_labels` is the set of Jordan region labels detected on
    the invoice (e.g. {"total", "company"}). `ocr_text` + `mean_conf` come from Damir's OCR.

    Returns: score (0-100), tier, and a has_<field> boolean breakdown (+ reference_match token).
    """
    region_labels = region_labels or set()
    refs = signals.get("references") or {}
    po = any(bool(v) for v in refs.values()) if isinstance(refs, dict) else False
    docno = find_docno(ocr_text)

    present = {
        "total": "total" in region_labels,
        "date": _num(signals.get("invoice_date")),
        "reference": po or bool(docno),
        "counterparty": bool(region_labels & {"company", "address"}),
        "readable": bool(ocr_text) and (mean_conf is None or (_num(mean_conf) and float(mean_conf) >= OCR_CONF_MIN)),
    }
    bonus = {
        "payment_terms": _num(signals.get("billing_due_days")) or _num(signals.get("payment_terms")),
        "visual_mark": bool(signals.get("stamp_detected") or signals.get("signature_detected")),
    }
    total = sum(w for k, w in WEIGHTS.items() if present[k]) + sum(BONUS[k] for k, v in bonus.items() if v)
    total = min(total, 100)
    tier = ("Ready" if total >= THRESHOLDS["ready"]
            else "Needs review" if total >= THRESHOLDS["review"] else "Not ready")

    out: dict[str, Any] = {"score": total, "tier": tier,
                           "reference_match": ("PO/Order/Contract" if po else (docno or ""))}
    out.update({f"has_{k}": present[k] for k in WEIGHTS})
    out.update({f"bonus_{k}": bonus[k] for k in BONUS})
    return out
