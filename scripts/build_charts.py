"""
Generate the report/deck summary charts from the authoritative metrics JSONs.

Reads (never edits):
  outputs/metrics/stamp_signature_metrics.json   (Diana)
  outputs/metrics/region_iou_metrics.json        (Jordan)
  outputs/reports/final_pipeline_report.md       (Hessam integration - readiness by policy)

Writes (overwrites in place - idempotent, re-runnable):
  presentation/images/metrics_per_class.png
  presentation/images/readiness_by_policy.png
  presentation/images/compute_profiles.png

CPU-only. No GPU, no notebook, no network. matplotlib only.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

REPO = Path(__file__).resolve().parents[1]
METRICS_DIR = REPO / "outputs" / "metrics"
IMAGES_DIR = REPO / "presentation" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# --- shared style: dataviz-skill reference palette (light mode, categorical slots) ---
BLUE = "#2a78d6"      # slot 1 - precision
ORANGE = "#eb6834"    # slot 2 - recall
AQUA = "#1baf7a"       # slot 3 - mean IoU
YELLOW = "#eda100"    # slot 4
MAGENTA = "#e87ba4"   # slot 5

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
WARNING = "#fab219"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_SECONDARY,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "text.color": INK_PRIMARY,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def load_json(name):
    with open(METRICS_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def bar_value_labels(ax, bars, fmt="{:.3f}"):
    for b in bars:
        h = b.get_height()
        ax.annotate(
            fmt.format(h),
            xy=(b.get_x() + b.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=INK_SECONDARY,
        )


def chart_metrics_per_class():
    diana = load_json("stamp_signature_metrics.json")
    jordan = load_json("region_iou_metrics.json")

    diana_classes = ["stamp", "signature"]
    diana_p = [diana[c]["precision"] for c in diana_classes]
    diana_r = [diana[c]["recall"] for c in diana_classes]
    diana_iou = [diana[c]["mean_iou"] for c in diana_classes]

    jordan_classes = ["company", "date", "address", "total", "other_text"]
    jp = jordan["per_class"]
    jordan_p = [jp[c]["precision"] for c in jordan_classes]
    jordan_r = [jp[c]["recall"] for c in jordan_classes]
    jordan_iou = [jp[c]["mean_iou"] for c in jordan_classes]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), width_ratios=[2, 5])
    fig.suptitle(
        "Per-Class Precision / Recall / Mean IoU — Diana (stamp/signature) & Jordan (regions)",
        fontsize=13, color=INK_PRIMARY, y=1.02,
    )

    for ax, classes, p, r, iou, title in [
        (axes[0], diana_classes, diana_p, diana_r, diana_iou,
         "Diana — stamp & signature\n(held-out SignverOD + StaVer split)"),
        (axes[1], jordan_classes, jordan_p, jordan_r, jordan_iou,
         "Jordan — 5-class regions\n(OCR Dataset official test split, 98 imgs)"),
    ]:
        n = len(classes)
        x = range(n)
        w = 0.26
        b1 = ax.bar([i - w for i in x], p, width=w, label="Precision", color=BLUE)
        b2 = ax.bar([i for i in x], r, width=w, label="Recall", color=ORANGE)
        b3 = ax.bar([i + w for i in x], iou, width=w, label="Mean IoU", color=AQUA)
        bar_value_labels(ax, b1)
        bar_value_labels(ax, b2)
        bar_value_labels(ax, b3)
        ax.set_xticks(list(x))
        ax.set_xticklabels(classes, rotation=0 if n <= 2 else 20, ha="center" if n <= 2 else "right")
        ax.set_ylim(0, 1.08)
        ax.set_title(title, fontsize=10.5, color=INK_SECONDARY)
        ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(BASELINE)
        ax.spines["bottom"].set_color(BASELINE)

    axes[1].axhline(jordan["macro_mean_iou"], color=INK_MUTED, linestyle="--", linewidth=1.2, zorder=4)
    axes[1].annotate(
        f"macro mean IoU = {jordan['macro_mean_iou']:.3f}",
        xy=(0.01, 0.995), xycoords="axes fraction",
        ha="left", va="top", fontsize=8.5, color=INK_MUTED,
    )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.04), fontsize=10)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    out = IMAGES_DIR / "metrics_per_class.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def chart_readiness_by_policy():
    # Cross-checked, authoritative values from outputs/reports/final_pipeline_report.md
    policies = ["Lenient", "Default", "Strict"]
    ready = [750, 475, 0]
    total = 750
    pct = [r / total * 100 for r in ready]
    colors = [GOOD, WARNING, CRITICAL]

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    bars = ax.bar(policies, pct, color=colors, width=0.55, zorder=3)
    for b, r, p in zip(bars, ready, pct):
        ax.annotate(
            f"{p:.1f}%\n({r} / 750)",
            xy=(b.get_x() + b.get_width() / 2, b.get_height()),
            xytext=(0, 6), textcoords="offset points",
            ha="center", va="bottom", fontsize=11, color=INK_PRIMARY, fontweight="bold",
        )
    ax.set_ylim(0, 115)
    ax.set_ylabel("Invoices marked Ready (%)")
    ax.set_title("Obligation-Readiness by Verdict Policy (750 invoices)", fontsize=13, pad=14)
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)

    ax.annotate(
        "Strict = 0% is honest, not a bug: this invoice corpus is clean,\n"
        "unsigned digital templates, and Strict policy requires a visual mark\n"
        "(stamp AND signature). Diana's detector finds 0/750 marks on this\n"
        "corpus while still scoring stamp IoU 0.82 / signature IoU 0.81 on its\n"
        "own held-out (non-invoice) evaluation split — a fail-closed, correct\n"
        "verdict given what the corpus actually contains.",
        xy=(0.5, -0.30), xycoords="axes fraction",
        ha="center", va="top", fontsize=8.7, color=INK_SECONDARY,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f4f3f0", edgecolor=GRIDLINE),
    )
    fig.tight_layout()
    out = IMAGES_DIR / "readiness_by_policy.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def chart_compute_profiles():
    diana = load_json("stamp_signature_metrics.json")["_run"]
    jordan = load_json("region_iou_metrics.json")["_run"]

    members = ["Diana\n(stamp/signature)", "Jordan\n(regions)"]
    wall_min = [diana["wall_clock_sec"] / 60.0, jordan["wall_clock_sec"] / 60.0]
    epochs = [diana["epochs"], jordan["epochs"]]
    imgsz = [diana["imgsz"], jordan["imgsz"]]

    # Three single-axis small multiples (never a dual/twin y-axis - two measures of
    # different scale get their own panel, indexed to nothing but their own units).
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.0))

    b = axes[0].bar(members, wall_min, color=[BLUE, ORANGE], width=0.5, zorder=3)
    bar_value_labels(axes[0], b, fmt="{:.0f} min")
    axes[0].set_ylabel("Wall-clock training time (minutes)")
    axes[0].set_title("Wall-clock time", fontsize=11.5)

    b1 = axes[1].bar(members, epochs, color=[BLUE, ORANGE], width=0.5, zorder=3)
    bar_value_labels(axes[1], b1, fmt="{:.0f}")
    axes[1].set_ylabel("epochs")
    axes[1].set_title("Training epochs", fontsize=11.5)

    b2 = axes[2].bar(members, imgsz, color=[BLUE, ORANGE], width=0.5, zorder=3)
    bar_value_labels(axes[2], b2, fmt="{:.0f} px")
    axes[2].set_ylabel("imgsz (px)")
    axes[2].set_title("Input image size", fontsize=11.5)

    for ax in axes:
        ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(BASELINE)
        ax.spines["bottom"].set_color(BASELINE)

    fig.suptitle(
        "Compute Budget: Diana (≤50 ep / imgsz 640, post GPU-exhaustion budget cut) vs.\n"
        "Jordan (100 ep / imgsz 960, full colab_gpu default) — both on a Colab Tesla T4",
        fontsize=11, y=1.05,
    )
    fig.tight_layout()
    out = IMAGES_DIR / "compute_profiles.png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    chart_metrics_per_class()
    chart_readiness_by_policy()
    chart_compute_profiles()
    print("Done. All charts written to", IMAGES_DIR)


if __name__ == "__main__":
    main()
