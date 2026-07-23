# DL-II Group Project — Study & Presentation Guide

**Invoice Region Detection & Business-Parameter Extraction → Obligation-Readiness**

> **How to use this document.** Upload **this file + your own notebook** to your AI assistant
> (your Claude or ChatGPT account) and ask it to walk you through your part. Suggested opening
> prompt:
>
> *"I'm presenting this notebook in class. Using the attached GROUP_STUDY_GUIDE.md for context,
> explain my notebook cell by cell: the model I chose and why, the key parameters, how it's tuned
> and evaluated, and the honest limitations. Then quiz me with 5 questions a professor might ask."*
>
> Each member section below ends with tailored questions to rehearse. Read the shared sections
> (1–5) first — they're common to everyone — then your own member section.

---

## 1. The problem we're solving

A business receives thousands of invoices as **images/scans**. Before an invoice can become a
structured **digital obligation record** (a "Pistac.io-ready" record that downstream finance/legal
systems can act on), someone must check: *is it signed or stamped? does it cite a PO / contract /
work-order? does it have clear payment terms and a valid date?*

Doing that by hand does not scale. **Our pipeline reads an invoice image and outputs a structured
JSON + a Ready / Not-ready verdict**, with every decision made transparent (why an invoice failed,
not just that it failed).

The end product is a **Streamlit app** where a user **configures the verdict rules themselves**
(e.g. "must have a stamp OR signature, must cite a PO or contract, payment terms > 30 days") and
sees the verdict for one invoice and across the whole batch.

## 2. The pipeline (how the five notebooks connect)

```
 01 Rolando ── invoice_manifest.csv ─────────────┐
   (data prep)                                    │
                                                  ▼
 02 Diana ── stamp/signature boxes ──►  ┌──────────────────┐
   (YOLOv8n detector)                   │   05 Hessam      │
                                        │  integration +   │─► final JSON per invoice
 03 Jordan ── region boxes ──────────►  │  Streamlit app + │   + Ready/Not-ready verdict
   (YOLOv8n detector)                   │  verdict engine  │   + metrics report
                                        └──────────────────┘
 04 Damir ── OCR text + params/terms ──────────────▲
   (EasyOCR + rule-based extraction)               │
```

Each notebook **publishes its outputs to Google Drive** (`outputs/<member>/…`) via
`colab_bootstrap.publish()`. Hessam's integration consumes them all.

## 3. Shared engineering the whole team should understand

**Compute profiles (`src/compute_profile.py`).** Every training notebook reads its knobs from
`get_profile()` so the *same code* runs two ways:

| knob | `local_cpu` (dev machine) | `colab_gpu` (your run) |
|---|---|---|
| epochs | 10 | **100** |
| imgsz (image size) | 416 | **960** |
| batch | 8 | **16** |
| workers | 0 | 2 |
| patience (early-stop) | 10 | 20 |
| max images / class | 250 (subsampled) | **None (full dataset)** |
| device | cpu | 0 (GPU) |

Your Colab notebook pins `IIP_COMPUTE_PROFILE = "colab_gpu"`, so you train at the **generous**
budget. Be ready to explain *why* two profiles exist: reproducibility + not letting a CPU-only
dev machine and a GPU run silently diverge.

**Provenance (`_run` block).** Every metrics JSON records how it was produced (profile, epochs,
imgsz, wall-clock, model). This is what lets the final report compare runs fairly.

**`colab_bootstrap.py`** mounts Drive, puts the shared `src/` code on the path, verifies inputs,
and `publish()`es results to both a "latest" folder and a timestamped archive (so re-runs don't
destroy earlier numbers).

## 4. The datasets (and an important honesty point)

| Dataset | What it is | Used by |
|---|---|---|
| **Invoice batches** | ~5,201 unique real invoice scans; 750 sampled into the manifest; batch_1 has annotation CSVs (real OCR text + fields) for ~1,413 | Rolando, all (via manifest) |
| **OCR Dataset of Multi-type Documents** | 973 SROIE-style **receipts**, 100% annotated, **52,331 polygon boxes + text** + entities (company/date/address/total), pre-split 778/97/98 | Jordan, Damir |
| **SignverOD** | 2,765 document images with **signature** bounding boxes (category 1 of 4) | Diana |
| **StaVer** | 400 scans with **stamp** ground-truth *masks* (no boxes — boxes are derived) | Diana |

**The domain gap — say this out loud in the demo.** SignverOD/StaVer are *documents, not invoices*;
the OCR Dataset is *receipts, not full-page invoices*. So detectors are trained on the best real
labelled data available and then **applied** to invoices. Metrics are reported on each dataset's own
held-out split (honest, real numbers); on the invoices we report detection **counts**, not
accuracy, because there's no invoice-level ground truth. Owning this limitation scores better than
hiding it.

