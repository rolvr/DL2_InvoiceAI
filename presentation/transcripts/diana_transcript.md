# Diana — Speaking Transcript
## Stamp & Signature Detection

*(~2–3 minutes. Read naturally — this is a script to internalize, not recite word for word.)*

---

Hi, I'm Diana. My job in this pipeline is answering one specific question for every invoice:
*is there a stamp on it, and is there a signature on it* — as two separate, independent checks,
because a business rule like "must be authorized" might require one, the other, or both, and
merging them into a single "authorization mark" class would throw that distinction away.

[SHOW: `outputs/predictions/stamp_signature_predictions.csv`]

I trained a **YOLOv8n** model — the "nano" variant of YOLOv8 — as a single **2-class** detector,
with `stamp` and `signature` as the two classes. I chose YOLO over a two-stage detector like
Faster R-CNN because it's a one-stage architecture: faster to train and run, and more than
accurate enough for two visually distinct marks like a stamp and a signature. I chose one 2-class
model instead of two separate detectors because it shares a single backbone, trains in one pass,
and I still get fully separate metrics per class at evaluation time — so I don't lose anything by
combining them at the architecture level.

[SHOW: the SignverOD bbox-conversion code cell]

The data engineering here was the hard part. I train on two real, but non-invoice, datasets.
**SignverOD** gives me signature boxes as *normalized* `[x, y, w, h]` coordinates that I convert
to pixels, and I keep only category 1 — signature — dropping categories 2 through 4, which are
initials, redaction, and date, because those aren't what I'm detecting.

[SHOW: the connected-components mask-to-box derivation cell]

**StaVer** is trickier — it ships *no bounding boxes at all*, only binary ground-truth masks. So I
derive boxes myself using `cv2.connectedComponentsWithStats`, and I cross-check every derived
count against the `numStamps` value in each scan's info file as a sanity check that I'm not
under- or over-segmenting stamps.

I trained under the `colab_gpu` profile — 100 epochs, image size 960, batch size 16, patience 20
for early stopping — and evaluate with a confidence threshold of 0.25 and an IoU match threshold
of 0.5, using the team's shared `src/iou.py` so my numbers are directly comparable to Jordan's.

[SHOW: `outputs/metrics/stamp_signature_metrics.json`]

I report precision, recall, and mean IoU **per class**, on a real held-out split — never a single
blended number. ⟪TBD: Diana stamp/signature precision, recall, mean-IoU per class (from
stamp_signature_metrics.json) — training was still finishing at the time of this rehearsal; the
structure and evaluation method you just saw don't change.⟫ Then I run inference on the 750 real invoices — and because neither
SignverOD nor StaVer is actually invoices, that's a real domain gap, so on the invoices I only
report detection counts and confidence distributions, never a precision or recall number, because
there's no invoice-level ground truth to score against.

[SHOW: `outputs/figures/stamp_signature_detection_examples.png`]

---

## Likely Professor Q&A

**Q1: What is IoU, and why do you report it per class instead of overall?**
A: IoU, Intersection-over-Union, measures how well a predicted box overlaps the true box — area of
overlap divided by area of union, from 0 to 1, and a prediction typically counts as correct if IoU
is at least 0.5. I report it per class because stamp and signature are visually and geometrically
different — a signature is often small and irregular, a stamp is usually a compact blob — and a
single blended IoU could hide one class performing much worse than the other.

**Q2: Walk me through deriving boxes from StaVer's masks — what could go wrong?**
A: I binarize the grayscale ground-truth mask, then run connected-component labeling to get
distinct blobs, filtering out anything below a minimum area fraction so noise doesn't become a
false box. What can go wrong: two nearby stamps touching in the mask can get merged into one
component, or a partially faded stamp can get split into two components. That's exactly why I
cross-check the derived box count against each scan's recorded `numStamps` — when they disagree,
it flags exactly this kind of segmentation error.

**Q3: Precision vs. recall — which matters more for a "must be signed" business check, and how do
you tune for it?**
A: For a compliance gate like "must be signed," I'd lean toward prioritizing recall — missing a
real signature (a false negative) means we wrongly tell the business the invoice isn't authorized,
which is the costlier mistake in that direction. I can shift that trade-off by lowering the
confidence threshold, which increases recall at some cost to precision. The two are tunable levers,
not fixed properties of the model.
