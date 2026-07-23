# Report Log — Jordan (Invoice Region Detection, SSD/CNN, IoU Evaluation Lead)

_Last updated: 2026-07-23 (final — Colab GPU training and evaluation complete)._

## 1. Objective (what I was responsible for)
Detect invoice business regions using SSD-style object detection and evaluate predictions
against ground truth with IoU. Core Deep Learning II deliverable.

## 2. What I did
- Trained a **YOLOv8n**, 5-class (`company`, `date`, `address`, `total`, `other_text`) region
  detector on the **OCR Dataset of Multi-type Documents** (973 real receipt images, 52,331 real
  polygon text boxes).
- Solved the core data-engineering problem: the dataset gives text *boxes with no class label*
  and, separately, per-document entity *values* (company/date/address/total) with *no
  coordinates*. Neither half is directly usable as detection training data alone.
- Built a **fuzzy-matching label-construction step** (`rapidfuzz`, max of `partial_ratio` and
  `ratio`, threshold **88**) that joins every text box to its best-matching entity value, or tags
  it `other_text` if nothing clears the threshold — turning 52,331 unlabelled boxes into a genuine
  5-class training set with real geometry, no hand-annotation required.
- Evaluated **per-class** precision, recall, and mean IoU (never a single blended mAP) on the
  dataset's own official test split (98 images), using the team's shared `src/iou.py`.
- Ran inference on all 750 real invoices (`source="invoice"`) and reported the result as a
  disclosed domain-shift count (receipts ~460px wide vs. full-page invoices 1654×2339), not an
  accuracy claim.

## 3. Approach & key decisions
- **YOLOv8n (documented as the SSD-family implementation used)** — a one-stage detector, fast to
  train under the shared Colab budget and sufficient for 5-class region localisation at this
  resolution.
- **Fuzzy-match threshold of 88** was chosen empirically to balance false matches (near-duplicate
  or substring text incorrectly assigned a field label) against missed matches (real field text
  that fails to clear a stricter threshold and falls into `other_text`); the resulting class
  distribution was inspected to sanity-check the matching behaved sensibly before training.
- **Per-class reporting, never one blended mAP** — a deliberate methodological choice given the
  severe class imbalance (see §4), so that a dominant class can never mask weak performance on a
  business-critical minority class.

## 4. Challenges faced & how I handled them
- **Challenge:** Severe class imbalance — `other_text` (support 4,153 boxes in the test split)
  massively outnumbers the four named field classes (company 127, date 337, address 325, total
  309), since most text on a receipt isn't the company, date, address, or total. A single blended
  metric (e.g. overall mAP) would be dominated by `other_text` and could hide poor performance on
  the rarer, business-critical classes.
  - **Resolution / status:** Report precision, recall, and mean IoU **per class**, plus a
    macro-averaged mean IoU across classes (0.873) that weights every class equally regardless of
    support — never a single support-weighted number that `other_text` would dominate.
- **Challenge:** No public dataset offers full-page invoices with real polygon-annotated business
  regions — the best available real, labelled ground truth is receipt-domain.
  - **Resolution / status:** Train and evaluate on the OCR Dataset's real held-out split (a
    legitimate, real metric), then apply the resulting detector to invoices as an explicitly
    disclosed domain-transfer step, reporting invoice results as detection counts only.

## 5. Results & metrics
From `outputs/metrics/region_iou_metrics.json` (OCR Dataset official test split, 98 images):

| Class | Precision | Recall | Mean IoU | Support |
|---|---|---|---|---|
| company | 0.897 | 0.819 | 0.894 | 127 |
| date | 0.756 | 0.855 | 0.812 | 337 |
| address | 0.880 | 0.883 | 0.896 | 325 |
| total | 0.763 | 0.783 | 0.887 | 309 |
| other_text | 0.911 | 0.967 | 0.877 | 4,153 |
| **Macro mean IoU** | — | — | **0.873** | — |

Run provenance (`_run` block): `colab_gpu` profile, Tesla T4, epochs 100, imgsz 960, batch 16,
778 training images, confidence threshold 0.25, IoU match threshold 0.5.

**Invoice inference (domain shift, counts only):** 750 of 750 invoices carry at least one region
detection (`invoices_with_regions: 750`) — unlike a visual mark, business-text regions transfer
usefully across the receipt→invoice domain shift even without invoice-native training data.

## 6. Assumptions & limitations
- **Domain gap.** Trained and evaluated on receipts (~460px wide); applied to full-page invoices
  (1654×2339). This is a real, disclosed domain shift; the per-class table above is a legitimate
  metric on the *source* domain, not a claim about invoice-domain accuracy.
- **Fuzzy-match label construction is a heuristic, not hand annotation.** It can mislabel a box
  whose text happens to resemble an entity value by coincidence, or when two nearby boxes have
  similar text; the class-distribution sanity check mitigates but does not eliminate this.
- **`date` has the lowest precision (0.756)** of the four named classes — plausible given dates are
  short, numeric, and easy to confuse with other short numeric text on a receipt.

## 7. Handoff notes (for downstream members / integration)
- `outputs/predictions/region_predictions.csv` schema carries per-box detections keyed by
  `document_id`; labels are exactly `company`, `date`, `address`, `total`, `other_text`.
- `src/iou.py` is the shared IoU implementation used identically by Diana and me — numbers are
  directly comparable across both stages.
- My `company`/`date`/`address`/`total` boxes have a second life in the app: cropping and OCR-ing
  just those regions gives a field localiser that feeds the verdict engine's date signal and a
  "where is this field, and what does it say" overlay. Note my label vocabulary is a
  receipt-entity schema, distinct from the obligation-region schema in
  `config/label_schema.json`, so the verdict engine does not depend on my labels directly.

## 8. Figures / artifacts to consider for the slide deck
- `presentation/images/region_detection_examples.png` — detector applied to sample invoices.
- `presentation/images/metrics_per_class.png` — grouped precision/recall/mean-IoU bars for all
  5 classes, alongside Diana's stamp/signature chart.
- An IoU explainer diagram/box overlap visual if time allows in the live talk.
