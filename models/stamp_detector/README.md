# stamp_detector

Single YOLOv8n **2-class** model (`stamp`, `signature`); the same weights are stored under both folder names to satisfy the output contract.

Trained on real SignverOD (category_id==1) + StaVer (boxes derived from GT masks).
Profile `colab_gpu`: epochs=50, imgsz=640, batch=16.

Metrics: {"stamp": {"precision": 0.9032, "recall": 0.875, "mean_iou": 0.822, "tp": 56, "fp": 6, "fn": 8}, "signature": {"precision": 0.8938, "recall": 0.6379, "mean_iou": 0.8148, "tp": 673, "fp": 80, "fn": 382}}
