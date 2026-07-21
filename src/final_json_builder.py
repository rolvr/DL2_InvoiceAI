"""
final_json_builder.py — assembles the final per-invoice JSON record from every member's
outputs, per the schema in model_interface_contract.md.

Owner: Hessam (integration). Reads the shared CSV/JSON outputs produced by Rolando, Diana,
Jordan, and Damir and merges them into one record per document_id.
"""

from typing import Any

REQUIRED_FOR_PISTACIO = [
    "line_items_table",
    "total_amount_region",
]


def build_visual_elements(stamp_sig_rows: list[dict]) -> dict:
    """stamp_sig_rows: rows from stamp_signature_predictions.csv for one document_id,
    each with 'label' ('stamp'|'signature') and 'confidence'."""
    stamp_rows = [r for r in stamp_sig_rows if r["label"] == "stamp"]
    signature_rows = [r for r in stamp_sig_rows if r["label"] == "signature"]

    return {
        "stamp_detected": len(stamp_rows) > 0,
        "signature_detected": len(signature_rows) > 0,
        "stamp_confidence": max((r["confidence"] for r in stamp_rows), default=None),
        "signature_confidence": max((r["confidence"] for r in signature_rows), default=None),
    }


def build_detected_regions(region_rows: list[dict]) -> dict:
    """region_rows: rows from region_predictions.csv for one document_id."""
    present_labels = {r["label"] for r in region_rows}
    tracked = [
        "reference_numbers_region",
        "line_items_table",
        "total_amount_region",
        "payment_terms_region",
        "terms_and_conditions_region",
    ]
    return {label: label in present_labels for label in tracked}


def build_required_parameters(parameter_rows: list[dict]) -> dict:
    """parameter_rows: rows from parameter_presence_results.csv for one document_id, each
    with 'field_name' and 'present'."""
    return {r["field_name"]: bool(r["present"]) for r in parameter_rows}


def build_pistacio_readiness(
    detected_regions: dict,
    required_parameters: dict,
    stamp_detected: bool,
    signature_detected: bool,
) -> dict:
    """Simple, transparent readiness rule: all of REQUIRED_FOR_PISTACIO regions detected,
    all required=True parameters present. Missing items are reported so the demo can explain
    *why* an invoice isn't ready, not just that it isn't."""
    missing_fields = []

    for region in REQUIRED_FOR_PISTACIO:
        if not detected_regions.get(region, False):
            missing_fields.append(region)

    for field_name, present in required_parameters.items():
        if not present:
            missing_fields.append(field_name)

    risk_flags = []
    if not stamp_detected and not signature_detected:
        risk_flags.append("no_stamp_or_signature_detected")
    if not detected_regions.get("terms_and_conditions_region", False):
        risk_flags.append("terms_and_conditions_not_detected")

    return {
        "can_create_digital_obligation_record": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "risk_flags": risk_flags,
    }


def build_final_json(
    document_id: str,
    source_image: str,
    stamp_sig_rows: list[dict],
    region_rows: list[dict],
    parameter_rows: list[dict],
    payment_context: dict,
    terms_and_conditions: dict,
    model_metrics: dict,
) -> dict[str, Any]:
    """Assemble the full record matching the schema in model_interface_contract.md."""
    visual_elements = build_visual_elements(stamp_sig_rows)
    detected_regions = build_detected_regions(region_rows)
    required_parameters = build_required_parameters(parameter_rows)

    pistacio_readiness = build_pistacio_readiness(
        detected_regions,
        required_parameters,
        visual_elements["stamp_detected"],
        visual_elements["signature_detected"],
    )

    return {
        "document_id": document_id,
        "source_image": source_image,
        "visual_elements": visual_elements,
        "detected_regions": detected_regions,
        "required_parameters": required_parameters,
        "payment_context": payment_context,
        "terms_and_conditions": terms_and_conditions,
        "pistacio_readiness": pistacio_readiness,
        "model_metrics": model_metrics,
    }
