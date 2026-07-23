# region_detector

YOLOv8n, 5 classes: ['company', 'date', 'address', 'total', 'other_text']

Trained on the OCR Dataset of Multi-type Documents (real polygon boxes; entity text matched to box text to assign field labels).
Profile colab_gpu: epochs=100, imgsz=960.

Metrics: {"company": {"precision": 0.8966, "recall": 0.8189, "mean_iou": 0.8942, "support": 127}, "date": {"precision": 0.7559, "recall": 0.8546, "mean_iou": 0.812, "support": 337}, "address": {"precision": 0.8804, "recall": 0.8831, "mean_iou": 0.8956, "support": 325}, "total": {"precision": 0.7634, "recall": 0.7832, "mean_iou": 0.8867, "support": 309}, "other_text": {"precision": 0.9107, "recall": 0.967, "mean_iou": 0.8769, "support": 4153}}
