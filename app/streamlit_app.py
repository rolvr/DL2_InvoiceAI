"""
streamlit_app.py — Invoice Obligation-Readiness demo.

Owner: Hessam. Run with:  streamlit run app/streamlit_app.py

The app's centrepiece is a USER-CONFIGURABLE verdict: the user builds a policy from rules
(visual mark / reference number / invoice-date range / payment-terms days) in the sidebar, and
every invoice is judged Ready / Not-ready against it, with a transparent per-rule breakdown.

Three views:
  • Live Demo    — upload or pick an invoice → annotated image → verdict → downloads
  • Batch Gallery— apply the policy across all invoices → "N of M pass" → filter → drilldown
  • Model Report — the members' metrics + local-CPU-vs-Colab-GPU comparison

Hybrid data model: Gallery/Report read pre-computed member outputs from `outputs/` (shown as
"waiting for X" until they land); a brand-new upload runs the real detectors live IF their
weights are in `models/`, else it still produces a verdict with vision marked "model unavailable".
Fail-closed: any enabled rule without a signal counts as a fail.
"""

import sys
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import results_store as RS  # noqa: E402
from src import policy_store  # noqa: E402
from src.config import load_required_fields, PATHS  # noqa: E402
from src.streamlit_helpers import signals_from_record  # noqa: E402
from src.verdict_engine import (  # noqa: E402
    DateRangeRule, PaymentTermsRule, Policy, ReferenceRule, VisualRule, evaluate,
)

st.set_page_config(page_title="Invoice Obligation-Readiness", layout="wide", page_icon="🧾")

REGION_COLORS = {
    "company": "#e45756", "date": "#54a24b", "address": "#f58518",
    "total": "#7c4dff", "other_text": "#9e9e9e",
}
VISUAL_COLORS = {"stamp": "#e45756", "signature": "#4c78a8"}


# ===========================================================================
# Sidebar — navigation + the verdict policy builder
# ===========================================================================
def sidebar_policy() -> Policy:
    st.sidebar.title("🧾 Obligation-Readiness")
    view = st.sidebar.radio("View", ["Live Demo", "Batch Gallery", "Model Report"])
    st.session_state["view"] = view

    st.sidebar.divider()
    st.sidebar.header("Verdict policy")
    st.sidebar.caption("Enable rules and set their values. **All enabled rules must pass** for "
                       "an invoice to be *Ready*. Missing evidence counts as a fail.")

    # load / save named policies
    saved = policy_store.load_all()
    names = list(saved.keys())
    picked = st.sidebar.selectbox("Load a policy", names,
                                  index=names.index("Default") if "Default" in names else 0)
    if st.sidebar.button("↩︎ Load into builder", width="stretch"):
        st.session_state["loaded_policy"] = saved[picked].to_dict()
        st.rerun()

    base = Policy.from_dict(st.session_state["loaded_policy"]) if "loaded_policy" in st.session_state \
        else saved.get("Default", saved[names[0]])
    b = {r.kind: r for r in base.rules}

    # --- Visual rule ---
    vis = b.get("visual", VisualRule())
    v_on = st.sidebar.checkbox("Visual mark", value=vis.enabled)
    v_mode = st.sidebar.radio("Required mark", ["either", "both", "stamp", "signature"],
                              index=["either", "both", "stamp", "signature"].index(vis.mode),
                              horizontal=True, label_visibility="collapsed",
                              format_func=lambda m: {"either": "stamp OR signature",
                                                     "both": "stamp AND signature",
                                                     "stamp": "stamp only",
                                                     "signature": "signature only"}[m])

    # --- Reference rule ---
    st.sidebar.markdown("---")
    ref = b.get("reference", ReferenceRule())
    r_on = st.sidebar.checkbox("Reference number present", value=ref.enabled)
    all_ref_fields = [f["field_name"] for f in load_required_fields()["default_required_fields"]]
    r_fields = st.sidebar.multiselect("Accept any of", all_ref_fields,
                                      default=[f for f in ref.fields if f in all_ref_fields])
    r_mode = st.sidebar.radio("Match", ["any", "all"], horizontal=True,
                              index=["any", "all"].index(ref.mode),
                              format_func=lambda m: "at least one" if m == "any" else "all of them")

    # --- Date range rule ---
    st.sidebar.markdown("---")
    dr = b.get("date", DateRangeRule())
    d_on = st.sidebar.checkbox("Invoice date in range", value=dr.enabled)
    c1, c2 = st.sidebar.columns(2)
    d_start = c1.text_input("From (YYYY-MM-DD)", value=dr.start or "")
    d_end = c2.text_input("To (YYYY-MM-DD)", value=dr.end or "")

    # --- Payment terms rule ---
    st.sidebar.markdown("---")
    pt = b.get("payment_terms", PaymentTermsRule())
    p_on = st.sidebar.checkbox("Payment terms threshold", value=pt.enabled)
    c3, c4 = st.sidebar.columns([1, 1])
    p_op = c3.selectbox("Due", [">", ">=", "<", "<=", "=="],
                        index=[">", ">=", "<", "<=", "=="].index(pt.op))
    p_days = c4.number_input("days", min_value=0, max_value=365, value=int(pt.days), step=5)

    policy = Policy(name=picked, rules=[
        VisualRule(enabled=v_on, mode=v_mode),
        ReferenceRule(enabled=r_on, fields=r_fields or all_ref_fields, mode=r_mode),
        DateRangeRule(enabled=d_on, start=d_start or None, end=d_end or None),
        PaymentTermsRule(enabled=p_on, op=p_op, days=int(p_days)),
    ])

    # save-as
    st.sidebar.markdown("---")
    new_name = st.sidebar.text_input("Save current policy as", value="")
    if st.sidebar.button("💾 Save policy", width="stretch") and new_name.strip():
        policy.name = new_name.strip()
        policy_store.save(policy)
        st.sidebar.success(f"Saved '{new_name.strip()}'")
        st.rerun()

    return policy


