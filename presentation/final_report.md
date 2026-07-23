# Invoice Region Detection & Business-Parameter Extraction for Obligation-Readiness

**A Deep Learning II Group Project**

**Authors:** Rolando (Data Ingestion & Manifest), Diana (Stamp & Signature Detection), Jordan
(Region Detection & IoU Evaluation), Damir (OCR, Parameters & Terms Extraction), Hessam
(Integration, Verdict Engine & Streamlit Application)

**Date:** July 2026

---

## Abstract

Before an invoice image can become a structured digital obligation record — the kind a
downstream finance or legal system (in the spirit of a "Pistac.io"-style platform) can act on
without a human first reading it — someone has to answer a handful of yes/no questions: *is it
signed or stamped? does it cite a purchase order, contract, or work order? does it state clear
payment terms and a valid date?* Doing this by hand does not scale past a few hundred invoices.
This project builds an end-to-end computer-vision and OCR pipeline that reads an invoice image
and answers those questions automatically, then lets a user **configure their own readiness
policy** and see a transparent, per-rule Ready / Not-ready verdict — never a black-box yes/no.

Five stages, one per team member, hand off outputs through a fixed CSV/JSON interface contract:
data ingestion and manifest construction (Rolando), a YOLOv8n stamp/signature detector (Diana),
a YOLOv8n region detector trained on real polygon-annotated receipt data (Jordan), EasyOCR text
extraction feeding rule-based business-parameter and payment-terms extraction (Damir), and an
integration layer that merges everything into one JSON per invoice and powers a Streamlit
application built around a **fail-closed, user-configurable verdict engine** (Hessam). Detectors
are trained and evaluated on the best available real, labelled datasets — SignverOD, StaVer, and
the OCR Dataset of Multi-type Documents — none of which are invoices; they are then *applied* to
real invoice scans, and we report that domain-transfer step honestly as detection counts, not
accuracy, since no invoice-level ground truth exists. This report documents the methodology,
design rationale, and honest limitations of the system; final quantitative results are inserted
as placeholders pending completion of two members' Colab GPU training runs (see Section 5).

---

## 1. Business Problem & Motivation

A business that receives invoices as scanned images or photographs faces a bottleneck before any
of that paper can enter an automated accounts-payable or obligation-tracking workflow: a human
has to look at each one and check whether it is *complete enough to act on*. Typical checks
include:

- Is the invoice **signed or stamped** (evidence of authorization)?
- Does it cite a **reference number** — a purchase order (PO), sales order, contract, or work
  order — that ties it to an approved commitment?
- Does it state a clear **invoice date** and **payment terms** (e.g. "Net 30")?
- Are there any **risk clauses** — late-payment penalties, dispute language — worth flagging to
  a reviewer?

At the volume real businesses operate at (thousands of invoices a month), manual triage is slow,
inconsistent between reviewers, and creates a queue that delays payment and reconciliation. The
Pistac.io framing used throughout this project names the goal precisely: a **digital obligation
record** — a structured, machine-readable summary of what an invoice obligates the business to do
and when — that downstream systems can consume without a human reading the source image first.

Our answer is a pipeline that takes an invoice image in and produces (a) a structured JSON record
of everything the pipeline could determine about that invoice, and (b) a Ready / Not-ready
**verdict**, evaluated against rules the *user* chooses and configures, with a transparent
per-rule breakdown of why an invoice passed or failed. Critically, the verdict is not a fixed
hardcoded rule buried in code — a compliance officer, an AP clerk, and an auditor may reasonably
want different thresholds (require both a stamp *and* a signature vs. either one; a 30-day vs.
a 60-day payment-terms floor), so the system exposes the policy itself as user-editable
configuration, and defaults to the conservative, safe answer whenever it cannot confirm a rule
(**fail-closed**: missing evidence is treated as a failed check, never a free pass).

## 2. Related Datasets & Data Pipeline

No single public dataset contains full-page invoices annotated with stamps, signatures, business
regions, and business-parameter text all at once. We therefore combine four real, purpose-built
datasets, each covering one facet of the problem, and apply the resulting models to real invoice
scans:

