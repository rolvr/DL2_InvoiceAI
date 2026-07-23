"""
streamlit_helpers.py — shared helpers for app/streamlit_app.py.

Owner: Hessam. Keeps the Streamlit app file focused on layout/UI while the actual
"run the pipeline on one uploaded image" logic lives here and is unit-testable outside
of Streamlit.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np


def run_full_pipeline(
    image: np.ndarray,
    confidence_threshold: float = 0.5,
    iou_threshold: float = 0.5,
    extra_required_fields: list[dict] | None = None,
) -> dict[str, Any]:
    """Run preprocessing -> region detection -> stamp/signature detection -> OCR ->
    parameter/terms extraction -> final JSON build, on a single uploaded image.

    This is a placeholder that wires together the src/ modules; each TODO should be
    filled in once the corresponding member's model is trained and its load_*/predict_*
    functions in src/layout_detection.py and src/stamp_signature_detection.py are
    implemented.

    Returns a dict matching the final JSON schema (model_interface_contract.md), with
    detected fields on success or a safe "not detected" fallback where a stage failed
    or a required model isn't trained/available yet.
    """
    from src.final_json_builder import build_final_json
    from src.image_preprocessing import preprocess_pipeline
    from src.ocr import ocr_regions
    from src.parameter_checker import check_all_fields
    from src.terms_extraction import extract_terms_and_conditions

    preprocessed = preprocess_pipeline(image, do_threshold=False)

    # TODO(Jordan's model): region_rows = predict_regions(preprocessed, region_model, confidence_threshold)
    region_rows: list[dict] = []

    # TODO(Diana's model): stamp_sig_rows = predict_stamp_signature(preprocessed, stamp_model, signature_model, confidence_threshold)
    stamp_sig_rows: list[dict] = []

    ocr_results = ocr_regions(preprocessed, region_rows) if region_rows else []
    region_texts = {r["label"]: r["text"] for r in ocr_results}

    combined_text = " ".join(region_texts.values())
    parameter_rows = check_all_fields(combined_text, extra_fields=extra_required_fields)

    terms_data = extract_terms_and_conditions(region_texts)

    model_metrics = {
        "region_mean_iou": None,
        "stamp_iou": None,
        "signature_iou": None,
    }

    return build_final_json(
        document_id="uploaded_image",
        source_image="uploaded_image",
        stamp_sig_rows=stamp_sig_rows,
        region_rows=region_rows,
        parameter_rows=parameter_rows,
        payment_context=terms_data["payment_context"],
        terms_and_conditions=terms_data["terms_and_conditions"],
        model_metrics=model_metrics,
    )


def to_downloadable_json(result: dict[str, Any]) -> bytes:
    """Serialize a result dict to pretty-printed JSON bytes for st.download_button."""
    return json.dumps(result, indent=2, default=str).encode("utf-8")


# ===========================================================================
# Verdict signals — derive the 4 signal groups the verdict engine needs.
#
# Reality check (see the interface contract + the frozen member notebooks):
#   * Diana's stamp/signature predictions ARE keyed to the 750 invoice document_ids.
#   * Jordan's region predictions include invoice-keyed rows.
#   * Damir's parameter/terms CSVs are keyed to the OCR-DATASET receipts, NOT the invoices, so
#     they cannot be read directly for an invoice verdict. Instead we DERIVE the reference/date/
#     payment-terms signals here, at integration time, by running the shared src/ text modules on
#     whatever OCR text / annotation text we have for a given invoice.
# Missing signals are returned as None so the verdict engine can fail-closed.
# ===========================================================================
def derive_reference_signals(text: str | None, extra_fields: list[dict] | None = None) -> dict | None:
    """Which reference fields are present in `text`. Returns None if there is no text at all
    (=> 'unknown' at verdict time), or a {field_name: bool} dict if text was available."""
    if not text:
        return None
    from src.parameter_checker import check_all_fields

    results = check_all_fields(text, extra_fields=extra_fields)
    return {r["field_name"]: bool(r["present"]) for r in results}


def derive_terms_signals(text: str | None) -> dict:
    """Pull invoice_date + billing_due_days from free OCR/annotation text using Damir's shared
    terms_extraction module. Values are None when not found (=> fail-closed)."""
    out = {"invoice_date": None, "billing_due_days": None, "payment_terms": None}
    if not text:
        return out
    from src.terms_extraction import extract_billing_due_days, extract_dates, extract_payment_terms

    dates = extract_dates(text)
    out["invoice_date"] = dates[0] if dates else None
    out["billing_due_days"] = extract_billing_due_days(text)
    out["payment_terms"] = extract_payment_terms(text)
    return out


def signals_from_record(record: dict[str, Any], ocr_text: str | None = None,
                        extra_fields: list[dict] | None = None) -> dict[str, Any]:
    """Build the verdict-engine signals dict from a per-invoice final-JSON `record`, optionally
    enriched with raw `ocr_text` (for reference/date/terms derivation).

    `record` follows model_interface_contract.md. `ocr_text` is the invoice's OCR text if we
    have it (Damir's invoice_batch1 rows, or an annotation CSV's 'OCRed Text'); when absent, the
    reference/date/terms signals are None so the verdict fails closed on those rules.
    """
    ve = record.get("visual_elements", {})
    pc = record.get("payment_context", {})

    terms = derive_terms_signals(ocr_text)
    references = derive_reference_signals(ocr_text, extra_fields=extra_fields)

    return {
        "stamp_detected": ve.get("stamp_detected"),
        "signature_detected": ve.get("signature_detected"),
        "references": references,
        # prefer a structured date already on the record, else the derived one
        "invoice_date": pc.get("invoice_date") or terms["invoice_date"],
        "billing_due_days": pc.get("billing_due_days") if pc.get("billing_due_days") is not None
        else terms["billing_due_days"],
    }


def signals_from_pipeline_result(result: dict[str, Any], ocr_text: str | None = None,
                                 extra_fields: list[dict] | None = None) -> dict[str, Any]:
    """Same as signals_from_record but for a live `run_full_pipeline` result on an upload.
    The combined OCR text from the pipeline (if any) drives reference/date/terms derivation."""
    return signals_from_record(result, ocr_text=ocr_text, extra_fields=extra_fields)

