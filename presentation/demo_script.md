# Demo Script

**Presenter: Hessam. Run `streamlit run app/streamlit_app.py` before the presentation starts
and keep the app open in a browser tab.**

## Setup checklist (do before presenting)

- [ ] `outputs/` contains fresh predictions/metrics from all four member notebooks.
- [ ] `app/sample_invoices/` has 2-3 representative invoice images ready to upload
      (pick one clean example and one messier/edge-case example).
- [ ] Streamlit app launches with no errors, sidebar controls are visible.

## Script

1. **Open with the business question** (30s): "Given an invoice image, can we automatically
   tell whether it's ready to become a structured obligation record — does it have a
   signature or stamp, the right regions, the right reference numbers, clear payment terms?"

2. **Upload the clean example invoice** (1 min). Narrate as the app processes:
   - Point out the uploaded image on the left.
   - Point out "Visual elements" — stamp/signature detected or not.
   - Point out "Detected regions" — line items, totals, payment terms, terms & conditions,
     reference numbers.

3. **Show required parameters** (1 min): scroll to "Required parameters" — PO Reference,
   Order Number, etc. — check/cross marks. Mention the sidebar lets you add a custom field
   (e.g. type "Insurance Cert" with a keyword) live.

4. **Show payment context & terms extraction** (1 min): due date, payment terms (e.g. "Net
   30"), and any late-payment/dispute/penalty clause flags pulled from the terms & conditions
   region.

5. **Show the Pistac.io readiness verdict** (30s): green "ready" banner or the missing-fields
   warning, plus risk flags.

6. **Show the full JSON + download button** (30s): this is the structured record that would
   feed a downstream Pistac.io-style workflow.

7. **Upload the messier/edge-case example** (1 min): show how missing regions / low-confidence
   detections surface as "not detected" / "missing" rather than silently failing — emphasize
   this transparency is deliberate.

8. **Wrap with metrics** (30s): mention the mean IoU numbers and stamp/signature precision/
   recall from `outputs/metrics/*.json` as the quantitative backing for what was just shown
   qualitatively.

Total: ~6 minutes, leaving room for Q&A.
