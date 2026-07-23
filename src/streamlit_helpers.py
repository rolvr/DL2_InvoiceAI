"""
streamlit_helpers.py — shared helpers for app/streamlit_app.py.

Owner: Hessam. Keeps the Streamlit app file focused on layout/UI while the actual
"run the pipeline on one uploaded image" logic lives here and is unit-testable outside
of Streamlit.
"""

import base64
import html
import json
from datetime import datetime, timezone
from io import BytesIO
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


# ===========================================================================
# Self-contained per-invoice HTML report (Live Demo download).
#
# Everything is inlined (CSS + the annotated image as a base64 data: URI) so the downloaded
# .html file is a single standalone artifact — no external assets, opens offline in any browser.
# ===========================================================================
def image_to_base64_png(image) -> str:
    """PIL.Image -> base64-encoded PNG string (no `data:` prefix)."""
    buf = BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_html_report(
    document_id: str,
    signals: dict[str, Any],
    verdict: dict[str, Any],
    image_b64: str | None = None,
    extracted_text: str | None = None,
    detections: dict[str, Any] | None = None,
) -> str:
    """Render a single self-contained HTML report for one invoice: the annotated image, the
    verdict badge + per-rule breakdown, and the extracted signals/fields — everything a
    presenter needs to hand to someone without them having to open the app.

    `verdict` is `VerdictResult.as_dict()`. `detections` is an optional free-form dict of
    extra context (e.g. detector availability, confidence threshold) shown in a footer table.
    """
    esc = html.escape
    ready = bool(verdict.get("ready"))
    badge_color = "#0ca30c" if ready else "#d03b3b"
    badge_text = "READY" if ready else "NOT READY"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rule_rows = []
    for r in verdict.get("rules", []):
        if not r.get("enabled"):
            icon, row_color = "&#9898;", "#9e9e9e"
            status_label = "disabled"
        else:
            status = r.get("status")
            icon = {"pass": "&#9989;", "fail": "&#10060;", "unknown": "&#10067;"}.get(status, "?")
            row_color = {"pass": "#0ca30c", "fail": "#d03b3b", "unknown": "#eda100"}.get(status, "#333")
            status_label = status
        rule_rows.append(
            f'<tr><td style="color:{row_color}; font-weight:600;">{icon} {esc(r.get("name", ""))}</td>'
            f'<td style="color:{row_color};">{esc(status_label)}</td>'
            f'<td>{esc(r.get("explanation", ""))}</td></tr>'
        )

    refs = signals.get("references")
    if refs is None:
        refs_html = "<p><em>no OCR text available — reference fields unknown</em></p>"
    elif not refs:
        refs_html = "<p><em>OCR ran; no reference fields matched</em></p>"
    else:
        ref_rows = "".join(
            f'<tr><td>{esc(k)}</td><td>{"&#9989; present" if v else "&#10060; absent"}</td></tr>'
            for k, v in refs.items()
        )
        refs_html = f'<table class="fields"><tr><th>Reference field</th><th>Found</th></tr>{ref_rows}</table>'

    fields_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(str(v)) if v is not None else '<em>unknown</em>'}</td></tr>"
        for k, v in [
            ("Stamp detected", signals.get("stamp_detected")),
            ("Signature detected", signals.get("signature_detected")),
            ("Invoice date", signals.get("invoice_date")),
            ("Billing due days", signals.get("billing_due_days")),
        ]
    )

    img_html = (
        f'<img class="invoice-img" src="data:image/png;base64,{image_b64}" alt="annotated invoice"/>'
        if image_b64 else "<p><em>no image attached</em></p>"
    )

    text_html = (
        f'<pre class="ocr-text">{esc(extracted_text)}</pre>' if extracted_text
        else "<p><em>no OCR text extracted</em></p>"
    )

    detections_html = ""
    if detections:
        det_rows = "".join(f"<tr><td>{esc(str(k))}</td><td>{esc(str(v))}</td></tr>" for k, v in detections.items())
        detections_html = f'<h2>Run context</h2><table class="fields">{det_rows}</table>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Invoice report — {esc(document_id)}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; max-width: 900px;
          margin: 2rem auto; padding: 0 1.25rem; line-height: 1.5; color: #1a1a1a;
          background: #ffffff; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e8e8e6; background: #14140f; }}
    table.fields td, table.fields th {{ border-color: #3a3a33 !important; }}
    .ocr-text {{ background: #1f1f18 !important; color: #d8d8d0 !important; }}
    .rules td {{ border-color: #3a3a33 !important; }}
  }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.1rem; }}
  h2 {{ font-size: 1.05rem; margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; }}
  .meta {{ color: #767671; font-size: 0.85rem; margin-bottom: 1.25rem; }}
  .badge {{ display: inline-block; padding: 0.35rem 0.9rem; border-radius: 999px; color: #fff;
            font-weight: 700; letter-spacing: 0.03em; background: {badge_color}; }}
  .invoice-img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 6px; margin-top: 0.75rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 0.5rem; }}
  table.rules td {{ border-bottom: 1px solid #e5e5e0; padding: 0.4rem 0.5rem; vertical-align: top;
                     font-size: 0.92rem; }}
  table.fields td, table.fields th {{ border: 1px solid #ddd; padding: 0.35rem 0.6rem;
                                       text-align: left; font-size: 0.9rem; }}
  .ocr-text {{ background: #f6f6f2; padding: 0.75rem; border-radius: 6px; white-space: pre-wrap;
               word-break: break-word; font-size: 0.85rem; max-height: 320px; overflow-y: auto; }}
  footer {{ margin-top: 2.5rem; color: #999; font-size: 0.78rem; }}
</style>
</head>
<body>
  <h1>Invoice Obligation-Readiness Report</h1>
  <div class="meta">Document: <strong>{esc(document_id)}</strong> &middot; generated {generated} &middot;
    CPU-only pipeline, no GPU used.</div>

  <span class="badge">{badge_text}</span>
  &nbsp; {verdict.get("n_pass", 0)} / {verdict.get("n_enabled", 0)} enabled rules passed

  <h2>Detections</h2>
  {img_html}

  <h2>Verdict — per-rule breakdown</h2>
  <table class="rules">
    <tr><th align="left">Rule</th><th align="left">Status</th><th align="left">Explanation</th></tr>
    {"".join(rule_rows) or "<tr><td colspan=3><em>no rules enabled</em></td></tr>"}
  </table>

  <h2>Extracted fields</h2>
  <table class="fields">{fields_rows}</table>

  <h2>Reference numbers</h2>
  {refs_html}

  <h2>Extracted OCR text</h2>
  {text_html}

  {detections_html}

  <footer>Generated by the Invoice Obligation-Readiness Streamlit demo. Self-contained — no
  external assets, opens offline.</footer>
</body>
</html>
"""