| Dataset | Contents | Used by |
|---|---|---|
| **Invoice batches** (real scans) | ~5,201 unique real invoice images after de-duplication; 750 sampled into the working manifest; batch_1 carries annotation CSVs (real OCR text + structured fields) for ~1,413 images | Rolando (ingestion); all others via the manifest |
| **OCR Dataset of Multi-type Documents** | 973 SROIE-style receipt images, pre-split 778/97/98, **100% annotated** with 52,331 real polygon text boxes + transcriptions, plus entity fields (`company`, `date`, `address`, `total`) | Jordan (region detector), Damir (OCR evaluation) |
| **SignverOD** | 2,765 document images with signature bounding boxes (4 categories; only category 1 = signature is used) | Diana |
| **StaVer** | 400 document scans with binary stamp ground-truth **masks** (no boxes — boxes are derived) | Diana |

**Rolando's data-engineering stage** turns a messy tree of raw invoice scans into the single
clean artifact every other stage joins on: `invoice_manifest.csv`
(`document_id, image_path, width, height, split, has_ground_truth`). Two decisions here are worth
calling out because they materially change what the rest of the pipeline can honestly claim:

- **Annotation-aware resampling.** A naive random sample of invoices produced only **26.3%**
  ground-truth coverage, because annotation CSVs exist *only* for `batch_1`. Resampling to prefer
  annotated images lifted coverage to **100%** across the 750-row manifest (split 525/120/105),
  at the cost of reduced cross-batch visual variety — a deliberate, documented trade-off.
- **Duplicate discovery.** `batch_3/` was found to silently re-contain copies of `batch_1` and
  `batch_2`. The true unique invoice count is **5,201, not 8,181**. Sampling the duplicated copies
  would have let the same physical invoice appear in both a training split and a test split —
  classic data leakage — so the duplicates are excluded from sampling entirely.

The manifest's `document_id` is the join key every downstream CSV uses, which is why getting this
stage right first is a precondition for everything else being trustworthy.

## 3. Methodology

Every training notebook pulls its training knobs from a single shared module,
`src/compute_profile.py`, so the same code runs identically in two modes and the two never
silently drift apart:

| Knob | `local_cpu` (dev machine) | `colab_gpu` (member runs) |
|---|---|---|
| epochs | 10 | **100** |
| imgsz | 416 | **960** |
| batch | 8 | **16** |
| workers | 0 | 2 |
| patience (early stop) | 10 | 20 |
| max images/class | 250 (subsampled) | **None (full dataset)** |
| device | cpu | GPU (device 0) |

All members trained under `IIP_COMPUTE_PROFILE = "colab_gpu"` on a Colab T4/L4/A100 runtime. Every
metrics JSON also carries a `_run` provenance block (profile, epochs, imgsz, device, wall-clock
seconds) so local-CPU and Colab-GPU runs can later be compared on equal footing.

### 3.1 Rolando — Data Ingestion & the Manifest

No model is trained in this stage; it is data engineering, and the project's overall honesty rests
on it. Beyond the annotation-aware resampling and duplicate exclusion described in Section 2,
Rolando's notebook performs a stratified split (by ground-truth availability, so every split stays
fully labelled) and produces a data-quality report plus sample/preprocessing figure grids for the
report and deck.

### 3.2 Diana — Stamp & Signature Detection

**Model choice: YOLOv8n**, trained as a single **2-class** detector (`stamp`, `signature` — never
merged, never renamed, since the final JSON schema and the verdict engine both assume the two
exist independently). YOLOv8n ("nano") was chosen over a two-stage detector such as Faster R-CNN
because it is a fast one-stage architecture well suited to small, visually distinct marks, trains
comfortably within the Colab GPU time budget, and a single 2-class model shares one backbone
rather than requiring two separately trained detectors.

