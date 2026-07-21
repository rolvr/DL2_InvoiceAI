# Slide Outline

1. **Title** — Invoice Region Detection and Business Parameter Extraction Using CNN, SSD, IoU,
   OCR, and Streamlit. Team names/roles.
2. **Business problem** — Pistac.io-style obligation-readiness: can we tell, automatically,
   whether an invoice has everything needed (stamp/signature, key regions, reference numbers,
   payment terms) to become a structured digital record?
3. **Why this is a CV problem, not just OCR** — pipeline diagram: preprocessing → CNN → SSD-
   style detection → bounding boxes → IoU evaluation → region classification → OCR (only on
   detected crops) → parameter/terms extraction → JSON.
4. **Datasets** — the 4 Kaggle datasets used (invoices, OCR multi-type, SignverOD, StaVer) +
   why a custom annotation subset was needed for regions not covered by public data.
5. **Data pipeline (Rolando)** — ingestion, cleaning, preprocessing (grayscale/resize/denoise/
   deskew), train/val/test split, data quality report.
6. **Stamp & signature detection (Diana)** — architecture, why kept as two separate labels,
   precision/recall/IoU per label, example detections.
7. **Region detection & IoU (Jordan)** — SSD concept explained, chosen implementation
   (SSD or documented YOLOv8 fallback), per-region precision/recall/mean IoU, example
   detections with boxes drawn.
8. **OCR & parameter extraction (Damir)** — why OCR runs only on detected crops, required-
   field checking (PO/order/contract/project/insurance/BoL), payment terms & due-date
   extraction, terms & conditions clause flagging.
9. **Integration & final JSON (Hessam)** — how all outputs merge into one record per invoice,
   the Pistac.io-readiness schema, missing-fields/risk-flags logic.
10. **Live demo** — Streamlit app walkthrough (see `demo_script.md`).
11. **Results summary** — key metrics table (mean IoU per label, stamp/signature P/R/IoU, OCR
    coverage, parameter-detection accuracy on the annotated subset).
12. **Limitations & future work** — dataset-label gaps, generalization beyond the sample
    datasets, SSD-vs-YOLO tradeoff, scaling to full dataset / more required-field types.
13. **Q&A**.