---

## 5. Notebook 00 — Preflight (everyone runs this once)

Not a member deliverable — a **one-minute, no-GPU check** that Drive is set up correctly (code,
manifest, datasets all present and at the right paths) before anyone burns GPU time. If it prints
`PASSED n / FAILED 0`, you're clear to run your notebook.

---

## 6. Member deep-dives

### 6.1 — Notebook 01 · Rolando · Data Ingestion & the Manifest

- **Purpose:** turn a messy tree of invoice scans into one clean **manifest** (`invoice_manifest.csv`:
  document_id, image_path, width, height, split, has_ground_truth) that every other notebook joins on.
- **No ML model** — this is data engineering, and that's the point to present well.
- **Key decisions to explain:**
  - **Annotation-aware sampling.** Naive sampling gave only **26% ground-truth coverage** because
    annotation CSVs exist *only for batch_1*. Resampling to prefer annotated images lifted coverage
    to **100%** (750 rows, split 525/120/105). Trade-off: less cross-batch visual variety for full
    labels — a real engineering trade-off worth discussing.
  - **Duplicate discovery.** `batch_3/` secretly re-contains copies of batches 1 & 2 → true unique
    count is **5,201, not 8,181**. Sampling the duplicates would have leaked the same invoice into
    train *and* test. Catching data leakage is a strong talking point.
  - **Stratified split** by ground-truth availability so every split stays fully labelled.
- **Demo angle:** "garbage in, garbage out" — the whole pipeline's honesty rests on this manifest.
- **Rehearse:** Why is data leakage dangerous? Why prefer annotated images? What would you do
  differently with annotations for all batches?

### 6.2 — Notebook 02 · Diana · Stamp & Signature Detection

- **Purpose:** detect **stamp** and **signature** as **two separate classes** (never merged) and
  evaluate per class.
- **Model selection: YOLOv8n** (the "nano" YOLOv8 object detector). *Why:* small, fast, strong for
  small-object detection, trains in the Colab budget; a single **2-class** model rather than two
  separate detectors (simpler, shares a backbone). Be ready to justify YOLO vs a two-stage detector
  (Faster R-CNN): YOLO is one-stage → faster, good enough for two visually distinct marks.
- **Data engineering to explain:**
  - SignverOD boxes are stored **normalized** `[x,y,w,h]` → converted to pixels; only **category 1
    (signature)** is kept (2/3/4 = initials/redaction/date are dropped).
  - StaVer ships **no boxes** — only binary masks → boxes are **derived with connected-components**
    (`cv2.connectedComponentsWithStats`), cross-checked against the `numStamps` count. This is the
    trickiest part of your notebook; know it cold.
- **Key parameters (as run, budget-optimized):** imgsz **640**, epochs **≤50**, batch **16**,
  patience **20**, confidence **0.25**, IoU match **0.5**. *(Reduced from imgsz 960 / 100 epochs
  after the Colab GPU budget ran out at epoch 86 — be ready to explain this; see Challenges below.)*
- **Budget challenge (know this for Q&A):** the first full-budget run died at epoch 86 and was lost
  because checkpoints were on Colab's ephemeral disk. The notebook now trains at imgsz 640 / ≤50
  epochs AND checkpoints to Google Drive (`save_period=10`, resume-aware) so a disconnect is
  recoverable. Lesson: match the budget to free-tier Colab, and always checkpoint to durable storage.
- **Tuning:** early-stopping via `patience`; class balance between stamp/signature; confidence
  threshold trades precision vs recall.
- **Evaluation:** **precision / recall / mean-IoU per class** on the real held-out split, using the
  shared `src/iou.py` (do NOT reimplement IoU). Then inference on the 750 invoices → detection
  counts (no invoice GT).
- **Rehearse:** What is IoU? Why per-class metrics not just overall? Why did you derive boxes from
  masks and how? Precision vs recall trade-off for a "must be signed" check?

### 6.3 — Notebook 03 · Jordan · Region Detection & IoU

- **Purpose:** detect invoice **regions** and evaluate localisation quality (IoU).
- **Model selection: YOLOv8n**, a **5-class** detector — `company, date, address, total, other_text`.
- **The clever bit to present:** the OCR Dataset gives **text boxes with no class labels**, and
  **entity values with no coordinates**. Jordan **joins them by fuzzy-matching the entity text to
  the box text** (`rapidfuzz`), turning unlabelled boxes into labelled *region* training data. This
  is the intellectual core of the notebook — explain the matching threshold and what it mislabels.
- **Key parameters (colab_gpu):** imgsz **960**, epochs **100**, batch **16**; fuzzy-match threshold
  ~88; confidence **0.25**, IoU threshold **0.5**.
