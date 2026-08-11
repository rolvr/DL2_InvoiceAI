"""
streamlit_app.py — Invoice Obligation-Readiness demo.

Owner: Hessam. Run with:  streamlit run app/streamlit_app.py

The app's centrepiece is a USER-CONFIGURABLE verdict: the user builds a policy from rules
(visual mark / reference number / invoice-date range / payment-terms days) in the sidebar, and
every invoice is judged Ready / Not-ready against it, with a transparent per-rule breakdown.

Three views:
  • Live Demo    — pick a sample or upload an invoice → annotated image → OCR → verdict → downloads
  • Batch Gallery— apply the policy across all invoices → "N of M pass" → filter → drilldown
  • Model Report — the members' real metrics + obligation-readiness-by-policy summary

CPU-only, no GPU. All three detectors (region / stamp / signature) are real trained YOLO models
loaded from `models/`; OCR is EasyOCR run on CPU, cached after first load.

Performance: the Batch Gallery's per-invoice signals (visual marks + OCR-derived reference/date/
terms) are POLICY-INDEPENDENT, so they are computed once and cached with `st.cache_data`. Only
`verdict_engine.evaluate()` — pure, cheap rule logic — re-runs when a policy rule is toggled, so
the "N/750 ready" readout updates near-instantly instead of re-deriving OCR signals every time.

Fail-closed: any enabled rule without a signal counts as a fail.
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import results_store as RS  # noqa: E402
from src import policy_store  # noqa: E402
from src.config import load_required_fields, PATHS  # noqa: E402
from src.streamlit_helpers import (  # noqa: E402
    build_html_report, image_to_base64_png, signals_from_record, to_downloadable_json,
)
from src.verdict_engine import (  # noqa: E402
    DateRangeRule, PaymentTermsRule, Policy, ReferenceRule, VisualRule, evaluate, preset_policies,
)
from src import completeness as CP  # noqa: E402

st.set_page_config(page_title="Invoice Obligation-Readiness", layout="wide", page_icon="🧾")

REGION_COLORS = {
    "company": "#e45756", "date": "#54a24b", "address": "#f58518",
    "total": "#7c4dff", "other_text": "#9e9e9e",
}
VISUAL_COLORS = {"stamp": "#e45756", "signature": "#4c78a8"}
SAMPLE_DIR = REPO_ROOT / "app" / "sample_invoices"


# ===========================================================================
# Sidebar — navigation + the verdict policy builder
# ===========================================================================
def sidebar_policy() -> Policy:
    st.sidebar.title("🧾 Obligation-Readiness")
    view = st.sidebar.radio("View", ["Showcase", "Live Demo", "Batch Gallery", "Completeness", "Model Report"])
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

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh cached batch data", width="stretch",
                         help="Clears the cached per-invoice signals (use if outputs/ changed on disk)."):
        _batch_signal_table.clear()
        st.sidebar.success("Cache cleared — will recompute on next view of Batch Gallery / Model Report.")

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


@st.cache_resource(show_spinner="Loading EasyOCR (first time only — downloads/loads CPU weights)…")
def _load_easyocr_reader():
    import easyocr
    return easyocr.Reader(["en"], gpu=False, verbose=False)


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


def run_live_ocr(image_bgr: np.ndarray, target_width: int = 700) -> str | None:
    """Run EasyOCR (CPU) over the (downscaled, for speed) full page and return the combined
    text, or None if the OCR engine is unavailable / fails — the caller should treat that as
    'unknown' and let the verdict fail-closed on the reference/date/terms rules.

    Downscaling to ~700px wide keeps a full-page CPU EasyOCR pass to ~15-20s instead of ~90s,
    while still recovering header/body text well enough for reference-number and date matching.
    """
    try:
        reader = _load_easyocr_reader()
        h, w = image_bgr.shape[:2]
        if w > target_width:
            scale = target_width / w
            small = cv2.resize(image_bgr, (int(w * scale), int(h * scale)))
        else:
            small = image_bgr
        results = reader.readtext(small, detail=0, paragraph=True)
        text = " ".join(results).strip()
        return text or None
    except Exception as e:
        st.info(f"🔌 OCR unavailable ({e}) — reference/date/terms signals are unknown → fail-closed.")
        return None


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

    sample_files = sorted(
        p.name for p in SAMPLE_DIR.glob("*")
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    ) if SAMPLE_DIR.exists() else []

    pick_col, up_col = st.columns([1, 1])
    with pick_col:
        picked = st.selectbox("Pick a sample invoice (no file dialog needed)",
                              ["— none —"] + sample_files)
    with up_col:
        up = st.file_uploader("…or upload your own", type=["png", "jpg", "jpeg", "tif", "tiff"])

    if up is not None:
        pil = Image.open(up).convert("RGB")
        image_name = up.name
    elif picked != "— none —":
        pil = Image.open(SAMPLE_DIR / picked).convert("RGB")
        image_name = picked
    else:
        st.info("Pick a sample above or upload an invoice to run the pipeline and see the "
                "verdict under your current policy.")
        avail = RS.availability()
        if not any(v for k, v in avail.items() if k.endswith(("predictions", "manifest"))):
            st.caption("⏳ No member outputs on disk yet — live upload still works if model weights "
                       "are in `models/`. The Gallery/Report views fill in as outputs land.")
        return

    image_bgr = np.array(pil)[:, :, ::-1]

    with st.spinner("Running detectors (region + stamp/signature, CPU)…"):
        live = run_live(image_bgr, conf)

    show_r = st.checkbox("Show region boxes", value=True)
    show_v = st.checkbox("Show stamp/signature boxes", value=True)
    annotated = draw_overlays(pil, live["stamp_sig_rows"], live["region_rows"], show_r, show_v)

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Detections")
        st.image(annotated, width="stretch")
        if not live["vision_available"]:
            st.caption("🔌 stamp/signature model unavailable (no weights in `models/`) — "
                       "those signals are unknown → fail-closed.")
        if not live["region_available"]:
            st.caption("🔌 region model unavailable — region overlay/field-crops disabled.")
        n_stamp = sum(1 for r in live["stamp_sig_rows"] if r["label"] == "stamp")
        n_sig = sum(1 for r in live["stamp_sig_rows"] if r["label"] == "signature")
        st.caption(f"{n_stamp} stamp box(es), {n_sig} signature box(es), "
                   f"{len(live['region_rows'])} region box(es) detected.")

    run_ocr_flag = st.checkbox(
        "Run OCR (EasyOCR, CPU — ~15–20s on a full page) to enable reference/date/terms rules",
        value=True,
        help="Without OCR text, the reference/date/payment-terms rules have no signal and "
             "fail-closed (shown as 'unknown'). This is the only step slow enough to need a spinner.",
    )
    ocr_text = None
    if run_ocr_flag:
        t0 = time.time()
        with st.spinner("Running OCR (EasyOCR, CPU)… this can take ~15–20s on a full page"):
            ocr_text = run_live_ocr(image_bgr)
        ocr_elapsed = time.time() - t0
        if ocr_text:
            st.caption(f"OCR finished in {ocr_elapsed:.1f}s.")
            with st.expander("Extracted OCR text"):
                st.text(ocr_text)

    record = {
        "visual_elements": {
            "stamp_detected": any(r["label"] == "stamp" for r in live["stamp_sig_rows"])
            if live["vision_available"] else None,
            "signature_detected": any(r["label"] == "signature" for r in live["stamp_sig_rows"])
            if live["vision_available"] else None,
        },
        "payment_context": {},
    }
    signals = signals_from_record(record, ocr_text=ocr_text)

    with right:
        st.subheader("Verdict")
        v = render_verdict(signals, policy)
        with st.expander("Signals used"):
            st.json(signals)

    st.divider()
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button("⬇︎ Download signals JSON",
                           data=to_downloadable_json(signals),
                           file_name=f"{Path(image_name).stem}_signals.json", mime="application/json")
    with dl2:
        report_html = build_html_report(
            document_id=image_name,
            signals=signals,
            verdict=v.as_dict(),
            image_b64=image_to_base64_png(annotated),
            extracted_text=ocr_text,
            detections={
                "confidence_threshold": conf,
                "region_model_available": live["region_available"],
                "stamp_signature_model_available": live["vision_available"],
                "ocr_ran": run_ocr_flag,
                "policy": policy.name,
                "device": "cpu",
            },
        )
        st.download_button("⬇︎ Download HTML report", data=report_html.encode("utf-8"),
                           file_name=f"{Path(image_name).stem}_report.html", mime="text/html")


# ===========================================================================
# Batch signal computation — cached (policy-independent) so policy toggles are instant.
# ===========================================================================
@st.cache_data(show_spinner="Computing per-invoice signals across the batch (first time only — cached after)…")
def _batch_signal_table() -> pd.DataFrame:
    """document_id -> {signals, stamp, signature, has_ocr}, for every invoice with SOME output.

    This is the expensive part (OCR-text-derived reference/date/terms parsing across ~750
    invoices, ~5-6s) and it does NOT depend on the verdict policy, so it is cached with
    `st.cache_data`: computed once per session, then every policy-rule toggle only re-runs the
    cheap, pure `verdict_engine.evaluate()` over the cached table (~0.05s for 750 rows).
    """
    records = RS.load_final_records()
    ss_rows = RS.load_stamp_signature()

    if not records:
        by_doc: dict[str, list[dict]] = {}
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

    if not records:
        # Last-resort: build the invoice list from Damir's OCR outputs (or the manifest) so the
        # batch views work with just ocr_outputs.csv — no final_json or Diana preds required.
        # Visual marks are unknown here → the verdict engine fails-closed on visual rules.
        ocr_docs = [str(r.get("document_id", "")).strip() for r in RS.load_ocr_outputs()
                    if str(r.get("source", "")).startswith("invoice") and r.get("document_id")]
        docs = list(dict.fromkeys(ocr_docs)) or \
            [str(r.get("document_id")) for r in RS.load_manifest() if r.get("document_id")]
        records = [{"document_id": d,
                    "visual_elements": {"stamp_detected": None, "signature_detected": None},
                    "payment_context": {}} for d in docs]

    ocr_text = RS.invoice_ocr_text()
    rows = []
    for rec in records:
        doc = rec.get("document_id")
        sig = signals_from_record(rec, ocr_text=ocr_text.get(doc))
        rows.append({
            "document_id": doc,
            "signals": sig,
            "stamp": rec.get("visual_elements", {}).get("stamp_detected"),
            "signature": rec.get("visual_elements", {}).get("signature_detected"),
            "has_ocr": doc in ocr_text,
        })
    return pd.DataFrame(rows)


def _apply_policy(table: pd.DataFrame, policy: Policy) -> pd.DataFrame:
    """Cheap, uncached: just runs evaluate() per row against the current policy."""
    rows = []
    for row in table.itertuples(index=False):
        v = evaluate(row.signals, policy)
        rows.append({"document_id": row.document_id, "ready": v.ready,
                     "passed": v.n_pass, "enabled": v.n_enabled,
                     "stamp": row.stamp, "signature": row.signature, "has_ocr": row.has_ocr})
    return pd.DataFrame(rows)


# ===========================================================================
# View: Batch Gallery
# ===========================================================================
def view_batch(policy: Policy):
    st.title("Batch Gallery — the policy across every invoice")

    if not (RS.availability()["final_json"] or RS.load_stamp_signature() or RS.load_ocr_outputs()):
        st.warning("⏳ Waiting for member outputs. The batch view needs Hessam's per-invoice JSON "
                   "(`outputs/final_json/…`), Diana's `stamp_signature_predictions.csv`, or at least "
                   "Damir's `ocr_outputs.csv` in `outputs/predictions/`.")
        _availability_panel()
        return

    t0 = time.time()
    table = _batch_signal_table()
    df = _apply_policy(table, policy)
    elapsed = time.time() - t0

    n_ready = int(df.ready.sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Invoices", len(df))
    c2.metric("Ready under this policy", n_ready)
    c3.metric("Pass rate", f"{100*n_ready/len(df):.0f}%" if len(df) else "—")
    c4.metric("Re-render time", f"{elapsed*1000:.0f} ms")

    st.caption(f"{int(df.has_ocr.sum())} of {len(df)} invoices have OCR text; reference/date/terms "
               "rules fail-close on the rest (shown honestly, not hidden). Toggling a rule in the "
               "sidebar only re-evaluates cached signals, so this view updates near-instantly.")
    st.caption("Honest note: with the **Strict** preset (visual mark required), readiness is "
               "**0/750** — this invoice corpus is clean, unsigned digital templates, not a "
               "detector failure (Diana's stamp/signature detector scores IoU 0.82/0.81 on its "
               "own held-out, non-invoice split).")

    filt = st.radio("Show", ["All", "Ready only", "Not ready only"], horizontal=True)
    view_df = df if filt == "All" else df[df.ready == (filt == "Ready only")]
    st.dataframe(view_df, width="stretch", height=320)

    st.download_button("⬇︎ Export passing set (CSV)",
                       data=df[df.ready][["document_id"]].to_csv(index=False).encode(),
                       file_name="passing_invoices.csv", mime="text/csv")

    st.divider()
    st.subheader("Inspect one invoice")
    pick = st.selectbox("document_id", df.document_id.tolist())
    sig_row = table[table.document_id == pick]
    if not sig_row.empty:
        cola, colb = st.columns([1, 1])
        with cola:
            img_path = _invoice_image_path(pick)
            if img_path:
                st.image(str(img_path), width="stretch")
            else:
                st.caption("image not found locally")
        with colb:
            sig = sig_row.iloc[0]["signals"]
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
            st.dataframe(pd.DataFrame(pc).T, width="stretch")
        st.write(f"macro mean IoU: **{m.get('macro_mean_iou', '—')}**")
        _run_block(m.get("_run"))

    if "ocr_parameter" in metrics:
        st.subheader("Damir — OCR / parameters")
        m = metrics["ocr_parameter"]
        primary = m.get("ocr_primary", {})
        if primary:
            oc1, oc2, oc3, oc4 = st.columns(4)
            oc1.metric("CER (mean)", primary.get("cer_mean", "—"))
            oc2.metric("CER (median)", primary.get("cer_median", "—"))
            oc3.metric("WER (mean)", primary.get("wer_mean", "—"))
            oc4.metric("WER (median)", primary.get("wer_median", "—"))
        with st.expander("Full OCR / parameter metrics JSON"):
            st.json(m)
        _run_block(m.get("_run"))

    # --- readiness-by-policy summary (reuses the same cached signal table as Batch Gallery) ---
    st.divider()
    st.subheader("Obligation-readiness by policy (whole batch)")
    if RS.availability()["final_json"] or RS.load_stamp_signature():
        table = _batch_signal_table()
        presets = preset_policies()
        N = len(table)
        ready_by_preset = {}
        for name, pol in presets.items():
            df = _apply_policy(table, pol)
            ready_by_preset[name] = int(df.ready.sum())

        summary_df = pd.DataFrame([
            {"Policy": name, "Ready": r, "Total": N, "%": round(100 * r / N, 1) if N else 0.0}
            for name, r in ready_by_preset.items()
        ])
        rc1, rc2 = st.columns([1, 1.4])
        with rc1:
            st.dataframe(summary_df, hide_index=True, width="stretch")
            st.caption("Strict = 0 is honest: the corpus is unsigned digital templates and Strict "
                       "requires a visual mark. Not a model bug — see Diana's metrics above.")
        with rc2:
            _readiness_chart(ready_by_preset, N)
    else:
        st.caption("⏳ No invoice-level outputs yet to summarize readiness across.")

    # local-CPU vs Colab-GPU comparison from the _run blocks
    runs = [(k, v.get("_run")) for k, v in metrics.items() if isinstance(v, dict) and v.get("_run")]
    if runs:
        st.subheader("Compute profile comparison (from each run's `_run` block)")
        st.dataframe(pd.DataFrame([{"model": k, **rb} for k, rb in runs]), width="stretch")


def _readiness_chart(ready_by_preset: dict, N: int):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = ["Lenient", "Default", "Strict"]
    colors = {"Lenient": "#0ca30c", "Default": "#eda100", "Strict": "#d03b3b"}
    names = [n for n in order if n in ready_by_preset] + [n for n in ready_by_preset if n not in order]
    vals = [ready_by_preset[n] for n in names]
    pct = [100 * v / N if N else 0 for v in vals]

    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    bars = ax.bar(names, pct, color=[colors.get(n, "#4c78a8") for n in names], width=0.55, zorder=3)
    for b, v, p in zip(bars, vals, pct):
        ax.annotate(f"{p:.1f}%\n({v}/{N})", xy=(b.get_x() + b.get_width() / 2, b.get_height()),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Ready (%)")
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")


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
# View: Completeness (graded readiness — notebook 06 rubric, via src/completeness.py)
# ===========================================================================
@st.cache_data(show_spinner="Scoring completeness across the batch (first time only — cached)…")
def _completeness_table() -> pd.DataFrame:
    """Graded completeness per invoice. Self-sufficient: builds the invoice list + OCR text from
    Damir's ocr_outputs.csv (invoice rows), regions from Jordan's region_predictions.csv, and
    derives reference/date/terms with the shared helpers. Does NOT require Hessam's final_json."""
    from src.streamlit_helpers import derive_reference_signals, derive_terms_signals

    ocr_by_doc, conf_by_doc = {}, {}
    for r in RS.load_ocr_outputs():
        if not str(r.get("source", "")).startswith("invoice"):
            continue
        d = str(r.get("document_id", "")).strip()
        if not d:
            continue
        t = r.get("ocr_text")
        ocr_by_doc.setdefault(d, t if isinstance(t, str) else "")
        conf_by_doc.setdefault(d, r.get("mean_confidence"))

    docs = list(ocr_by_doc) or [str(r.get("document_id")) for r in RS.load_manifest() if r.get("document_id")]
    if not docs:
        return pd.DataFrame()

    reg_by_doc = {}
    for r in RS.load_regions():
        if "source" in r and str(r.get("source", "")) not in ("", "invoice"):
            continue
        d, lbl = r.get("document_id"), r.get("region_label")
        if d and lbl:
            reg_by_doc.setdefault(d, set()).add(lbl)

    ss_by_doc = {}
    for r in RS.load_stamp_signature():
        ss_by_doc.setdefault(r.get("document_id"), set()).add(r.get("label"))

    rows = []
    for d in docs:
        txt = ocr_by_doc.get(d, "")
        terms = derive_terms_signals(txt)
        sig = {
            "stamp_detected": "stamp" in ss_by_doc.get(d, set()),
            "signature_detected": "signature" in ss_by_doc.get(d, set()),
            "references": derive_reference_signals(txt),
            "invoice_date": terms.get("invoice_date"),
            "billing_due_days": terms.get("billing_due_days"),
            "payment_terms": terms.get("payment_terms"),
        }
        res = CP.score(sig, reg_by_doc.get(d, set()), txt, conf_by_doc.get(d))
        rows.append({"document_id": d, **res})
    return pd.DataFrame(rows)