# ===========================================================================
# Verdict rendering
# ===========================================================================
def render_verdict(signals: dict, policy: Policy):
    v = evaluate(signals, policy)
    if v.ready:
        st.success(f"### ✅ READY  ·  {v.n_pass}/{v.n_enabled} rules passed")
    else:
        st.error(f"### ⛔ NOT READY  ·  {v.n_pass}/{v.n_enabled} rules passed")
    for r in v.rules:
        if not r.enabled:
            st.markdown(f"&nbsp;&nbsp;⚪ ~~{r.name}~~ *(disabled)*", unsafe_allow_html=True)
            continue
        icon = {"pass": "✅", "fail": "❌", "unknown": "❓"}[r.status]
        tail = " *(unknown → treated as fail)*" if r.status == "unknown" else ""
        st.markdown(f"&nbsp;&nbsp;{icon} **{r.name}** — {r.explanation}{tail}")
    return v


# ===========================================================================
# Live inference (hybrid) — load member weights if present in models/
# ===========================================================================
@st.cache_resource(show_spinner=False)
def _load_yolo(weights_path: str):
    from ultralytics import YOLO
    return YOLO(weights_path)


def _weights(sub: str) -> Path | None:
    p = PATHS.models_dir / sub / "best.pt"
    return p if p.exists() else None


def run_live(image_bgr: np.ndarray, conf: float) -> dict:
    """Run whatever detectors have weights present. Returns rows + availability flags."""
    out = {"stamp_sig_rows": [], "region_rows": [],
           "vision_available": False, "region_available": False}
    ss = _weights("stamp_detector") or _weights("signature_detector")
    if ss:
        try:
            m = _load_yolo(str(ss))
            pr = m.predict(image_bgr, conf=conf, verbose=False)[0]
            names = pr.names
            for c, b, cf in zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy(),
                                pr.boxes.conf.cpu().numpy()):
                out["stamp_sig_rows"].append({"label": names[int(c)], "confidence": round(float(cf), 3),
                                              "xmin": float(b[0]), "ymin": float(b[1]),
                                              "xmax": float(b[2]), "ymax": float(b[3])})
            out["vision_available"] = True
        except Exception as e:
            st.warning(f"stamp/signature model failed to run: {e}")
    rw = _weights("region_detector")
    if rw:
        try:
            m = _load_yolo(str(rw))
            pr = m.predict(image_bgr, conf=conf, verbose=False)[0]
            names = pr.names
            for c, b, cf in zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy(),
                                pr.boxes.conf.cpu().numpy()):
                out["region_rows"].append({"region_label": names[int(c)], "confidence": round(float(cf), 3),
                                           "xmin": float(b[0]), "ymin": float(b[1]),
                                           "xmax": float(b[2]), "ymax": float(b[3])})
            out["region_available"] = True
        except Exception as e:
            st.warning(f"region model failed to run: {e}")
    return out