- **Challenge to name:** **class imbalance** — `other_text` massively outnumbers the four field
  classes. That's why you report **per-class** precision/recall/IoU, not just overall mAP.
- **Evaluation:** per-class IoU on the OCR-Dataset test split; then inference on the 750 invoices
  (`source="invoice"` rows) — receipts→invoices is a domain shift, reported as counts.
- **Use case for the app:** Jordan's `date`/`total`/`company` boxes act as **field localisers** —
  crop → OCR just that box → read the value → highlight *where* the field is. This feeds the app's
  date rule and its best visual.
- **Rehearse:** How did you create labels from unlabelled boxes? What is mAP vs IoU? How does class
  imbalance distort metrics and what did you do about it?

### 6.4 — Notebook 04 · Damir · OCR, Parameters & Terms

- **Purpose:** read the text, then extract **business parameters** (PO/Order/Contract/Work-Order
  references) and **payment terms** (date, due-days, clauses).
- **Model selection: EasyOCR** (deep-learning OCR, GPU) for text; **rule-based** extraction
  (`src/parameter_checker.py`, `src/terms_extraction.py`) for fields. *Why rule-based on top of OCR:*
  transparent, no training data needed for fields, easy for a user to extend with a new keyword/regex.
  Be ready to contrast EasyOCR vs Tesseract vs PaddleOCR (accuracy vs speed vs setup).
- **Two evaluation sets to explain:**
  - **Primary:** OCR Dataset receipts — **100% coverage**, per-box transcriptions → real
    **CER / WER** (character/word error rate, via `jiwer`). Lower is better.
  - **Secondary:** ~120 real batch_1 invoices with ground-truth OCR text — honest but small; always
    state the denominator (~197 of 750 invoices have any GT).
- **Key parameters:** OCR language `en`, GPU on; parameter fields + regex/keywords come from
  `config/required_fields_config.json` (so new fields need no code change).
- **Rehearse:** What are CER and WER? Why rule-based extraction on top of OCR rather than an
  end-to-end model? Which parameters are hardest to detect and why? Why report the denominator?

### 6.5 — Notebook 05 · Hessam · Integration, Verdict Engine & Streamlit App

- **Purpose:** merge everyone's outputs into one **final JSON per invoice**, then power the demo app.
- **The headline feature: a user-configurable verdict engine** (`src/verdict_engine.py`). Rather than
  a hardcoded rule, the user builds a **policy** from toggleable rules — visual mark (stamp OR/AND
  signature), reference-number present (any of PO/Order/Contract/Work-Order), invoice-date range,
  payment-terms threshold (> N days). Verdict = **AND of all enabled rules**, **fail-closed** (no
  evidence = not ready), with a per-rule breakdown.
- **Applied two ways:** one uploaded invoice (live), and across all 750 ("N of 750 pass this policy").
- **Integration honesty note:** Damir's parameter/terms CSVs are keyed to the *receipt* dataset, so
  the invoice-level reference/date/terms signals are **derived at integration** by running Damir's
  same shared modules on the invoice OCR text + batch_1 annotation text.
- **Rehearse:** Why is a *configurable* verdict better than a fixed one? What does "fail-closed"
  mean and why is it right for a compliance gate? How do you compare CPU vs GPU runs (the `_run` block)?

---

## 7. Glossary (quick answers for Q&A)

- **YOLOv8n** — a fast one-stage object detector; "n" = nano (smallest, fastest variant).
- **Bounding box** — rectangle (xmin,ymin,xmax,ymax) around a detected object.
- **IoU (Intersection over Union)** — overlap between a predicted box and the true box, 0–1; ≥0.5
  usually counts as a correct detection.
- **Precision** — of what you flagged, how much was right. **Recall** — of what was there, how much
  you found. Trade-off tuned by the confidence threshold.
- **mAP** — mean Average Precision across classes/thresholds; the standard detection score.
- **CER / WER** — Character / Word Error Rate for OCR; **lower is better**.
- **Epoch** — one full pass over the training data. **Batch** — images processed together per step.
- **Early stopping (patience)** — stop training when validation stops improving for N epochs.
- **Domain gap** — train and test data come from different distributions (documents/receipts vs
  invoices), so performance transfers imperfectly.
- **Fail-closed** — when evidence is missing, default to "not ready" (safe for a compliance gate).

## 8. Your 90-second pitch (fill in your numbers after the run)

> "I'm **[name]**, responsible for **[stage]**. I used **[model / method]** because **[reason]**.
> The hardest part was **[challenge]**, which I handled by **[solution]**. On the held-out data I got
> **[metric = value]**. The honest limitation is **[domain gap / coverage]**, and it feeds
> **[next stage]** by producing **[output file]**."

Good luck — rehearse with your AI using the prompt at the top of this guide.