The data-engineering challenge here is real: SignverOD stores boxes as normalized `[x, y, w, h]`
which must be converted to pixel coordinates, and only category 1 (signature) is kept — categories
2–4 (initials, redaction, date) are dropped. StaVer, by contrast, ships **no boxes at all**, only
binary ground-truth masks; boxes are *derived* using `cv2.connectedComponentsWithStats`, and the
count of derived boxes is cross-checked against each scan's `numStamps` count from its info file
as a sanity check.

**Key parameters (colab_gpu):** epochs 100, imgsz 960, batch 16, patience 20; inference confidence
threshold **0.25**; IoU match threshold **0.5** (via the shared `src/iou.py`, never reimplemented).
**Evaluation:** precision, recall, and mean IoU computed **per class** on a real held-out split of
SignverOD + StaVer — never merged into one detection score, since a "must be signed" business rule
needs the signature number specifically. Inference is then run on the 750 invoices and reported as
**detection counts and confidence distributions only** (no invoice-level ground truth exists, so
no precision/recall claim is made there).

### 3.3 Jordan — Region Detection & IoU

**Model choice: YOLOv8n**, trained as a **5-class** detector: `company, date, address, total,
other_text`. The intellectual core of this stage is turning an unlabelled-boxes dataset into a
labelled one: the OCR Dataset of Multi-type Documents ships 52,331 real polygon text boxes with
*no class label*, alongside per-document entity *values* (`company`, `date`, `address`, `total`)
with *no coordinates*. Jordan joins the two by **fuzzy-matching** each box's transcribed text
against each entity value (`rapidfuzz`, using the max of `partial_ratio` and `ratio`, threshold
**88**), assigning the best-matching field label when the score clears the threshold and
`other_text` otherwise. This turns 52,331 unlabelled boxes into a genuine 5-class region-detection
training set with real geometry.

**Key parameters (colab_gpu):** epochs 100, imgsz 960, batch 16; fuzzy-match threshold 88;
inference confidence **0.25**; IoU match threshold **0.5**. **Challenge named explicitly:**
`other_text` massively outnumbers the four named field classes (visible directly in the
train-split class-distribution printout), so **per-class** precision/recall/IoU are reported,
never a single blended score that a dominant class could inflate. **Evaluation:** per-class IoU on
the dataset's own official test split (98 images). Predictions are then run on the 750 invoices
(rows tagged `source="invoice"`), where receipts (~460 px wide) transferring to full-page invoices
(1654×2339) is a domain shift reported as counts. Jordan's `date`/`total`/`company` boxes have a
second life in the app: cropping and OCR-ing just those regions gives a field localiser that feeds
the verdict engine's date signal and a "where is this field, and what does it say" overlay.

### 3.4 Damir — OCR, Business Parameters & Terms

**Model choice: EasyOCR** (a deep-learning OCR engine, run on GPU) for text extraction, followed
by **rule-based extraction** — `src/parameter_checker.py` and `src/terms_extraction.py` — for
structured fields. The rule-based choice over an end-to-end learned extractor is deliberate:
it needs no training data of its own, every decision is traceable to a specific keyword or regex
match (auditable, which matters for a compliance-adjacent tool), and a user can add a brand-new
required field (e.g. "Insurance Certificate") by editing
`config/required_fields_config.json` with no code change.

Damir's stage has **two evaluation sets of very different strength**, and the notebook is explicit
about reporting both honestly:

- **Primary (headline):** the OCR Dataset's own test split — 973 images, **100% coverage**,
  per-box ground-truth transcriptions — scored with real **CER** (character error rate) and
  **WER** (word error rate) via `jiwer`. Lower is better.
- **Secondary:** a bounded sample of up to 120 real batch_1 invoices with ground-truth OCR text
  from the annotation CSVs — a genuine full-page-invoice check, but small, and the notebook always
  states the denominator (only ~197 of the 750 manifest images carry any ground truth at all,
  because annotation CSVs exist only for `batch_1`).