def draw_overlays(pil: Image.Image, stamp_sig_rows, region_rows,
                  show_regions=True, show_visual=True) -> Image.Image:
    img = pil.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    if show_regions:
        for r in region_rows:
            c = REGION_COLORS.get(r.get("region_label"), "#333")
            d.rectangle([r["xmin"], r["ymin"], r["xmax"], r["ymax"]], outline=c, width=3)
            d.text((r["xmin"] + 2, max(0, r["ymin"] - 12)),
                   f'{r.get("region_label")} {r.get("confidence", "")}', fill=c)
    if show_visual:
        for r in stamp_sig_rows:
            c = VISUAL_COLORS.get(r.get("label"), "#000")
            d.rectangle([r["xmin"], r["ymin"], r["xmax"], r["ymax"]], outline=c, width=4)
            d.text((r["xmin"] + 2, max(0, r["ymin"] - 12)),
                   f'{r.get("label")} {r.get("confidence", "")}', fill=c)
    return img


# ===========================================================================
# View: Live Demo
# ===========================================================================
def view_live_demo(policy: Policy):
    st.title("Live Demo — one invoice, your rules")
    conf = st.slider("Detection confidence threshold", 0.0, 1.0, 0.25, 0.05)

    up = st.file_uploader("Upload an invoice image", type=["png", "jpg", "jpeg", "tif", "tiff"])
    if up is None:
        st.info("Upload an invoice to run the pipeline and see the verdict under your current policy.")
        avail = RS.availability()
        if not any(v for k, v in avail.items() if k.endswith(("predictions", "manifest"))):
            st.caption("⏳ No member outputs on disk yet — live upload still works if model weights "
                       "are in `models/`. The Gallery/Report views fill in as outputs land.")
        return

    pil = Image.open(up).convert("RGB")
    image_bgr = np.array(pil)[:, :, ::-1]

    with st.spinner("Running detectors…"):
        live = run_live(image_bgr, conf)

    show_r = st.checkbox("Show region boxes", value=True)
    show_v = st.checkbox("Show stamp/signature boxes", value=True)

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Detections")
        st.image(draw_overlays(pil, live["stamp_sig_rows"], live["region_rows"], show_r, show_v),
                 width="stretch")
        if not live["vision_available"]:
            st.caption("🔌 stamp/signature model unavailable (no weights in `models/`) — "
                       "those signals are unknown → fail-closed.")
        if not live["region_available"]:
            st.caption("🔌 region model unavailable — region overlay/field-crops disabled.")

    # Build signals. No OCR engine locally (easyocr absent) → reference/date/terms unknown.
    record = {
        "visual_elements": {
            "stamp_detected": any(r["label"] == "stamp" for r in live["stamp_sig_rows"])
            if live["vision_available"] else None,
            "signature_detected": any(r["label"] == "signature" for r in live["stamp_sig_rows"])
            if live["vision_available"] else None,
        },
        "payment_context": {},
    }
    signals = signals_from_record(record, ocr_text=None)

    with right:
        st.subheader("Verdict")
        render_verdict(signals, policy)
        with st.expander("Signals used"):
            st.json(signals)

    st.divider()
    st.download_button("⬇︎ Download signals JSON",
                       data=__import__("json").dumps(signals, indent=2, default=str).encode(),
                       file_name=f"{Path(up.name).stem}_signals.json", mime="application/json")


