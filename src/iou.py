"""
iou.py — shared Intersection-over-Union implementation.

Owner: Jordan (region detection / IoU evaluation). This is the SINGLE implementation of IoU
for the whole project — Diana, Jordan, Damir, and Hessam should all import from here rather
than writing their own, so evaluation numbers are directly comparable across notebooks.
"""

import numpy as np
import pandas as pd


def compute_iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    """IoU between two boxes in (xmin, ymin, xmax, ymax) format. Returns 0.0 if either box
    has zero or negative area, or if they don't overlap."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def match_predictions_to_ground_truth(
    pred_boxes: list[tuple[float, float, float, float]],
    gt_boxes: list[tuple[float, float, float, float]],
    iou_threshold: float = 0.5,
) -> list[dict]:
    """Greedy one-to-one matching of predicted boxes to ground-truth boxes by descending IoU.

    Returns a list of {"pred_idx", "gt_idx", "iou", "is_match"} dicts — one entry per
    predicted box. Unmatched ground-truth boxes (false negatives) are not represented here;
    compute those separately as gt indices not present in any "gt_idx".
    """
    results = []
    used_gt = set()

    # Precompute all pairwise IoUs, then greedily assign highest-IoU pairs first.
    pairs = []
    for p_idx, p_box in enumerate(pred_boxes):
        for g_idx, g_box in enumerate(gt_boxes):
            iou = compute_iou(p_box, g_box)
            pairs.append((iou, p_idx, g_idx))
    pairs.sort(key=lambda x: x[0], reverse=True)

    matched_pred = set()
    assignment = {}
    for iou, p_idx, g_idx in pairs:
        if p_idx in matched_pred or g_idx in used_gt:
            continue
        if iou <= 0:
            continue
        matched_pred.add(p_idx)
        used_gt.add(g_idx)
        assignment[p_idx] = (g_idx, iou)

    for p_idx in range(len(pred_boxes)):
        if p_idx in assignment:
            g_idx, iou = assignment[p_idx]
            results.append({
                "pred_idx": p_idx,
                "gt_idx": g_idx,
                "iou": iou,
                "is_match": iou >= iou_threshold,
            })
        else:
            results.append({"pred_idx": p_idx, "gt_idx": None, "iou": 0.0, "is_match": False})

    return results


def precision_recall_iou(
    pred_boxes: list[tuple[float, float, float, float]],
    gt_boxes: list[tuple[float, float, float, float]],
    iou_threshold: float = 0.5,
) -> dict:
    """Single-image precision/recall/mean-IoU summary for one label."""
    if not pred_boxes and not gt_boxes:
        return {"precision": None, "recall": None, "mean_iou": None, "n_pred": 0, "n_gt": 0}

    matches = match_predictions_to_ground_truth(pred_boxes, gt_boxes, iou_threshold)
    true_positives = sum(1 for m in matches if m["is_match"])
    n_pred = len(pred_boxes)
    n_gt = len(gt_boxes)

    precision = true_positives / n_pred if n_pred else 0.0
    recall = true_positives / n_gt if n_gt else 0.0
    ious = [m["iou"] for m in matches if m["iou"] > 0]
    mean_iou = float(np.mean(ious)) if ious else 0.0

    return {"precision": precision, "recall": recall, "mean_iou": mean_iou, "n_pred": n_pred, "n_gt": n_gt}


def evaluate_predictions_df(
    predictions: pd.DataFrame,
    ground_truth: pd.DataFrame,
    labels: list[str],
    iou_threshold: float = 0.5,
) -> dict:
    """Aggregate precision/recall/mean-IoU per label across an entire predictions vs.
    ground-truth dataframe pair (both must have document_id, label, xmin, ymin, xmax, ymax).

    Returns {"per_label": {label: {...}}, "overall_mean_iou": float}
    """
    per_label = {}
    all_ious = []

    for label in labels:
        pred_label = predictions[predictions["label"] == label]
        gt_label = ground_truth[ground_truth["label"] == label]
        doc_ids = set(pred_label["document_id"]) | set(gt_label["document_id"])

        label_ious, tp_total, pred_total, gt_total = [], 0, 0, 0
        for doc_id in doc_ids:
            p_boxes = pred_label[pred_label["document_id"] == doc_id][["xmin", "ymin", "xmax", "ymax"]].values.tolist()
            g_boxes = gt_label[gt_label["document_id"] == doc_id][["xmin", "ymin", "xmax", "ymax"]].values.tolist()
            result = precision_recall_iou(p_boxes, g_boxes, iou_threshold)
            if result["mean_iou"] is not None:
                label_ious.append(result["mean_iou"])
            tp_total += int(result["precision"] * result["n_pred"]) if result["n_pred"] else 0
            pred_total += result["n_pred"]
            gt_total += result["n_gt"]

        mean_iou = float(np.mean(label_ious)) if label_ious else None
        precision = tp_total / pred_total if pred_total else None
        recall = tp_total / gt_total if gt_total else None

        per_label[label] = {"precision": precision, "recall": recall, "mean_iou": mean_iou}
        if mean_iou is not None:
            all_ious.append(mean_iou)

    return {
        "per_label": per_label,
        "overall_mean_iou": float(np.mean(all_ious)) if all_ious else None,
    }