**Key parameters:** OCR language `en`, GPU enabled; required-field keywords/regex patterns and the
custom-field list are both read from `config/required_fields_config.json` (default fields: PO
Reference, Order Number, Contract Number, Work Order No., Project Reference, Insurance Policy
Number, Bill of Lading Number). Payment-terms extraction pattern-matches phrasings such as
"Net 30" or "due within 15 days" and separately flags late-payment, dispute, and penalty clause
language via keyword sets in `src/terms_extraction.py`.

### 3.5 Hessam — Integration, Verdict Engine & Streamlit Application

Hessam's stage merges all four upstream outputs into one final JSON per invoice
(`model_interface_contract.md` §5) and builds the demo application. The headline design decision
is the **verdict engine** (`src/verdict_engine.py`): rather than a single hardcoded readiness rule,
the user builds a **policy** out of four toggleable rule types before judging any invoice —

- **Visual mark** — stamp OR signature, stamp AND signature, stamp only, or signature only.
- **Reference number** — at least one (or all) of PO / Order / Contract / Work Order present.
- **Invoice date range** — inclusive start/end bounds.
- **Payment terms** — a day-count threshold with a comparison operator (e.g. `> 30` days).

The verdict is the **AND of every enabled rule**; disabled rules are skipped entirely. Every rule
returns one of three statuses — `pass`, `fail`, or `unknown` — and the engine is deliberately
**fail-closed**: an `unknown` status (no signal available for that invoice, e.g. it was never
OCR'd) counts as *not satisfied*, so the invoice is marked Not-ready rather than silently passed.
The breakdown always shows this distinction explicitly ("unknown — treated as fail"), never
hiding it. This logic is pure Python with no Streamlit or I/O dependency, so it is independently
unit-tested (9/9 tests passing as of this writing) and reused identically by both the single-
invoice and whole-batch code paths.

A subtler integration point deserves its own callout: **Damir's `parameter_presence_results.csv`
and `terms_extraction_results.csv` are keyed to the OCR-Dataset *receipt* IDs, not the 750
invoices**, because that is the dataset his notebook evaluates against for real ground truth. The
invoice-level reference/date/payment-terms signals the verdict engine actually consumes are
therefore **derived at integration time** — Damir's own shared modules
(`parameter_checker.py`, `terms_extraction.py`) are re-run on invoice OCR text (from the upload
path or `ocr_outputs.csv`) and on the batch_1 annotation CSVs' `OCRed Text` field. This keeps
Damir's evaluated numbers honest to what he actually measured, while still giving the app real
signals to judge invoices against, at whatever coverage the underlying OCR/annotation data
supports.

The Streamlit application (`app/streamlit_app.py`) exposes three views: **Live Demo** (upload or
pick one invoice → annotated boxes → verdict card with per-rule breakdown → downloads),
**Batch Gallery** (roll up the configured policy across all 750 invoices — "N of 750 pass" — with
filtering and a passing-set export), and **Model Report** (the members' own metrics plus the
local-CPU-vs-Colab-GPU comparison charts). Execution is **hybrid**: the gallery and roll-up read
pre-computed published results for full-speed browsing, while a brand-new uploaded image runs the
live pipeline (vision models if `best.pt` weights are present in `models/`, OCR/parameter/terms
extraction always, since those run acceptably on CPU).

## 4. Integration & the Configurable Verdict Engine

The system's central architectural insight is that **the pipeline extracts signals; the user's
policy is applied to those signals** — and the two are cleanly separated. Every signal a verdict
rule needs already exists somewhere in a member's output:

| Verdict rule | Signal | Source |
|---|---|---|
| Stamp / signature present | `visual_elements.stamp_detected` / `signature_detected` | Diana |
| Reference number present | `required_parameters[...]` via `config/required_fields_config.json` | Damir (re-run on invoice text at integration) |
| Invoice date in range | `payment_context.invoice_date` | Damir / annotation text (derived) |
| Payment terms > N days | `payment_context.billing_due_days` | Damir / annotation text (derived) |

Notably, the verdict depends on Diana's and Damir's signals but **not** on Jordan's region labels
directly — Jordan's `company`/`date`/`address`/`total`/`other_text` vocabulary is a receipt-entity
schema, not the obligation-region schema in `config/label_schema.json`, so that mismatch is kept
off the verdict's critical path. It still matters: Jordan's boxes power a "detected regions" panel
and the region-guided crop-then-OCR feature (cropping a `date` or `total` box and running OCR on
just that region) that feeds the app's date rule and its clearest visual.

Coverage differs sharply by path. On the **upload path**, all four rule signals can be computed
live for a brand-new image since OCR, parameter-checking, and terms-extraction all run on CPU.
On the **batch/gallery path**, the visual-mark signal has full coverage (750/750, since Diana's
detector runs on every manifest image), but the reference/date/payment-terms signals only cover
the subset of invoices with usable OCR or batch_1 annotation text — for the rest, the verdict
engine's fail-closed rule marks those checks `unknown → fail`, and the UI labels them "not
evaluated (no OCR)" rather than hiding the gap.

## 5. Results

Diana's and Jordan's Colab GPU training runs, and independent verification of Damir's completed
run, were still in progress at the time of writing. The tables below are the exact structure the
final numbers will populate — every cell that depends on a completed run is a clearly-marked
placeholder rather than a guess.

### 5.1 Diana — Stamp & Signature Detection (real held-out split of SignverOD + StaVer)

| Class | Precision | Recall | Mean IoU | Support |
|---|---|---|---|---|
| stamp | ⟪TBD: Diana stamp precision (from stamp_signature_metrics.json)⟫ | ⟪TBD: Diana stamp recall⟫ | ⟪TBD: Diana stamp mean-IoU⟫ | ⟪TBD: Diana stamp support (tp+fn)⟫ |
| signature | ⟪TBD: Diana signature precision⟫ | ⟪TBD: Diana signature recall⟫ | ⟪TBD: Diana signature mean-IoU⟫ | ⟪TBD: Diana signature support (tp+fn)⟫ |

Invoice inference (750 real invoices, counts only — no ground truth):
⟪TBD: invoices with ≥1 detection / 750, and detections-by-label breakdown, from `_invoice_inference` block⟫

### 5.2 Jordan — Region Detection (OCR Dataset official test split, 98 images)

| Class | Precision | Recall | Mean IoU | Support |
|---|---|---|---|---|
| company | ⟪TBD: Jordan company precision (from region_iou_metrics.json)⟫ | ⟪TBD: Jordan company recall⟫ | ⟪TBD: Jordan company mean-IoU⟫ | ⟪TBD: Jordan company support⟫ |
| date | ⟪TBD: Jordan date precision⟫ | ⟪TBD: Jordan date recall⟫ | ⟪TBD: Jordan date mean-IoU⟫ | ⟪TBD: Jordan date support⟫ |
| address | ⟪TBD: Jordan address precision⟫ | ⟪TBD: Jordan address recall⟫ | ⟪TBD: Jordan address mean-IoU⟫ | ⟪TBD: Jordan address support⟫ |
| total | ⟪TBD: Jordan total precision⟫ | ⟪TBD: Jordan total recall⟫ | ⟪TBD: Jordan total mean-IoU⟫ | ⟪TBD: Jordan total support⟫ |
| other_text | ⟪TBD: Jordan other_text precision⟫ | ⟪TBD: Jordan other_text recall⟫ | ⟪TBD: Jordan other_text mean-IoU⟫ | ⟪TBD: Jordan other_text support⟫ |
| **Macro mean IoU** | — | — | ⟪TBD: Jordan macro_mean_iou⟫ | — |

Invoice inference (domain shift, counts only): ⟪TBD: invoices with ≥1 region detection / 750, from `_invoice_inference` block⟫

### 5.3 Damir — OCR & Business-Parameter Extraction

**Primary (OCR Dataset test split, 100% coverage):**

| Metric | Value |
|---|---|
| Docs scored | ⟪TBD: Damir n_scored (ocr_parameter_metrics.json → ocr_primary)⟫ |
| CER (mean / median) | ⟪TBD: Damir cer_mean⟫ / ⟪TBD: Damir cer_median⟫ |
| WER (mean / median) | ⟪TBD: Damir wer_mean⟫ / ⟪TBD: Damir wer_median⟫ |

**Secondary (batch_1 real invoices — state the denominator):**

| Metric | Value |
|---|---|
| Invoices scored / manifest with GT | ⟪TBD: Damir ocr_secondary_invoices.n_scored⟫ / ⟪TBD: manifest rows with GT (denominator_note)⟫ |
| CER (mean) | ⟪TBD: Damir ocr_secondary_invoices.cer_mean⟫ |

**Business-parameter presence rate** (share of scored documents where each field was detected):
⟪TBD: parameter_presence_rate dict — has_company / has_date / has_total / has_address, from ocr_parameter_metrics.json⟫

### 5.4 Hessam — Integration & Verdict Engine Coverage

| Metric | Value |
|---|---|
| Invoices in manifest | 750 |
| Sample final-JSON records produced | ⟪TBD: count of files in outputs/final_json/sample_invoice_outputs/⟫ |
| Invoices with both stamp AND signature detected | ⟪TBD: `ready` count from final_pipeline_report.md⟫ |
| Default policy — N of 750 pass | ⟪TBD: batch-gallery roll-up count under the "Default" preset policy⟫ |
| Strict policy — N of 750 pass | ⟪TBD: batch-gallery roll-up count under the "Strict" preset policy⟫ |
| Lenient policy — N of 750 pass | ⟪TBD: batch-gallery roll-up count under the "Lenient" preset policy⟫ |

### 5.5 Compute Budget Comparison (local_cpu vs. colab_gpu, from each `_run` provenance block)

| Member | Profile | Epochs | imgsz | Batch | Wall-clock |
|---|---|---|---|---|---|
| Diana | colab_gpu | 100 | 960 | 16 | ⟪TBD: Diana wall_clock_sec⟫ |
| Jordan | colab_gpu | 100 | 960 | 16 | ⟪TBD: Jordan wall_clock_sec⟫ |
| Damir | colab_gpu | — (no training) | — | — | ⟪TBD: Damir wall_clock_sec⟫ |

## 6. Limitations & Honest Caveats

These are stated plainly, not hidden, because owning a limitation is a stronger technical
position than glossing over it.

- **Domain gap.** Diana's detector is trained on SignverOD (documents) and StaVer (documents);
  Jordan's detector is trained on the OCR Dataset of Multi-type Documents (receipts, ~460 px
  wide). Neither source is an invoice, and the invoice corpus is full-page (1654×2339). Both
  detectors are then *applied* to invoices as a domain-transfer step. Metrics are reported on each
  dataset's own real held-out split (legitimate numbers); on the invoices themselves we report
  **detection counts**, never precision/recall/accuracy, because there is no invoice-level ground
  truth to score against.