# ===========================================================================
# View: Batch Gallery
# ===========================================================================
def view_batch(policy: Policy):
    st.title("Batch Gallery — the policy across every invoice")
    records = RS.load_final_records()
    ss_rows = RS.load_stamp_signature()

    if not records and not ss_rows:
        st.warning("⏳ Waiting for member outputs. The batch view needs Hessam's per-invoice JSON "
                   "(`outputs/final_json/…`) or at least Diana's `stamp_signature_predictions.csv`. "
                   "It will populate automatically once you copy the Colab outputs into `outputs/`.")
        _availability_panel()
        return

    ocr_text = RS.invoice_ocr_text()

    # Build a record per invoice if final JSON isn't there yet, from Diana's predictions.
    if not records:
        by_doc = {}
        for r in ss_rows:
            by_doc.setdefault(r["document_id"], []).append(r)
        records = [{
            "document_id": doc,
            "visual_elements": {
                "stamp_detected": any(x["label"] == "stamp" for x in rows),
                "signature_detected": any(x["label"] == "signature" for x in rows),
            },
            "payment_context": {},
        } for doc, rows in by_doc.items()]

    rows = []
    for rec in records:
        doc = rec.get("document_id")
        sig = signals_from_record(rec, ocr_text=ocr_text.get(doc))
        v = evaluate(sig, policy)
        rows.append({"document_id": doc, "ready": v.ready,
                     "passed": v.n_pass, "enabled": v.n_enabled,
                     "stamp": rec.get("visual_elements", {}).get("stamp_detected"),
                     "signature": rec.get("visual_elements", {}).get("signature_detected"),
                     "has_ocr": doc in ocr_text})

    import pandas as pd
    df = pd.DataFrame(rows)
    n_ready = int(df.ready.sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Invoices", len(df))
    c2.metric("Ready under this policy", n_ready)
    c3.metric("Pass rate", f"{100*n_ready/len(df):.0f}%" if len(df) else "—")

    st.caption(f"{int(df.has_ocr.sum())} of {len(df)} invoices have OCR text; reference/date/terms "
               "rules fail-close on the rest (shown honestly, not hidden).")

    filt = st.radio("Show", ["All", "Ready only", "Not ready only"], horizontal=True)
    view_df = df if filt == "All" else df[df.ready == (filt == "Ready only")]
    st.dataframe(view_df, width="stretch", height=320)

    st.download_button("⬇︎ Export passing set (CSV)",
                       data=df[df.ready][["document_id"]].to_csv(index=False).encode(),
                       file_name="passing_invoices.csv", mime="text/csv")

    st.divider()
    st.subheader("Inspect one invoice")
    pick = st.selectbox("document_id", df.document_id.tolist())
    rec = next((r for r in records if r.get("document_id") == pick), None)
    if rec:
        cola, colb = st.columns([1, 1])
        with cola:
            img_path = _invoice_image_path(pick)
            if img_path:
                st.image(str(img_path), width="stretch")
            else:
                st.caption("image not found locally")
        with colb:
            sig = signals_from_record(rec, ocr_text=ocr_text.get(pick))
            render_verdict(sig, policy)


# ===========================================================================
# View: Model Report
# ===========================================================================
def view_report():
    st.title("Model Report — how the detectors performed")
    metrics = RS.load_metrics()
    if not metrics:
        st.warning("⏳ Waiting for member metrics JSONs in `outputs/metrics/`.")
        _availability_panel()
        return

    if "stamp_signature" in metrics:
        st.subheader("Diana — stamp / signature (real held-out split)")
        m = metrics["stamp_signature"]
        cols = st.columns(2)
        for col, cls in zip(cols, ["stamp", "signature"]):
            if cls in m:
                col.metric(f"{cls} — mean IoU", m[cls].get("mean_iou", "—"))
                col.write({k: m[cls][k] for k in ("precision", "recall") if k in m[cls]})
        _run_block(m.get("_run"))

    if "region_iou" in metrics:
        st.subheader("Jordan — region detection (OCR-Dataset test split)")
        m = metrics["region_iou"]
        pc = m.get("per_class", {})
        if pc:
            import pandas as pd
            st.dataframe(pd.DataFrame(pc).T, width="stretch")
        st.write(f"macro mean IoU: **{m.get('macro_mean_iou', '—')}**")
        _run_block(m.get("_run"))

    if "ocr_parameter" in metrics:
        st.subheader("Damir — OCR / parameters")
        m = metrics["ocr_parameter"]
        st.json(m.get("ocr_primary", m))
        _run_block(m.get("_run"))

    # local-CPU vs Colab-GPU comparison from the _run blocks
    runs = [(k, v.get("_run")) for k, v in metrics.items() if isinstance(v, dict) and v.get("_run")]
    if runs:
        st.subheader("Compute profile comparison (from each run's `_run` block)")
        import pandas as pd
        st.dataframe(pd.DataFrame([{"model": k, **rb} for k, rb in runs]), width="stretch")


def _run_block(rb):
    if rb:
        st.caption(f"profile `{rb.get('profile')}` · device {rb.get('device')} · "
                   f"epochs {rb.get('epochs')} · imgsz {rb.get('imgsz')} · "
                   f"{rb.get('wall_clock_sec')}s")


# ===========================================================================
# small shared helpers
# ===========================================================================
def _availability_panel():
    st.subheader("Output availability")
    for k, ok in RS.availability().items():
        st.markdown(f"&nbsp;&nbsp;{'✅' if ok else '⏳'} {k}")


def _invoice_image_path(document_id: str):
    for base in [PATHS.processed_dir / "images", PATHS.repo_root / "inputs" / "images",
                 PATHS.processed_dir]:
        for ext in (".jpg", ".png", ".jpeg"):
            p = base / f"{document_id}{ext}"
            if p.exists():
                return p
    return None


# ===========================================================================
def main():
    policy = sidebar_policy()
    view = st.session_state.get("view", "Live Demo")
    if view == "Live Demo":
        view_live_demo(policy)
    elif view == "Batch Gallery":
        view_batch(policy)
    else:
        view_report()


main()
