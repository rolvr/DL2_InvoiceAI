"""
streamlit_app.py — final demo app for the Invoice Region Detection and Business Parameter
Extraction pipeline.

Owner: Hessam. Run with:
    streamlit run app/streamlit_app.py

This app lets a user upload an invoice image and walks it through the full pipeline:
preprocessing -> region detection -> stamp/signature detection -> OCR on detected regions ->
required-parameter checking -> payment terms / terms & conditions extraction -> final
Pistac.io-readiness JSON.

NOTE: Until Jordan's and Diana's trained detectors are wired into src/layout_detection.py
and src/stamp_signature_detection.py, this app runs end-to-end but region/stamp/signature
detection will report "not detected" (see src/streamlit_helpers.run_full_pipeline). That is
expected during early development — the UI, OCR, parameter-checking, and JSON-export paths
are all fully functional against that placeholder.
"""

import sys
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

# Make `src` importable when Streamlit runs this file directly (not as an installed package).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import load_required_fields  # noqa: E402
from src.streamlit_helpers import run_full_pipeline, to_downloadable_json  # noqa: E402

st.set_page_config(page_title="Invoice Obligation-Readiness Demo", layout="wide")

st.title("Invoice Region Detection & Business Parameter Extraction")
st.caption(
    "CNN / SSD-style region detection -> IoU evaluation -> OCR -> parameter & terms "
    "extraction -> Pistac.io obligation-readiness JSON."
)

# ---------------------------------------------------------------------------
# Sidebar: configuration controls
# ---------------------------------------------------------------------------
st.sidebar.header("Detection settings")
confidence_threshold = st.sidebar.slider("Detection confidence threshold", 0.0, 1.0, 0.5, 0.05)
iou_threshold = st.sidebar.slider("IoU threshold", 0.0, 1.0, 0.5, 0.05)

st.sidebar.header("Required fields")
required_fields_config = load_required_fields()
default_field_names = [f["field_name"] for f in required_fields_config["default_required_fields"]]
selected_fields = st.sidebar.multiselect(
    "Fields to check for", options=default_field_names, default=default_field_names
)

st.sidebar.subheader("Add a custom field")
custom_field_name = st.sidebar.text_input("Custom field name", value="")
custom_keywords = st.sidebar.text_input("Custom keywords (comma-separated)", value="")
custom_pattern = st.sidebar.text_input("Custom regex pattern (optional)", value="")

extra_fields = []
if custom_field_name.strip():
    extra_fields.append({
        "field_name": custom_field_name.strip(),
        "required": True,
        "keywords": [k.strip() for k in custom_keywords.split(",") if k.strip()],
        "patterns": [custom_pattern.strip()] if custom_pattern.strip() else [],
    })

# ---------------------------------------------------------------------------
# Main: upload + run pipeline
# ---------------------------------------------------------------------------
uploaded_file = st.file_uploader("Upload an invoice image", type=["png", "jpg", "jpeg", "tif", "tiff"])

if uploaded_file is not None:
    pil_image = Image.open(uploaded_file).convert("RGB")
    image_np = np.array(pil_image)[:, :, ::-1]  # RGB -> BGR for OpenCV-based src/ functions

    col_image, col_summary = st.columns([1, 1])
    with col_image:
        st.subheader("Uploaded invoice")
        st.image(pil_image, use_container_width=True)

    with st.spinner("Running detection + OCR pipeline..."):
        result = run_full_pipeline(
            image_np,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            extra_required_fields=extra_fields or None,
        )

    with col_summary:
        st.subheader("Visual elements")
        ve = result["visual_elements"]
        c1, c2 = st.columns(2)
        c1.metric("Stamp", "Detected" if ve["stamp_detected"] else "Not detected")
        c2.metric("Signature", "Detected" if ve["signature_detected"] else "Not detected")

        st.subheader("Detected regions")
        for label, present in result["detected_regions"].items():
            st.write(("✅ " if present else "❌ ") + label)

    st.divider()
    st.subheader("Required parameters")
    for field_name, present in result["required_parameters"].items():
        st.write(("✅ " if present else "❌ ") + field_name)

    st.subheader("Payment context")
    st.json(result["payment_context"])

    st.subheader("Terms & conditions")
    st.json(result["terms_and_conditions"])

    st.subheader("Model metrics")
    st.json(result["model_metrics"])

    st.divider()
    st.subheader("Pistac.io readiness")
    readiness = result["pistacio_readiness"]
    if readiness["can_create_digital_obligation_record"]:
        st.success("This invoice has everything needed for a digital obligation record.")
    else:
        st.warning(f"Missing before this invoice is Pistac.io-ready: {readiness['missing_fields']}")
    if readiness["risk_flags"]:
        st.error(f"Risk flags: {readiness['risk_flags']}")

    st.subheader("Full JSON result")
    st.json(result)
    st.download_button(
        "Download JSON",
        data=to_downloadable_json(result),
        file_name="invoice_result.json",
        mime="application/json",
    )
else:
    st.info("Upload an invoice image above to run the pipeline.")
