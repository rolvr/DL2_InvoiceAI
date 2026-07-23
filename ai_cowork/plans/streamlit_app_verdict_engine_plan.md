# Streamlit App — Configurable Invoice Obligation-Readiness Demo

## Context

The pipeline (Rolando ingest → Diana stamp/signature → Jordan regions → Damir OCR/params/terms →
Hessam integration) is running on Colab; members publish outputs to Drive within ~1–3h. This plan
is the final phase: the demo app (`app/streamlit_app.py`, owned by Hessam). A working stub already
exists, fully wired to the `src/` modules and the final-JSON schema, so this is an **upgrade in
place**, not a greenfield build.

**Central requirement (from the user):** the "ready / not-ready" verdict must be **user-configurable**.
The user builds a policy from rules *before* judging an invoice. This generalizes the currently
fixed `src/final_json_builder.py:build_pistacio_readiness()` into a user-defined rule engine. The
app should serve both a business audience (product-like Live Demo + verdict) and a grader
(technical Model Report) — **balanced framing**.

## Key architectural insight

The pipeline **extracts signals**; the user's policy **is applied to those signals**. They separate
cleanly, and every signal the verdict rules need ALREADY exists in member outputs:

| Verdict rule | Signal (already produced) | Source |
|---|---|---|
| stamp / signature present | `visual_elements.stamp_detected / signature_detected` | Diana |
| PO / Order / Contract / Work-Order no. present | `required_parameters[...]` (`config/required_fields_config.json`) | Damir |
| invoice date in range | `payment_context.invoice_date` | Damir |
| payment terms > N days | `payment_context.billing_due_days` | Damir |

The verdict depends on Diana's + Damir's signals, **not** Jordan's region labels — so the known
region-label↔schema mismatch (Jordan emits receipt entities company/date/address/total, while
`config/label_schema.json` expects obligation regions) is **off the verdict critical path**. It
affects only a "detected regions" display panel, not the Ready/Not-ready decision.

## CONSTRAINT: notebooks 2–4 are FROZEN (verified against colab/bundle/gen_colab_notebooks.py)

Cannot change Diana/Jordan/Damir notebooks. What they actually produce keyed to the **750 real
invoices**:
- **Diana** `stamp_signature_predictions.csv` — invoice-keyed (`document_id`), all 750. ✅
- **Jordan** `region_predictions.csv` — rows with `source="invoice"`, invoice-keyed, all 750
  (labels company/date/address/total/other_text). ✅
- **Damir** — `parameter_presence_results.csv` + `terms_extraction_results.csv` are keyed to the
  **OCR-dataset RECEIPT `file_id`s** (e.g. X00016469612), fields `has_company/has_date/has_total/
  has_address` — NOT the 750 invoices, NOT PO/Contract/Work-Order. Damir's only invoice-keyed output
  is **raw OCR text for ~120 batch_1 invoices** (`source="invoice_batch1"` in `ocr_outputs.csv`).
- **Annotation CSVs** (`inputs/annotations/batch1_*.csv`) — real structured GT for ~197 invoices:
  `Json Data{invoice, items, subtotal, payment_instructions}` + `OCRed Text`.

### Consequence for the verdict rules — signals must be RE-SOURCED at integration (nb05 + app, ours)

| Rule | Signal source (frozen-notebook reality) | Coverage |
|---|---|---|
| stamp / signature | Diana, direct | **750/750** |
| reference PO/Contract/Work-Order | DERIVE: run `src/parameter_checker.py` on Damir invoice OCR text + annotation `OCRed Text` | ~120–197 |
| invoice date in range | DERIVE: Jordan `date`-region crop→OCR, or annotation `Json Data` | subset |
| payment terms > N days | DERIVE: annotation `payment_instructions` | WEAKEST — may barely exist → removal candidate |

- Do NOT read Damir's `parameter_presence_results.csv` / `terms_extraction_results.csv` for the
  invoice verdict — they describe the receipt dataset, not the 750.
- **Upload (hybrid live) path** runs OCR + parameter_checker + terms_extraction, so all enabled
  rules work live for a new invoice. **Batch path** has full coverage only for the visual rule; the
  others cover the OCR'd/annotated subset, rest shown "not evaluated (no OCR)".