- **Ground-truth coverage.** Annotation CSVs with real structured text exist only for `batch_1`.
  A naive sample gave 26.3% manifest coverage; annotation-aware resampling raised that to 100%
  across the 750-row manifest, trading away cross-batch visual variety for full labels — a
  deliberate, documented trade-off, not an oversight.
- **Data leakage, caught and fixed.** `batch_3/` was discovered to secretly duplicate `batch_1`
  and `batch_2`. True unique invoice count is 5,201, not 8,181. The duplicates are excluded from
  sampling to prevent the same invoice appearing in both a training and a test context.
- **Integration re-derivation.** Damir's `parameter_presence_results.csv` and
  `terms_extraction_results.csv` are keyed to OCR-Dataset receipt IDs, not the 750 invoices. The
  invoice-level reference/date/payment-terms signals the verdict engine consumes are therefore
  derived at integration time from invoice OCR text and batch_1 annotation text using Damir's own
  shared modules — coverage on the batch path is bounded by how many invoices have usable OCR or
  annotation text, not the full 750.
- **Verdict-engine semantics.** The engine is deliberately fail-closed: a rule with no signal for
  a given invoice counts as failed, never passed. This is the right default for a compliance gate
  (a readiness check must not pass what it cannot confirm), but it means Not-ready counts include
  both genuinely-failing invoices and invoices the pipeline simply could not evaluate — the
  per-rule breakdown always distinguishes the two so this is never silently conflated.