def view_completeness():
    st.title("Completeness Score — graded obligation-readiness")
    st.caption(
        "A complement to the strict pass/fail verdict. Instead of one hard gate (which is ~0% on "
        "this corpus with no PO/contract references), each invoice is scored on how many core "
        "obligation fields it actually has — **total 25 · date 20 · reference 20 · counterparty 20 "
        "· readable 15** (+bonus payment-terms/visual 10 each). **Ready ≥ 80 · Needs review 60–79 "
        "· Not ready < 60.** Fail-closed; the reference slot requires a real digit-bearing invoice "
        "number and is capped at 20/100 so it can't dominate.")

    if not (RS.load_ocr_outputs() or RS.load_regions()):
        st.warning("⏳ Needs Damir's `ocr_outputs.csv` and/or Jordan's `region_predictions.csv` in "
                   "`outputs/predictions/`. Add those two files and reload.")
        _availability_panel()
        return

    df = _completeness_table()
    if df.empty:
        st.warning("No invoices to score yet.")
        return

    order = ["Ready", "Needs review", "Not ready"]
    counts = df.tier.value_counts().reindex(order).fillna(0).astype(int)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Invoices scored", len(df))
    c2.metric("Ready (≥80)", f"{int(counts['Ready'])} ({100*counts['Ready']/len(df):.0f}%)")
    c3.metric("Needs review", f"{int(counts['Needs review'])} ({100*counts['Needs review']/len(df):.0f}%)")
    c4.metric("Mean score", f"{df.score.mean():.1f}/100")

    st.bar_chart(counts)
    st.caption("Honest note: on this corpus date/reference/readable are near-universal, so the tier "
               "is effectively driven by whether the region detector found a **total** and a "
               "**counterparty** — the per-field breakdown below shows exactly why each invoice scored.")

    filt = st.radio("Show", ["All"] + order, horizontal=True)
    view_df = df if filt == "All" else df[df.tier == filt]
    st.dataframe(view_df, width="stretch", height=340)
    st.download_button("⬇︎ Export completeness scores (CSV)",
                       data=df.to_csv(index=False).encode(),
                       file_name="readiness_completeness_scores.csv", mime="text/csv")

    st.divider()
    st.subheader("Inspect one invoice")
    pick = st.selectbox("document_id", df.document_id.tolist())
    st.json(df[df.document_id == pick].iloc[0].to_dict())