### Jordan region-label use case (chosen): region-guided field extraction
Crop Jordan's `date`/`total`/`company` boxes and OCR just those regions → structured values +
a Live-Demo overlay ("where the key fields are + what they say"). The `date` crop feeds the verdict
date rule; `total` feeds an amount display. This is the concrete use for Jordan's output in the app.

## Decisions locked (all confirmed with user)

1. **Configurable verdict engine** — user sets rules; verdict = judged against them.
2. **Scope: BOTH single + batch** — rules set once → live verdict + per-rule breakdown on one
   invoice, AND a roll-up across all 750 ("N of 750 pass", filter gallery by pass/fail).
3. **Rule logic: per-rule enable toggle; all ENABLED rules AND-ed.** Within a rule the AND/OR the
   user described still applies (stamp OR/AND signature; any-of the reference types).
4. **Execution: HYBRID** — gallery + roll-up read pre-computed published results; a brand-new
   upload runs live models IF `best.pt` weights are in `models/`, else runs OCR/params/terms (CPU)
   and marks vision signals "model unavailable". The verdict engine runs on whatever signals exist.
5. **Extra features in scope:** save/load named policies; export the passing set; per-invoice
   PDF/JSON report. (Side-by-side compare: out of scope for v1.)
6. **Framing: balanced** — business on Live Demo/verdict, technical depth on Model Report.
7. **Rule set: all 4** — visual + reference + date + payment-terms. Signals derived at integration
   from OCR text + annotation CSVs (see frozen-notebook table). Full on upload path; batch shows
   full coverage for visual, subset coverage for the others.