- **Compute budget.** All headline numbers come from the `colab_gpu` profile (100 epochs, imgsz
  960, full dataset). The `local_cpu` profile (10 epochs, imgsz 416, 250-image subsample) exists
  purely for fast iteration on a CPU-only development machine and is not the basis for any
  reported metric.

## 7. Conclusion & Future Work

The pipeline demonstrates that a business-facing readiness question — "is this invoice complete
enough to become a digital obligation record?" — can be decomposed into a small number of
independently trainable/evaluable computer-vision and NLP sub-problems (mark detection, region
detection, OCR, rule-based field extraction), integrated through a fixed schema, and judged by a
transparent, user-configurable, fail-closed rule engine rather than a single opaque model output.
Every sub-stage is evaluated on real, labelled data with real metrics; the honest domain gap
between training data and the invoice application target is surfaced rather than hidden, and the
data-engineering issues found along the way (low ground-truth coverage, duplicate-invoice
leakage) were caught and fixed before they could quietly bias results.

Future work, roughly in order of expected impact: (1) collect or license invoice-native
ground truth — even a few hundred hand-annotated invoices with real stamp/signature/region boxes
would let Diana and Jordan report true invoice-domain accuracy instead of source-domain accuracy
plus counts; (2) extend the annotation-aware sampling strategy to batches 2 (and any future
batches) so ground-truth coverage does not depend on batch_1 alone; (3) add a learned OCR-quality
gate so the verdict engine can distinguish "field genuinely absent" from "OCR failed, field
possibly present" more granularly than a single `unknown` status; (4) expose the fuzzy-match
threshold and confidence thresholds as tunable sidebar controls in the app so a grader or user can
directly observe the precision/recall trade-off live, rather than only in the notebooks.

