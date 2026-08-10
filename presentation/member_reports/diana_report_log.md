# Diana — Stamp & Signature Detection · Report Log

> Destination in repo: `presentation/member_reports/diana_report_log.md`
> Raw material for the group report + slide deck. Numbers are from the final run
> `stamp_sig_768_defaug` (YOLOv8n, imgsz 768, 75 epochs, Tesla T4).

## Role
Detect **stamp** and **signature** as two separate classes on document images and evaluate
per class (precision / recall / mean-IoU) on a real held-out split. Two labels are kept
strictly separate — the final JSON, Streamlit UI, and readiness logic all depend on it.

## Model & method
- **YOLOv8n**, a single **2-class** detector (`stamp`, `signature`) — one shared backbone,
  one-stage, fast enough for the Colab budget.
- Trained on real data: **SignverOD** (signatures; `category_id == 1` only) and **StaVer**
  (stamps; boxes *derived from binary GT masks* via connected components).
- Dataset built: **2,287 train / 458 val** images.

## Key parameters (final run)
`imgsz=768`, `epochs=75`, `batch=16`, `patience=20`, YOLO default augmentation **with
rotation & shear disabled** (`degrees=0, shear=0`), `save_period=5` (Drive checkpoints),
eval `conf=0.25`, IoU match threshold `0.5`. Wall-clock ≈ 3.5 h on a T4.

## Final results (real held-out split of SignverOD + StaVer)

| Class | Precision | Recall | mean-IoU | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| **Stamp** | 0.906 | 0.906 | 0.815 | 0.923 | 0.61 |
| **Signature** | 0.897 | 0.636 | 0.819 | 0.687 | 0.42 |
| Overall (val) | — | — | — | 0.805 | 0.515 |

Confidence sweep (0.15 / 0.25 / 0.40): signature recall is **flat** (0.644 → 0.636 → 0.632),
so `conf=0.25` was kept (best stamp precision at equal recall).

**Invoice inference:** 0 / 750 detections — the invoice corpus is clean digital templates
with no stamps or signatures. Reported as counts only (no invoice-level ground truth).

## What we learned (experiments)
Three controlled runs isolated the drivers of IoU:

| Run | Config | Stamp IoU | Sig IoU |
|---|---|---|---|
| Baseline | 640 / 50, default aug | 0.82 | 0.81 |
| Attempt 2 | 768 / 75, + rotation & shear | 0.803 | 0.804 |
| **Final** | **768 / 75, default aug, no rotation/shear** | **0.815** | **0.819** |

- Adding geometric distortion (rotation/shear) **lowered** IoU on this small, clean dataset.
- Removing it while keeping the higher resolution gave the best result and the best
  precision/recall for stamp (0.91 / 0.91).
- IoU is at the **data ceiling (~0.82)** — added resolution and epochs did not move it.

## Honest limitations
Stamp detection is strong (P/R ≈ 0.91, mAP₅₀ 0.92, IoU 0.82). Signature localization is
comparable (IoU 0.82) but **recall plateaus at ~0.64** — the confidence sweep (0.15–0.40)
showed recall is threshold-insensitive, so these are genuine missed detections, not filtering.
The remaining bottlenecks are SignverOD's small/faint signatures, StaVer's derived-from-mask
boxes (only 88.5% match the expected stamp count), and the document→invoice **domain gap** —
not the training recipe.

## Handoff
`stamp_signature_predictions.csv` + `stamp_signature_metrics.json` + weights published to
`outputs/diana/` and `inputs/upstream/diana/`. Feeds `visual_elements.stamp_detected /
signature_detected` and `model_metrics.stamp_iou / signature_iou` in the final JSON (Hessam).

## Q&A rehearsal
- **What is IoU / mean-IoU?** Overlap of predicted vs true box (0–1); we average it over
  correctly matched boxes (match = IoU ≥ 0.5).
- **Why per-class metrics?** Stamp and signature behave very differently (stamp strong,
  signature recall-limited); an overall number would hide that.
- **Why derive stamp boxes from masks?** StaVer ships no boxes — only binary masks — so boxes
  come from connected-components, cross-checked against the `numStamps` count (88.5% match).
- **Precision vs recall trade-off for a "must be signed" check?** We tested it directly — a
  confidence sweep didn't recover signature recall, so the misses are real, not a threshold choice.