# ===========================================================================
# View: Showcase — one invoice, both readiness views. Self-contained (weights only).
# ===========================================================================
def view_showcase():
    st.title("🧾 Invoice Obligation-Readiness — Showcase")
    st.caption(
        "Pick a sample invoice (or upload one). The app detects regions + stamp/signature, reads "
        "the text, and shows **both** readiness views — the strict rule-based policies **and** the "
        "graded completeness score. Self-contained: needs only the model weights in `models/` "
        "(no batch data) — this is the view to deploy.")

    conf = st.slider("Detection confidence threshold", 0.0, 1.0, 0.25, 0.05)
    samples = sorted(
        p.name for p in SAMPLE_DIR.glob("*")
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    ) if SAMPLE_DIR.exists() else []

    c1, c2 = st.columns(2)
    picked = c1.selectbox("Sample invoice", ["— none —"] + samples)
    up = c2.file_uploader("…or upload your own", type=["png", "jpg", "jpeg", "tif", "tiff"])

    if up is not None:
        pil, name = Image.open(up).convert("RGB"), up.name
    elif picked != "— none —":
        pil, name = Image.open(SAMPLE_DIR / picked).convert("RGB"), picked
    else:
        st.info("Pick a sample above or upload an invoice to run the full pipeline.")
        return

    image_bgr = np.array(pil)[:, :, ::-1]
    with st.spinner("Detecting regions + stamp/signature and reading text (CPU)…"):
        live = run_live(image_bgr, conf)
        ocr_text = run_live_ocr(image_bgr)

    annotated = draw_overlays(pil, live["stamp_sig_rows"], live["region_rows"], True, True)
    record = {
        "visual_elements": {
            "stamp_detected": (any(r["label"] == "stamp" for r in live["stamp_sig_rows"])
                               if live["vision_available"] else None),
            "signature_detected": (any(r["label"] == "signature" for r in live["stamp_sig_rows"])
                                   if live["vision_available"] else None),
        },
        "payment_context": {},
    }
    signals = signals_from_record(record, ocr_text=ocr_text)
    region_labels = {r.get("region_label") for r in live["region_rows"]}
    comp = CP.score(signals, region_labels, ocr_text or "", None)

    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Detected")
        st.image(annotated, width="stretch")
        n_stamp = sum(1 for r in live["stamp_sig_rows"] if r["label"] == "stamp")
        n_sig = sum(1 for r in live["stamp_sig_rows"] if r["label"] == "signature")
        st.caption(f"{len(live['region_rows'])} region box(es) · {n_stamp} stamp · {n_sig} signature"
                   + ("" if live["region_available"] else "  ⚠️ region weights missing from models/")
                   + ("" if live["vision_available"] else "  ⚠️ stamp/signature weights missing from models/"))
        with st.expander("Extracted OCR text"):
            st.text(ocr_text or "(no text)")

    with right:
        st.subheader("① Graded completeness")
        st.progress(comp["score"] / 100.0)
        st.metric("Score", f"{comp['score']} / 100", comp["tier"])
        for k, lbl in [("total", "Total / amount"), ("date", "Date"), ("reference", "Reference no."),
                       ("counterparty", "Counterparty"), ("readable", "Readable OCR")]:
            st.markdown(f"&nbsp;&nbsp;{'✅' if comp['has_' + k] else '❌'} {lbl}", unsafe_allow_html=True)
        if comp["reference_match"]:
            st.caption(f"reference matched: `{comp['reference_match']}`")

        st.divider()
        st.subheader("② Strict policies (fail-closed)")
        for pname, pol in preset_policies().items():
            v = evaluate(signals, pol)
            st.markdown(f"{'✅' if v.ready else '⛔'} **{pname}** — "
                        f"{'Ready' if v.ready else 'Not ready'} ({v.n_pass}/{v.n_enabled} rules)")
        with st.expander("Signals used"):
            st.json(signals)

    st.divider()
    dl1, dl2 = st.columns(2)
    payload = {"document_id": name, "completeness": comp, "signals": signals,
               "strict_policies": {n: evaluate(signals, p).as_dict() for n, p in preset_policies().items()}}
    dl1.download_button("⬇︎ Download result JSON", data=to_downloadable_json(payload),
                        file_name=f"{Path(name).stem}_showcase.json", mime="application/json")


# ===========================================================================
def main():
    import os
    # Deployed demo: set DL2_SHOWCASE_ONLY=1 to show ONLY the Showcase tab (no batch data needed).
    if os.environ.get("DL2_SHOWCASE_ONLY", "").strip().lower() in ("1", "true", "yes"):
        st.sidebar.title("🧾 Obligation-Readiness")
        st.sidebar.caption("Deployed demo — upload or pick an invoice.")
        view_showcase()
        return
    policy = sidebar_policy()
    view = st.session_state.get("view", "Showcase")
    if view == "Showcase":
        view_showcase()
    elif view == "Live Demo":
        view_live_demo(policy)
    elif view == "Batch Gallery":
        view_batch(policy)
    elif view == "Completeness":
        view_completeness()
    else:
        view_report()


main()
