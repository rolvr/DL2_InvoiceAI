# Jordan — Speaking Transcript
## Region Detection & IoU Evaluation

*(~2–3 minutes. Read naturally — this is a script to internalize, not recite word for word.)*

---

Hi, I'm Jordan. My stage detects *where the important business regions are* on a document —
`company`, `date`, `address`, and `total` — plus a catch-all `other_text` class, and then I
evaluate how good those detections are using IoU. This feeds Damir directly, because once you know
*where* the date or total is, you only need to OCR that small region instead of the whole page.

[SHOW: the OCR Dataset annotation JSON — `ocr_boxes` + `entities`]

I trained on the **OCR Dataset of Multi-type Documents** — 973 real receipt images with 52,331
real polygon text boxes. But here's the catch: the dataset gives me text *boxes with no class
label*, and separately gives me entity *values* like the total amount, with no coordinates at all.
Neither half is directly usable as detection training data on its own.

[SHOW: the fuzzy-matching code cell, `fuzz.partial_ratio` / `fuzz.ratio`]

So the intellectual core of my notebook is joining the two: for every text box, I compare its
transcribed text against every entity value using `rapidfuzz` — I take the maximum of
`partial_ratio` and `ratio` — and if that similarity score clears a threshold of **88**, I assign
that box the matching field label; otherwise it becomes `other_text`. That turns 52,331 unlabelled
boxes into a genuine 5-class region-detection training set with real geometry, without me having
to hand-annotate anything. What can this mislabel? A box containing a substring that happens to
resemble an entity value, or two nearby boxes with similar text, can occasionally get the wrong
label — that's the trade-off of a fuzzy threshold instead of exact matching.

[SHOW: the class-distribution printout — `other_text` dominating]

I trained a **YOLOv8n** 5-class detector under the `colab_gpu` profile — 100 epochs, image size
960, batch 16 — with an inference confidence of 0.25 and IoU match threshold of 0.5. The
challenge I have to name explicitly is **class imbalance**: `other_text` massively outnumbers the
four named field classes, since most text on a receipt isn't the company, date, address, or total.
That's exactly why I report **per-class** precision, recall, and mean IoU — a single blended mAP
would be dominated by `other_text` and would hide how well I'm actually detecting the fields that
matter for the business logic.

[SHOW: `outputs/metrics/region_iou_metrics.json`]

Here are the final per-class numbers. **Company**: precision 0.897, recall 0.819, mean IoU 0.894.
**Date**: precision 0.756, recall 0.855, mean IoU 0.812 — my weakest precision, which makes sense,
dates are short numeric strings that are easy to confuse with other numeric text on a receipt.
**Address**: precision 0.880, recall 0.883, mean IoU 0.896 — my best-localized class. **Total**:
precision 0.763, recall 0.783, mean IoU 0.887. **Other_text**: precision 0.911, recall 0.967, mean
IoU 0.877 — high recall makes sense, it's the catch-all class. **Macro mean IoU across all five
classes: 0.873.** I evaluate on the dataset's own official test split of 98 images, then run
inference on the 750 real invoices tagged `source="invoice"`. Receipts are about 460 pixels wide;
our invoices are full-page, 1654 by 2339 — that's a real domain shift, so invoice results are
counts only, never accuracy. The good news: **750 of 750 invoices** get at least one region
detection — unlike a visual mark like a stamp, business-text regions are present everywhere, so
the detector transfers usefully even without invoice-native training data.

[SHOW: presentation/images/region_detection_examples.png]
[SHOW: presentation/images/metrics_per_class.png]

---

## Likely Professor Q&A

**Q1: How did you turn unlabelled boxes into labelled training data?**
A: I fuzzy-matched each box's OCR'd text against the document's known entity values — company,
date, address, total — using RapidFuzz's partial-ratio and ratio scores, taking the best of the
two. If the best score cleared a threshold of 88, the box got that field's label; otherwise it was
tagged `other_text`. It's a heuristic label-construction step, not hand annotation, so I checked
the resulting class distribution to make sure the matching was behaving sensibly.

**Q2: What's the difference between mAP and IoU, and how does class imbalance distort metrics?**
A: IoU measures overlap quality for a single predicted-vs-true box pair. mAP (mean Average
Precision) aggregates precision across confidence thresholds and typically across classes into one
number. With heavy class imbalance — `other_text` dominating — an overall mAP would be pulled
toward whatever `other_text` does, potentially masking poor performance on the rarer, more
business-critical classes like `total` or `date`. That's why I report every class's precision,
recall, and mean IoU separately rather than one combined score.

**Q3: Why receipts instead of directly annotating invoice regions?**
A: Because the OCR Dataset gives me 52,331 *real* polygon boxes with real transcriptions and
entity ground truth — no public dataset offers that for full-page invoices. Rather than fabricate
synthetic or heuristic invoice boxes, which the team explicitly decided against, I train on the
best real labelled data available and apply the resulting detector to invoices, reporting that
step as a disclosed domain shift rather than pretending the receipt-trained detector is
invoice-native.