8. **Missing-signal handling: FAIL-CLOSED.** An enabled rule with no signal for an invoice =
   NOT CONFIRMED = counts as fail → invoice NOT READY. Shown transparently in the breakdown as
   "unknown — treated as fail", never silent. (A readiness gate must not pass what it can't confirm.)

## The verdict rule builder (v1 rule set)

```
┌─ VERDICT POLICY ─────────────────────────────┐   policy: [ Strict ▾ ] [Save] [Load]
│ ☑ Visual mark   (•) stamp OR signature         │
│                 ( ) stamp AND signature        │
│                 ( ) stamp only  ( ) signature  │
│ ☑ Reference no. ☑ PO ☑ Contract ☑ Work order   │
│                 → at least one present (any-of)│
│ ☐ Invoice date  between [start] – [end]        │
│ ☑ Payment terms  due  [ > ▾ ]  [ 30 ] days     │
└──────────────────────────────────────────────┘
   Verdict = AND of enabled rules → ● READY / ○ NOT READY
   ✅ stamp OR signature   (stamp, conf 0.88)
   ✅ reference present     (PO-4471)
   ❌ payment terms > 30d   (found: 14 days)
```

## Implementation

### 1. New module `src/verdict_engine.py` (the heart of the app)
- `Rule` types: `VisualRule(mode: stamp|signature|either|both)`, `ReferenceRule(fields: list, mode=any)`,
  `DateRangeRule(start, end)`, `PaymentTermsRule(op: >|>=|<|<=, days: int)`. Each has `enabled: bool`.
- `Policy` = ordered list of rules + a name; (de)serializable to JSON.
- `evaluate(signals: dict, policy: Policy) -> VerdictResult` returning
  `{ready: bool, rules: [{name, enabled, status: pass|fail|unknown, found_value, explanation}]}` —
  AND of enabled rules. **Fail-closed:** a missing signal → `status="unknown"` which counts as fail;
  the invoice is NOT READY and the breakdown says "unknown — treated as fail".
- Keep `build_pistacio_readiness()` intact (the final-JSON contract still needs its default
  `pistacio_readiness` block); the engine is a **UI-layer policy on top**, not a schema change.
- Unit-testable without Streamlit (mirror the pattern of the existing logic-only src/ modules).

### 1b. Integration signal derivation (`src/streamlit_helpers.py` / nb05 — because Damir's CSVs are receipt-keyed)
- `derive_invoice_signals(document_id, ocr_text, annotation_row) -> dict` producing the 4 signal
  groups for the 750 invoices: stamp/sig from Diana; reference presence via `src/parameter_checker.py`
  on OCR text / annotation `OCRed Text`; invoice date from annotation `Json Data` or Jordan `date`-crop
  OCR; payment days from annotation `payment_instructions` via `src/terms_extraction.py`.
- Where no OCR/annotation exists for an invoice, the reference/date/terms signals are absent →
  fail-closed at evaluate time. Batch view labels these "not evaluated (no OCR)".

### 2. Signal extraction (`src/streamlit_helpers.py`)
- `signals_from_record(final_json: dict) -> dict` — pull the 4 signal groups from a published
  per-invoice JSON (gallery/batch path).
- `signals_from_upload(...)` — reuse `run_full_pipeline`; wire its two TODO placeholders
  (`region_rows`, `stamp_sig_rows`) to load `models/*/best.pt` via ultralytics when present, else
  return empty + a `vision_available=False` flag. OCR/params/terms already work on CPU.
- `load_published_results()` — read `outputs/final_json/sample_invoice_outputs/*.json`,
  `outputs/predictions/*.csv`, `outputs/metrics/*.json` (the local copies the user syncs from Drive),
  cached with `st.cache_data`.

### 3. App rebuild `app/streamlit_app.py` — sidebar policy builder + 3 views
- **Sidebar:** the verdict policy builder (above) + save/load named policies + confidence slider.
- **Live Demo:** upload or pick → annotated image (region boxes + stamp/sig boxes, layer toggles,
  confidence re-filter) → verdict card + per-rule breakdown → payment/terms panel → downloads
  (JSON always; per-invoice PDF report). Business framing.
- **Batch Gallery:** grid/table of the 750 with pre-computed results; **roll-up count** "N of 750
  pass this policy"; filter by pass/fail, split, has-stamp; click → drilldown; **export passing set**
  (CSV of document_ids + combined JSON).
- **Model Report:** per-member metrics (Diana P/R/IoU, Jordan region IoU, Damir CER/WER) + the
  local_cpu-vs-colab_gpu comparison charts from the `_run` blocks + members' published figures.
  Technical framing.

### 4. Supporting changes
- `config/required_fields_config.json` — add **Work Order No.** reference field (keywords/patterns),
  same shape as existing PO/Order/Contract entries.
- `config/verdict_policies.json` (new) — persisted named policies (ships with 2 presets:
  "Strict", "Lenient").
- Per-invoice **PDF report**: lightweight (reportlab or HTML-string → download); JSON download stays.
- `presentation/demo_script.md` — update to the new flow (build a policy → single verdict →
  batch roll-up → export).
- `app/sample_invoices/` — drop 2–3 representative images for the demo.

### 5. Data the app expects locally (user syncs these from Drive after members finish)
- `outputs/final_json/sample_invoice_outputs/*.json` (gallery/batch), `outputs/predictions/*.csv`,
  `outputs/metrics/*.json`, members' figures, and `models/*/best.pt` (enables live vision on upload).
- The 750 images (`data/processed/` or `inputs/images/`) for gallery thumbnails.

## Ownership note
`src/layout_detection.py` + `src/stamp_signature_detection.py` are Jordan's/Diana's modules. The app
should load YOLO weights **generically** in `streamlit_helpers` (or via thin, additive `predict_*`
functions) rather than rewriting members' code — coordinate before editing their files.

## Build sequencing (much can start before outputs land)
- **Now (output-independent):** `verdict_engine.py` + tests, the policy-builder UI, save/load,
  app skeleton/views, Work Order field, PDF report — all work against the fixed JSON schema with
  a few mock records.
- **After outputs land:** wire live inference (weights), point data-loading at the real published
  files, populate Model Report, finalize demo assets.

## Verification
- `python -m pytest` (or a quick script) on `verdict_engine.evaluate` with crafted signals:
  each rule toggled on/off flips `ready` and the per-rule breakdown as expected; AND-semantics hold.
- `streamlit run app/streamlit_app.py` launches clean; upload → annotated image + verdict render;
  toggling a rule live flips the verdict.
- Batch roll-up "N of 750 pass" matches a manual filter of the JSON records for the same policy.
- Save a policy, reload it, verdict reproduces; export passing set opens as valid CSV/JSON;
  per-invoice PDF downloads and contains image + verdict + breakdown.
- With `models/` empty: upload still yields a verdict with vision marked "model unavailable"
  (hybrid fallback). With weights present: vision boxes appear.
