# Report Log — Diana (Annotation, Stamp Detection, Signature Detection Lead)

_Last updated: 2026-07-23 (final — Colab GPU training and evaluation complete)._

## 1. Objective (what I was responsible for)
Detect stamp and signature as two separate object classes on invoice images, and evaluate
precision/recall/IoU separately per class.

## 2. What I did
- Adapted **SignverOD** (2,765 document images, signature bounding boxes) by converting its
  normalized `[x, y, w, h]` box format to pixel coordinates and keeping only category 1
  (signature) — categories 2-4 (initials, redaction, date) are dropped since they are not the
  classes I'm detecting.
- Adapted **StaVer** (400 document scans, stamp ground-truth **masks**, no boxes) by deriving
  bounding boxes from the binary masks with `cv2.connectedComponentsWithStats`, cross-checking
  each derived count against the scan's recorded `numStamps` value as a sanity check.
- Trained a single **YOLOv8n**, 2-class (`stamp`, `signature`) object detector on the combined,
  converted data.
- Evaluated precision, recall, and mean IoU **per class** (never blended) on a real held-out split
  of SignverOD + StaVer, using the team's shared `src/iou.py` (IoU match threshold 0.5).
- Ran inference on all 750 real invoices in the manifest and reported detection counts only (no
  invoice-level ground truth exists to score against).
- Survived a mid-training GPU-budget exhaustion (see §4) by retraining at a reduced, durable-
  checkpointed budget.

## 3. Approach & key decisions
- **One 2-class YOLOv8n model, not two separate detectors.** Shares a single backbone, trains in
  one pass, and still yields fully independent per-class metrics at evaluation time — so nothing is
  lost by combining stamp and signature at the architecture level, and a downstream business rule
  like "must be signed" can still be evaluated on the signature class alone.
- **YOLOv8n over a two-stage detector (e.g. Faster R-CNN).** A one-stage architecture is faster to
  train and run and is more than accurate enough for two visually distinct, compact marks, and it
  fits comfortably inside a shared-team Colab GPU time budget.
- **Mask-to-box derivation for StaVer**, since the dataset ships no boxes at all — connected-
  component labeling on the binarized mask, with a minimum-area filter to suppress noise, and a
  cross-check against each scan's `numStamps` field to catch merged/split components.

## 4. Challenges faced & how I handled them
- **Challenge:** GPU-budget exhaustion mid-training. The 2-class detector was first launched at the
  `colab_gpu` default (100 epochs, imgsz 960). The Colab GPU allocation ran out at **epoch 86**, and
  because Ultralytics wrote checkpoints to the ephemeral `/content` disk, the entire 86-epoch run
  was lost when the runtime recycled — no resumable state.
  - **Resolution / status:** Retrained at a deliberately reduced budget — **imgsz 640, ≤50
    epochs** — and, critically, changed the training cell to write checkpoints to a **Drive-backed
    run directory with `save_period=10`** and made it **resume-aware**
    (`YOLO(last.pt).train(resume=True)`), so a future disconnect resumes from the last durable
    checkpoint instead of restarting from scratch. This run completed and produced the final metrics
    below.

## 5. Results & metrics
From `outputs/metrics/stamp_signature_metrics.json`:

| Class | Precision | Recall | Mean IoU | tp / fp / fn |
|---|---|---|---|---|
| stamp | 0.903 | 0.875 | 0.822 | 56 / 6 / 8 |
| signature | 0.894 | 0.638 | 0.815 | 673 / 80 / 382 |

Run provenance (`_run` block): `colab_gpu` profile, Tesla T4, epochs ≤50, imgsz 640, batch 16,
2,287 training images, evaluated on a real held-out split of SignverOD + StaVer, confidence
threshold 0.25, IoU match threshold 0.5.

**Invoice inference (750 real invoices, counts only — no ground truth):** 0 of 750 invoices have
any stamp or signature detection (`detections_by_label: {}`). This is the honest, expected result
of applying a document/receipt-trained detector to a corpus of clean, unsigned digital invoice
templates — a property of the invoice corpus, not a failure of the detector, whose own held-out
IoU (0.822 stamp / 0.815 signature) is strong.

## 6. Assumptions & limitations
- **Domain gap.** Neither SignverOD nor StaVer is invoice-native — both are general document
  scans. The detector is trained and evaluated honestly on its own source-domain held-out split,
  then *applied* to invoices as a disclosed domain-transfer step; on invoices I report detection
  counts only, never precision/recall/accuracy, since there is no invoice-level ground truth.
- **Signature recall (0.638) is meaningfully lower than precision (0.894).** The model is
  conservative on signatures — 382 false negatives vs. 80 false positives — which matters if this
  feeds a compliance rule that requires signature evidence; recall can be raised by lowering the
  inference confidence threshold at some cost to precision.
- **Reduced training budget.** The final model trained at ≤50 epochs / imgsz 640 rather than the
  `colab_gpu` default of 100 epochs / imgsz 960, after the GPU-budget exhaustion described above —
  a modest expected trade against peak localisation sharpness for small marks, in exchange for a
  run that reliably completes.

## 7. Handoff notes (for downstream members / integration)
- `outputs/predictions/stamp_signature_predictions.csv` carries per-invoice detections; label
  strings are exactly `"stamp"` and `"signature"` (never merged/renamed), matching
  `visual_elements.stamp_detected` / `signature_detected` in the final JSON contract.
- Model weights: `models/models/stamp_detector/best.pt` and
  `models/models/signature_detector/best.pt` (both point at the same 2-class model).
- Because the invoice corpus yields 0/750 detections, any verdict-policy rule that requires a
  visual mark (Strict preset) will fail-closed for the entire batch — this is expected and
  documented, not an integration bug (see `outputs/reports/final_pipeline_report.md`).

## 8. Figures / artifacts to consider for the slide deck
- `presentation/images/stamp_signature_detection_examples.png` — detector applied to sample
  invoices.
- `presentation/images/diana_BoxPR_curve.png` — box precision-recall curve.
- `presentation/images/diana_confusion_matrix.png` — held-out split confusion matrix.
- `presentation/images/diana_results.png` — full training/validation curves across all epochs.
- `presentation/images/diana_val_batch0_pred.jpg` — predictions on a validation batch.
- `presentation/images/metrics_per_class.png` — grouped precision/recall/mean-IoU bars alongside
  Jordan's per-class chart.
