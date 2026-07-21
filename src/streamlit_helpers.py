"""
streamlit_helpers.py — shared helpers for app/streamlit_app.py.

Owner: Hessam. Keeps the Streamlit app file focused on layout/UI while the actual
"run the pipeline on one uploaded image" logic lives here and is unit-testable outside
of Streamlit.
"""

import json
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