## 8. Individual Contributions

| Member | Role | Key deliverables |
|---|---|---|
| Rolando | Data ingestion & manifest | `invoice_manifest.csv`, data-quality report, annotation-aware resampling, duplicate-leakage discovery and exclusion |
| Diana | Stamp & signature detection | 2-class YOLOv8n detector, SignverOD/StaVer adaptation (normalized-box conversion; mask→box derivation via connected components), per-class P/R/IoU |
| Jordan | Region detection & IoU | 5-class YOLOv8n detector, entity-text-to-box fuzzy-matching label construction, per-class P/R/IoU on the OCR Dataset test split |
| Damir | OCR, parameters & terms | EasyOCR text extraction, CER/WER evaluation (primary + secondary sets), rule-based parameter/terms extraction integration |
| Hessam | Integration, verdict engine & app | Final-JSON integration, `src/verdict_engine.py` (fail-closed configurable policy engine, unit-tested), Streamlit application (Live Demo / Batch Gallery / Model Report), report & deck assembly |

## References

- SignverOD — signature detection dataset (document images with signature bounding boxes).
- StaVer — stamp verification dataset (document scans with stamp ground-truth masks).
- OCR Dataset of Multi-type Documents — SROIE-style receipt dataset with polygon text boxes,
  transcriptions, and entity annotations (company/date/address/total).
- Real invoice batch scans (`data/raw/invoices/batch_1..3/`) with batch_1 annotation CSVs
  (`Json Data{invoice, items, subtotal, payment_instructions}`, `OCRed Text`).
- Jocher, G. et al., **Ultralytics YOLOv8** (object detection framework).
- JaidedAI, **EasyOCR** (deep-learning OCR engine).
- `jiwer` — CER/WER scoring library.
- `rapidfuzz` — fuzzy string matching library.
- Project source: `src/compute_profile.py`, `src/verdict_engine.py`, `src/parameter_checker.py`,
  `src/terms_extraction.py`, `src/iou.py`, `model_interface_contract.md`,
  `colab/notebooks/00_preflight_check_colab.ipynb` through `05_hessam_integration_colab.ipynb`.
