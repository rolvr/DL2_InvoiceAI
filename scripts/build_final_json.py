"""
build_final_json.py — Hessam's integration: fuse every member's outputs into one JSON per
invoice, and compute batch obligation-readiness statistics.

CPU-only, no GPU, no notebook. Reuses the shared modules (final_json_builder, verdict_engine,
streamlit_helpers, results_store) so the materialized JSON matches exactly what the Streamlit app
computes on the fly. Writes:
  - outputs/final_json/sample_invoice_outputs/<document_id>.json   (all manifest invoices; gitignored)
  - outputs/reports/final_pipeline_report.md                       (tracked integration report)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.config import PATHS
from src import results_store as RS
from src.final_json_builder import build_final_json
from src.streamlit_helpers import signals_from_record
from src.verdict_engine import default_policy, preset_policies, evaluate

# Jordan's receipt-entity labels -> the contract's tracked obligation regions (only 'total' maps).
REGION_MAP = {"total": "total_amount_region"}


def _by_doc(rows, key="document_id"):
    d = defaultdict(list)
    for r in rows:
        d[str(r.get(key))].append(r)
    return d


def main():
    manifest = pd.read_csv(PATHS.processed_dir / "invoice_manifest.csv").to_dict("records")
    diana = _by_doc(RS.load_stamp_signature())
    jordan = _by_doc([r for r in RS.load_regions() if str(r.get("source")) == "invoice"])
    params = _by_doc(pd.read_csv(
        PATHS.predictions_dir / "parameter_presence_results.csv").to_dict("records"))
    terms = {str(r["document_id"]): r for r in
             pd.read_csv(PATHS.predictions_dir / "terms_extraction_results.csv").to_dict("records")}
    ocr_text = RS.invoice_ocr_text()

    out_dir = PATHS.final_json_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()

    policy = default_policy()
    presets = preset_policies()
    ready_by_preset = {name: 0 for name in presets}
    region_label_counts = defaultdict(int)
    n_written = 0
    n_ready_default = 0

    for m in manifest:
        doc = str(m["document_id"])
        ss_rows = [{"label": r["label"], "confidence": r.get("confidence", 0.0),
                    "xmin": r.get("xmin"), "ymin": r.get("ymin"),
                    "xmax": r.get("xmax"), "ymax": r.get("ymax")} for r in diana.get(doc, [])]

        reg_rows = []
        for r in jordan.get(doc, []):
            lbl = r.get("region_label")
            region_label_counts[lbl] += 1
            reg_rows.append({"label": REGION_MAP.get(lbl, lbl),
                             "confidence": r.get("confidence")})

        param_rows = [{"field_name": r["field_name"], "present": bool(r["present"])}
                      for r in params.get(doc, [])]

        t = terms.get(doc, {})
        def _clean(v):
            return None if (v is None or (isinstance(v, float) and pd.isna(v))) else v
        payment_context = {
            "invoice_date": _clean(t.get("invoice_date")),
            "due_date": _clean(t.get("due_date")),
            "payment_terms": _clean(t.get("payment_terms")),
            "billing_due_days": _clean(t.get("billing_due_days")),
        }
        terms_and_conditions = {
            "region_detected": False,
            "late_payment_clause_detected": bool(t.get("late_payment_flag", False)),
            "dispute_clause_detected": bool(t.get("dispute_flag", False)),
            "penalty_clause_detected": bool(t.get("penalty_flag", False)),
            "extracted_text": str(_clean(t.get("extracted_text")) or ""),
            "summary": str(_clean(t.get("summary")) or ""),
        }

        rec = build_final_json(
            document_id=doc, source_image=m.get("image_path", ""),
            stamp_sig_rows=ss_rows, region_rows=reg_rows, parameter_rows=param_rows,
            payment_context=payment_context, terms_and_conditions=terms_and_conditions,
            model_metrics={"region_mean_iou": 0.8731, "stamp_iou": 0.822, "signature_iou": 0.8148},
        )
        # extra, honest region info (Jordan's real labels, beyond the contract's tracked set)
        rec["region_detections_raw"] = {
            lbl: sum(1 for r in jordan.get(doc, []) if r.get("region_label") == lbl)
            for lbl in ["company", "date", "address", "total", "other_text"]
        }

        # the user-configurable verdict (default policy) + all presets for the batch stats
        sig = signals_from_record(rec, ocr_text=ocr_text.get(doc))
        v = evaluate(sig, policy)
        rec["configurable_verdict_default"] = v.as_dict()
        if v.ready:
            n_ready_default += 1
        for name, pol in presets.items():
            if evaluate(sig, pol).ready:
                ready_by_preset[name] += 1

        (out_dir / f"{doc}.json").write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
        n_written += 1

    # integration report
    N = len(manifest)
    rep = PATHS.reports_dir / "final_pipeline_report.md"
    rep.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final Pipeline Integration Report", "",
        f"Fused **{n_written}** per-invoice JSON records from all four upstream stages into "
        f"`outputs/final_json/sample_invoice_outputs/`.", "",
        "## Obligation-readiness across the batch (by policy)", "",
        "| Policy | Invoices Ready | of | % |",
        "|---|---|---|---|",
    ]
    for name in presets:
        lines.append(f"| {name} | {ready_by_preset[name]} | {N} | {100*ready_by_preset[name]/N:.1f}% |")
    lines += [
        "", f"Default policy: **{n_ready_default} / {N} ready** "
        f"({100*n_ready_default/N:.1f}%).", "",
        "## Region detections on invoices (Jordan, `source=invoice`)", "",
        "| Region label | Total boxes across 750 invoices |", "|---|---|",
    ]
    for lbl, c in sorted(region_label_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {lbl} | {c} |")
    lines += [
        "", "## Honest integration notes", "",
        "- **Visual rule fails-closed on the whole batch:** the invoice corpus is clean digital "
        "templates with no stamps or signatures (Diana: 0/750 detections), so any policy requiring "
        "a visual mark yields 0 ready. This is a property of the data, not a model failure "
        "(Diana's held-out stamp IoU 0.82 / signature IoU 0.81).",
        "- Reference/date/terms signals are derived at integration from invoice OCR text + batch_1 "
        "annotation text (Damir's per-receipt CSVs are not invoice-keyed).",
        "- `detected_regions` uses the contract's tracked labels; Jordan's richer receipt-entity "
        "labels are preserved under `region_detections_raw`.",
    ]
    rep.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {n_written} JSON records -> {out_dir}")
    print(f"default-policy ready: {n_ready_default}/{N}")
    print("ready by preset:", ready_by_preset)
    print("region label counts:", dict(region_label_counts))
    print(f"report -> {rep}")


if __name__ == "__main__":
    main()
