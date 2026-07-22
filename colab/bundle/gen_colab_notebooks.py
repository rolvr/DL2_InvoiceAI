"""Generate the five per-member Colab notebooks into colab/notebooks/.

All five share one skeleton (title -> GPU check -> bootstrap -> profile -> Kaggle data ->
stage work -> metrics with _run block -> publish -> report-log prompts) so they behave
consistently and a member who has run one can run any of them.
"""
from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

REPO = Path(r"C:\Users\hessa\OneDrive\Dropbox Backup\WorkSpace\GBC_AIML_Dev_2026\Deep Learning II\invoice-image-processing")
OUT = REPO / "colab" / "notebooks"

SLUG_INVOICES = "osamahosamabdellatif/high-quality-invoice-images-for-ocr"
SLUG_OCRSET = "senju14/ocr-dataset-of-multi-type-documents"
SLUG_SIGN = "victordibia/signverod"
SLUG_STAMP = "rtatman/stamp-verification-staver-dataset"


def md(t):
    return nbf.v4.new_markdown_cell(t)


def co(t):
    return nbf.v4.new_code_cell(t)


# ----------------------------------------------------------------- shared cells
def c_title(num, member, role, what, inputs, outputs, runtime):
    return md(f"""# {num} — {member}: {role}

**Google Colab notebook.** Runtime → *Change runtime type* → **GPU (T4 / L4 / A100)** before running.

{what}

| | |
|---|---|
| **Inputs** | {inputs} |
| **Outputs** | {outputs} |
| **Expected runtime** | {runtime} |
| **Compute profile** | `colab_gpu` (generous — full data, pinned in the profile cell) |

### How results get back to the team
Everything is written to Google Drive by `colab_bootstrap.publish()`, into **both**:
- `outputs/{member.lower()}/<kind>/` — the *latest* copy
- `runs/{member.lower()}/<UTC-timestamp>/<kind>/` — an immutable archive, so re-running never
  silently destroys an earlier result

Tell the integrator (Hessam) when you're done; he copies from `outputs/` into the repo.

> **Before you run:** `MyDrive/DL2_InvoiceAI/` must already contain `code/` (the repo's `src/`,
> `scripts/`, and `colab_bootstrap.py`) and `inputs/`. If it doesn't, the bootstrap cell fails
> fast with a message telling you exactly what's missing.""")


def c_gpu():
    return co("""# --- GPU check: stop here if this says "no GPU" ---------------------------------
import subprocess
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout or
      "!! NO GPU. Runtime > Change runtime type > Hardware accelerator = GPU, then re-run.")
import torch
print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available(),
      "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only")""")


def c_bootstrap(deps):
    d = ", ".join(f'"{x}"' for x in deps)
    return co(f"""# --- Mount Drive + load the shared bootstrap -----------------------------------
DRIVE_ROOT = "/content/drive/MyDrive/DL2_InvoiceAI"   # <-- change if your folder differs

import sys, os, shutil, json, time
from pathlib import Path
from google.colab import drive
drive.mount("/content/drive")

_bs = Path(DRIVE_ROOT) / "code" / "colab_bootstrap.py"
assert _bs.exists(), (
    f"Missing {{_bs}}.\\nUpload the repo's colab/colab_bootstrap.py into "
    f"{{DRIVE_ROOT}}/code/ and re-run this cell."
)
sys.path.insert(0, str(_bs.parent))
import colab_bootstrap as CB

root  = CB.mount_drive(DRIVE_ROOT)
paths = CB.setup_paths(root)
CB.install_deps({d})
print("Drive root:", root)""")


def c_profile():
    return co("""# --- Pin the generous Colab budget --------------------------------------------
os.environ["IIP_COMPUTE_PROFILE"] = "colab_gpu"
from src.compute_profile import get_profile

P = get_profile()
print(json.dumps(P, indent=2, default=str))

RUN_TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())   # one archive folder for this run
T0 = time.time()""")


def c_drive_data(required: dict, note=""):
    """Datasets are read from Google Drive (pre-downloaded), so no Kaggle token is needed."""
    checks = "\n".join(f'    DATA / "{p}",' for p in required.values())
    shows = "\n".join(
        f'print(f"  {k:<12s}", DATA / "{v}", "->",'
        f' sum(1 for _ in (DATA / "{v}").rglob("*") if _.is_file()), "files")'
        for k, v in required.items()
    )
    return co(f"""# --- Datasets: read straight from Google Drive (NO Kaggle token needed) ------
# {note}
DATA = paths.inputs / "datasets"

CB.verify_inputs([
{checks}
])

print("datasets found in Drive:")
{shows}""")


def c_runblock(member, extra=""):
    return co(f"""# --- Provenance: the _run block makes cross-run model comparison possible ------
def run_block(**kw):
    \"\"\"Stamp every metrics JSON with how it was produced, so local-CPU and Colab-GPU
    results can be charted against each other later.\"\"\"
    b = {{
        "profile": P.get("profile_name", "colab_gpu"),
        "device": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"),
        "epochs": P.get("epochs"), "imgsz": P.get("imgsz"), "batch": P.get("batch"),
        "wall_clock_sec": round(time.time() - T0, 1),
        "timestamp_utc": RUN_TS, "member": "{member}",
    }}
    b.update(kw)
    return b
{extra}""")


def c_report(member, prompts):
    items = "\n".join(f"{i}. {p}" for i, p in enumerate(prompts, 1))
    return md(f"""## Report log — fill this in before you finish

Copy your answers into `presentation/member_reports/{member}_report_log.md` in the repo (or paste
them to the integrator). This is the raw material for the group report and slide deck, so be
specific and **honest about what didn't work**.

{items}

Also note anything the next stage needs from you, and which figure you'd put on a slide.""")


def c_publish(member, items, note=""):
    body = "\n".join(
        f'    ("{k}", {v}),' for k, v in items.items()
    )
    return co(f"""# --- Publish to Drive (latest + immutable archive) -----------------------------
# {note}
to_publish = [
{body}
]
for kind, src in to_publish:
    if src is None:
        continue
    p = Path(src)
    if not p.exists():
        print(f"  skip (not produced): {{p}}")
        continue
    CB.publish("{member}", p, kind, paths=paths, run_timestamp=RUN_TS)

print("\\nLatest ->", paths.outputs("{member}"))
print("Archive ->", paths.run_dir("{member}", timestamp=RUN_TS))""")


# ================================================================= 01 ROLANDO
def nb_rolando():
    c = [
        c_title("01", "Rolando", "Data Ingestion & Annotation-Aware Manifest",
                "Builds the invoice manifest that every other stage depends on. **This version "
                "samples annotation-aware**, so the manifest carries OCR/field ground truth "
                "instead of the 26% coverage the first local run produced.",
                "Drive `inputs/datasets/invoices_raw/` (optional — see note)",
                "`invoice_manifest.csv`, QA report, 2 figures",
                "~10–20 min (optional — the manifest was already built locally)"),
        md("""### Why this notebook exists

The first manifest stratified across all three batches for *visual diversity*, blind to labels.
But annotation CSVs exist **only for batch_1** — so only **197 of 750 images (26.3%)** had ground
truth, and just 26 in the test split. That is too thin to report an OCR or field-extraction score on.

Two corrections here:
1. **Annotation-aware sampling** — prefer images that have a row in the batch_1 annotation CSVs,
   lifting GT coverage toward ~100%.
2. **Skip the duplicates** — `batch_3/` contains full copies of `batch_1/` and `batch_2/` beside
   its own `batch3_*` folders. True unique images = **5,201**, not the 8,181 you get by counting
   everything. Sampling the duplicates would put the same invoice in train *and* test."""),
        c_gpu(),
        c_bootstrap(["pandas", "pillow", "tqdm"]),
        c_profile(),
        c_drive_data({"invoices_raw": "invoices_raw"},
                     "OPTIONAL stage: the manifest in inputs/ was already produced from this "
                     "data locally. You only need invoices_raw/ in Drive if you want to "
                     "re-derive the manifest yourself."),
        co("""# --- Locate the real batch folders, excluding batch_3's duplicate copies ------
import pandas as pd
from PIL import Image

RAW = DATA / "invoices_raw"
roots = [p for p in RAW.rglob("batch*_*") if p.is_dir() and any(p.glob("*.jpg"))]

# batch_3/batch_1/* and batch_3/batch_2/* duplicate batches 1 and 2 - drop them.
def is_dup(p: Path) -> bool:
    parts = p.parts
    return "batch_3" in parts and not any(x.startswith("batch3_") for x in parts)

leaf = sorted([p for p in roots if not is_dup(p)])
dups = sorted([p for p in roots if is_dup(p)])

print("USING these leaf folders:")
for p in leaf:
    print(f"  {p.relative_to(RAW)}: {len(list(p.glob('*.jpg')))}")
print(f"\\nEXCLUDED {len(dups)} duplicate folders "
      f"({sum(len(list(p.glob('*.jpg'))) for p in dups)} images)")
print("unique images:", sum(len(list(p.glob('*.jpg'))) for p in leaf))"""),
        co("""# --- Load the batch_1 annotation CSVs = the only real ground truth ------------
ann_csvs = sorted(RAW.rglob("batch1_*.csv"))
print("annotation CSVs:", [p.name for p in ann_csvs])

gt = pd.concat([pd.read_csv(p) for p in ann_csvs], ignore_index=True)
gt["stem"] = gt["File Name"].astype(str).str.replace(".jpg", "", regex=False).str.strip()
gt = gt.drop_duplicates("stem")
annotated = set(gt["stem"])

print("columns      :", list(gt.columns))
print("annotated ids:", len(annotated))
print("\\nJson Data holds invoice / items / subtotal / payment_instructions;")
print("OCRed Text holds the page-level transcription. Both are REAL ground truth.")
gt.head(2)"""),
        co("""# --- Annotation-aware sample -------------------------------------------------
TARGET = 750
SEED = 42

rows = []
for d in leaf:
    for img in sorted(d.glob("*.jpg")):
        rows.append({"document_id": img.stem, "src": img,
                     "batch": d.name, "has_gt": img.stem in annotated})
allimgs = pd.DataFrame(rows)
print("total unique images:", len(allimgs), "| with GT:", int(allimgs.has_gt.sum()))

# Take every annotated image first, then top up with unannotated ones for visual variety.
have = allimgs[allimgs.has_gt]
rest = allimgs[~allimgs.has_gt]
take_gt = have.sample(min(TARGET, len(have)), random_state=SEED)
need = TARGET - len(take_gt)
sample = pd.concat([take_gt,
                    rest.groupby("batch", group_keys=False)
                        .apply(lambda g: g.sample(max(1, need // rest.batch.nunique()),
                                                  random_state=SEED))
                    ][: 2 if need > 0 else 1]).head(TARGET).reset_index(drop=True)

cov = sample.has_gt.mean()
print(f"sampled {len(sample)} | GT coverage {cov:.1%}  (was 26.3%)")
assert sample.document_id.is_unique, "document_id collision - check the duplicate filter"
sample.batch.value_counts()"""),
        co("""# --- Build the contracted manifest -------------------------------------------
from tqdm.auto import tqdm

STAGE = Path("/content/out"); (STAGE / "images").mkdir(parents=True, exist_ok=True)
recs = []
for r in tqdm(sample.itertuples(), total=len(sample)):
    try:
        with Image.open(r.src) as im:
            w, h = im.size
        corrupt = False
    except Exception:
        w = h = 0; corrupt = True
    dst = STAGE / "images" / f"{r.document_id}.jpg"
    shutil.copyfile(r.src, dst)
    recs.append({"document_id": r.document_id, "image_path": f"inputs/images/{dst.name}",
                 "width": w, "height": h, "file_type": "jpg",
                 "is_corrupt": corrupt, "split": None, "has_ground_truth": r.has_gt})

man = pd.DataFrame(recs)

# Stratify the split by GT availability so the test set is not starved of labels.
import numpy as np
rng = np.random.default_rng(SEED)
man["split"] = "train"
for flag in [True, False]:
    idx = man.index[man.has_ground_truth == flag].to_numpy()
    rng.shuffle(idx)
    n = len(idx)
    man.loc[idx[: int(.16 * n)], "split"] = "val"
    man.loc[idx[int(.16 * n): int(.30 * n)], "split"] = "test"

man.to_csv(STAGE / "invoice_manifest.csv", index=False)
print(man.split.value_counts().to_dict())
print("GT coverage per split:")
print(man.groupby("split").has_ground_truth.mean().round(3))"""),
        co("""# --- Figures + data-quality report -------------------------------------------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG = Path("/content/out/figures"); FIG.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(3, 4, figsize=(14, 10))
for a, r in zip(ax.ravel(), man.sample(12, random_state=SEED).itertuples()):
    a.imshow(Image.open(STAGE / "images" / f"{r.document_id}.jpg")); a.axis("off")
    a.set_title(f"{r.document_id}\\n{'GT' if r.has_ground_truth else 'no GT'}", fontsize=8)
fig.suptitle("Sample of the annotation-aware invoice manifest", fontsize=13)
fig.tight_layout(); fig.savefig(FIG / "sample_invoice_grid.png", dpi=150); plt.close(fig)

fig, ax = plt.subplots(1, 3, figsize=(15, 4))
man.split.value_counts().plot.bar(ax=ax[0], title="split sizes", rot=0)
man.groupby("split").has_ground_truth.mean().plot.bar(ax=ax[1], title="GT coverage by split", rot=0)
ax[1].set_ylim(0, 1)
man.plot.scatter("width", "height", s=6, alpha=.3, ax=ax[2], title="image dimensions")
fig.tight_layout(); fig.savefig(FIG / "preprocessing_examples.png", dpi=150); plt.close(fig)

REP = Path("/content/out/data_quality_report.md")
REP.write_text(f'''# Data Quality Report — Rolando (Colab, annotation-aware)

- Unique images available: {len(allimgs)} (duplicate batch_3 copies excluded)
- Sampled: {len(man)}
- **Ground-truth coverage: {cov:.1%}** (previous local run: 26.3%)
- Split: {man.split.value_counts().to_dict()}
- Corrupt images: {int(man.is_corrupt.sum())}
- Annotated ids available: {len(annotated)}

## Known limitations
- Annotation CSVs exist only for batch_1, so high coverage is achieved by *preferring* batch_1
  images. This trades some cross-batch visual diversity for label availability — state this
  in the report.
- `batch_3/` duplicates batches 1 and 2; those copies are excluded to avoid train/test leakage.
''', encoding="utf-8")
print(REP.read_text()[:600])"""),
        c_runblock("rolando"),
        co("""# --- metrics + publish --------------------------------------------------------
met = Path("/content/out/ingestion_metrics.json")
met.write_text(json.dumps({
    "n_images": len(man), "gt_coverage": round(float(cov), 4),
    "split": man.split.value_counts().to_dict(),
    "unique_available": len(allimgs), "annotated_available": len(annotated),
    "_run": run_block(n_train_images=len(man), model="n/a (ingestion)"),
}, indent=2), encoding="utf-8")
print(met.read_text())"""),
        c_publish("rolando", {
            "predictions": 'STAGE / "invoice_manifest.csv"',
            "metrics": "met",
            "figures": 'FIG / "sample_invoice_grid.png"',
            "logs": "REP",
        }, "Also copy the manifest + images into inputs/ so downstream notebooks see them."),
        co("""# --- Refresh inputs/ for every downstream member -------------------------------
# Rolando is the only member who writes into inputs/ - the others only read it.
shutil.copyfile(STAGE / "invoice_manifest.csv", paths.inputs / "invoice_manifest.csv")
(paths.inputs / "images").mkdir(exist_ok=True)
for p in (STAGE / "images").glob("*.jpg"):
    shutil.copyfile(p, paths.inputs / "images" / p.name)
CB.publish("rolando", FIG / "preprocessing_examples.png", "figures",
           paths=paths, run_timestamp=RUN_TS)
print("inputs/ refreshed:", len(list((paths.inputs / 'images').glob('*.jpg'))), "images")"""),
        c_report("rolando", [
            "Why annotation-aware sampling, and what diversity did you trade away for coverage?",
            "The duplicate-`batch_3` discovery — how would it have leaked into train/test?",
            "Final GT coverage per split, and whether the test split has enough labels to report on.",
            "Anything odd in the images (corrupt files, wild aspect ratios, rotations).",
        ]),
    ]
    return c


# ================================================================= 02 DIANA
def nb_diana():
    c = [
        c_title("02", "Diana", "Stamp & Signature Detection",
                "Trains a **2-class** detector (`stamp`, `signature`) on real SignverOD + StaVer "
                "data, evaluates per class on a real held-out split, then runs inference on the "
                "invoice images.",
                "Drive: `datasets/signatures/`, `datasets/stamps/`, invoice manifest",
                "`stamp_signature_predictions.csv`, metrics JSON, figure, weights",
                "~45–90 min on a T4"),
        md("""### The rule that cannot bend
`stamp` and `signature` are **always two separate labels**. Never merge them into one
"authorization mark" class, never rename either string — the final JSON schema, the Streamlit UI,
and the Pistac.io readiness logic all assume both exist independently.

### Two datasets, two shapes of annotation
- **SignverOD** — `train.csv`/`test.csv` give `bbox` as a *stringified JSON list of **normalized**
  `[xmin, ymin, w, h]`*, joined to `image_ids.csv` for pixel dimensions. Categories are
  `1=signature, 2=initials, 3=redaction, 4=date` → **only category 1** is our `signature`.
- **StaVer** — ships **no boxes at all**, only binary ground-truth *masks*. Boxes have to be
  derived with connected components, cross-checked against `numStamps` in the info files.

### Domain gap — be honest about it
Neither source is an invoice. Metrics below are computed on a **held-out split of the real source
data** (legitimate, real numbers). Inference on invoices has **no ground truth**, so report
detection counts and confidence distributions there — never a precision/recall figure."""),
        c_gpu(),
        c_bootstrap(["ultralytics", "opencv-python-headless", "pandas"]),
        c_profile(),
        c_drive_data({"signatures": "signatures", "stamps": "stamps"},
                     "Both were pre-downloaded into Drive, so this cell only checks they exist."),
        co("""# --- SignverOD -> pixel boxes for category_id == 1 (signature) ----------------
import pandas as pd, ast, cv2, numpy as np

SIG = DATA / "signatures"
ids = pd.read_csv(SIG / "image_ids.csv")            # height,width,id,file_name
tr  = pd.read_csv(SIG / "train.csv")                # area,bbox,category_id,id,image_id

df = tr[tr.category_id == 1].merge(ids, left_on="image_id", right_on="id", suffixes=("", "_img"))
print("signature annotations:", len(df), "| images:", df.file_name.nunique())

def to_px(row):
    x, y, w, h = ast.literal_eval(row["bbox"])       # normalized [xmin,ymin,w,h]
    W, H = row["width"], row["height"]
    return pd.Series([x * W, y * H, (x + w) * W, (y + h) * H])

df[["xmin", "ymin", "xmax", "ymax"]] = df.apply(to_px, axis=1)
# sanity: normalized area should reconstruct
print("area check:", np.allclose(df.area.head(20),
      ((df.xmax-df.xmin)/df.width * (df.ymax-df.ymin)/df.height).head(20), atol=2e-3))
df.head(3)[["file_name", "xmin", "ymin", "xmax", "ymax"]]"""),
        co("""# --- StaVer -> boxes from the binary GT masks --------------------------------
STA = DATA / "stamps"
scans = {p.stem: p for p in (STA / "scans").glob("*.png")}
masks = sorted((STA / "ground-truth-maps").glob("*-gt.png"))
print("scans:", len(scans), "| gt masks:", len(masks))

def boxes_from_mask(mask_path, min_area_frac=2e-4):
    m = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    # stamps are the dark/coloured ink on a white GT map - binarise either polarity
    bw = (m < 128).astype(np.uint8)
    if bw.mean() > .5:
        bw = 1 - bw
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    H, W = m.shape
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a >= min_area_frac * H * W:
            out.append((x, y, x + w, y + h))
    return out, (W, H)

stamp_rows = []
for mp in masks:
    stem = mp.stem.replace("-gt", "")
    if stem not in scans:
        continue
    bx, (W, H) = boxes_from_mask(mp)
    info = STA / "info" / f"{stem}.txt"
    expected = None
    if info.exists():
        try:
            expected = int(info.read_text().strip().splitlines()[-1].split()[2])
        except Exception:
            pass
    for b in bx:
        stamp_rows.append({"file": scans[stem], "stem": stem, "W": W, "H": H,
                           "xmin": b[0], "ymin": b[1], "xmax": b[2], "ymax": b[3],
                           "n_found": len(bx), "n_expected": expected})
sdf = pd.DataFrame(stamp_rows)
print("stamp boxes:", len(sdf), "| images:", sdf.stem.nunique())
ok = sdf.drop_duplicates("stem").dropna(subset=["n_expected"])
print("images where found == expected numStamps: %.1f%%" %
      (100 * (ok.n_found == ok.n_expected).mean()))"""),
        co("""# --- Build a 2-class YOLO dataset --------------------------------------------
D = Path("/content/yolo")
for sp in ["train", "val"]:
    (D / sp / "images").mkdir(parents=True, exist_ok=True)
    (D / sp / "labels").mkdir(parents=True, exist_ok=True)

NAMES = ["stamp", "signature"]          # index 0 = stamp, 1 = signature - do not reorder

def write(split, img_path, boxes, cls_idx, size=None):
    dst = D / split / "images" / f"{cls_idx}_{Path(img_path).stem}.jpg"
    im = cv2.imread(str(img_path))
    if im is None:
        return False
    H, W = im.shape[:2]
    cv2.imwrite(str(dst), im)
    lines = []
    for (x1, y1, x2, y2) in boxes:
        cx, cy = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H
        bw, bh = (x2 - x1) / W, (y2 - y1) / H
        if bw <= 0 or bh <= 0:
            continue
        lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
    (D / split / "labels" / f"{dst.stem}.txt").write_text("\\n".join(lines))
    return True

cap = P.get("max_images_per_class") or 10**9

# stamps
stems = sorted(sdf.stem.unique())[:cap]
for i, s in enumerate(stems):
    g = sdf[sdf.stem == s]
    write("val" if i % 6 == 0 else "train", g.file.iloc[0],
          g[["xmin", "ymin", "xmax", "ymax"]].values, 0)

# signatures
sig_imgs = sorted(df.file_name.unique())[:cap]
IMG_DIR = SIG / "images"
for i, fn in enumerate(sig_imgs):
    g = df[df.file_name == fn]
    p = IMG_DIR / fn
    if not p.exists():
        continue
    write("val" if i % 6 == 0 else "train", p, g[["xmin", "ymin", "xmax", "ymax"]].values, 1)

yaml = D / "data.yaml"
yaml.write_text(f"path: {D}\\ntrain: train/images\\nval: val/images\\n"
                f"nc: 2\\nnames: {NAMES}\\n")
print("train:", len(list((D/'train'/'images').glob('*'))),
      "| val:", len(list((D/'val'/'images').glob('*'))))"""),
        co("""# --- Train (colab_gpu budget) -------------------------------------------------
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
res = model.train(
    data=str(yaml), epochs=P["epochs"], imgsz=P["imgsz"], batch=P["batch"],
    workers=P.get("workers", 2), device=0, patience=P.get("patience", 20),
    project="/content/runs", name="stamp_sig", exist_ok=True, verbose=True,
)
BEST = Path("/content/runs/stamp_sig/weights/best.pt")
print("best weights:", BEST, BEST.exists())"""),
        co("""# --- Per-class precision / recall / mean IoU on the REAL held-out split -------
from src.iou import compute_iou           # Jordan's module - import, never reimplement

val_imgs = sorted((D / "val" / "images").glob("*.jpg"))
m = YOLO(str(BEST))
CONF = 0.25

stats = {n: {"tp": 0, "fp": 0, "fn": 0, "ious": []} for n in NAMES}
for ip in val_imgs:
    lab = D / "val" / "labels" / f"{ip.stem}.txt"
    im = cv2.imread(str(ip)); H, W = im.shape[:2]
    gt = []
    for line in lab.read_text().splitlines():
        if not line.strip():
            continue
        ci, cx, cy, bw, bh = line.split()
        ci = int(ci); cx, cy, bw, bh = map(float, (cx, cy, bw, bh))
        gt.append((ci, [(cx-bw/2)*W, (cy-bh/2)*H, (cx+bw/2)*W, (cy+bh/2)*H]))

    pr = m.predict(str(ip), conf=CONF, verbose=False)[0]
    preds = [(int(c), b.tolist()) for c, b in
             zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy())]

    for ci, name in enumerate(NAMES):
        g = [b for k, b in gt if k == ci]
        p_ = [b for k, b in preds if k == ci]
        used = set()
        for pb in p_:
            best, bi = 0.0, -1
            for j, gb in enumerate(g):
                if j in used:
                    continue
                v = compute_iou(pb, gb)
                if v > best:
                    best, bi = v, j
            if best >= 0.5:
                stats[name]["tp"] += 1; stats[name]["ious"].append(best); used.add(bi)
            else:
                stats[name]["fp"] += 1
        stats[name]["fn"] += len(g) - len(used)

metrics = {}
for n, s in stats.items():
    tp, fp, fn = s["tp"], s["fp"], s["fn"]
    metrics[n] = {
        "precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
        "recall":    round(tp / (tp + fn), 4) if tp + fn else 0.0,
        "mean_iou":  round(float(np.mean(s["ious"])), 4) if s["ious"] else 0.0,
        "tp": tp, "fp": fp, "fn": fn,
    }
print(json.dumps(metrics, indent=2))"""),
        c_runblock("diana"),
        co("""# --- Inference on the REAL invoices (no GT here - counts only) ----------------
man = pd.read_csv(paths.inputs / "invoice_manifest.csv")
rows = []
for r in man.itertuples():
    ip = root / r.image_path
    if not ip.exists():
        continue
    pr = m.predict(str(ip), conf=CONF, verbose=False)[0]
    for cls, box, cf in zip(pr.boxes.cls.cpu().numpy(),
                            pr.boxes.xyxy.cpu().numpy(),
                            pr.boxes.conf.cpu().numpy()):
        rows.append({"document_id": r.document_id, "image_path": r.image_path,
                     "label": NAMES[int(cls)],
                     "xmin": float(box[0]), "ymin": float(box[1]),
                     "xmax": float(box[2]), "ymax": float(box[3]),
                     "confidence": round(float(cf), 4)})

pred = pd.DataFrame(rows, columns=["document_id", "image_path", "label",
                                   "xmin", "ymin", "xmax", "ymax", "confidence"])
assert pred.empty or set(pred.label) <= {"stamp", "signature"}, "label vocabulary violated!"
OUTD = Path("/content/out"); OUTD.mkdir(exist_ok=True)
pred.to_csv(OUTD / "stamp_signature_predictions.csv", index=False)

print("invoices with a detection:", pred.document_id.nunique(), "/", len(man))
print(pred.label.value_counts().to_dict())
print(pred.groupby("label").confidence.describe()[["mean", "min", "max"]] if not pred.empty else "")"""),
        co("""# --- Figure + weights ---------------------------------------------------------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

FIG = Path("/content/out/figures"); FIG.mkdir(parents=True, exist_ok=True)
show = (pred.document_id.drop_duplicates().head(6).tolist() if not pred.empty
        else man.document_id.head(6).tolist())
fig, ax = plt.subplots(2, 3, figsize=(15, 10))
for a, d in zip(ax.ravel(), show):
    r = man[man.document_id == d].iloc[0]
    a.imshow(plt.imread(root / r.image_path)); a.axis("off"); a.set_title(d, fontsize=9)
    for q in pred[pred.document_id == d].itertuples():
        col = "tab:red" if q.label == "stamp" else "tab:blue"
        a.add_patch(Rectangle((q.xmin, q.ymin), q.xmax-q.xmin, q.ymax-q.ymin,
                              fill=False, lw=2, ec=col))
        a.text(q.xmin, q.ymin-4, f"{q.label} {q.confidence:.2f}", color=col, fontsize=7)
fig.suptitle("Stamp (red) / signature (blue) detections on real invoices", fontsize=13)
fig.tight_layout(); fig.savefig(FIG / "stamp_signature_detection_examples.png", dpi=150)
plt.close(fig)

MD = Path("/content/out/models"); (MD/"stamp_detector").mkdir(parents=True, exist_ok=True)
(MD/"signature_detector").mkdir(parents=True, exist_ok=True)
for sub in ["stamp_detector", "signature_detector"]:
    shutil.copyfile(BEST, MD / sub / "best.pt")
    (MD / sub / "README.md").write_text(
        f"# {sub}\\n\\nSingle YOLOv8n **2-class** model (`stamp`, `signature`); the same weights "
        f"are stored under both folder names to satisfy the output contract.\\n\\n"
        f"Trained on real SignverOD (category_id==1) + StaVer (boxes derived from GT masks).\\n"
        f"Profile `colab_gpu`: epochs={P['epochs']}, imgsz={P['imgsz']}, batch={P['batch']}.\\n\\n"
        f"Metrics: {json.dumps(metrics)}\\n", encoding="utf-8")

met = Path("/content/out/stamp_signature_metrics.json")
payload = dict(metrics)
payload["_run"] = run_block(model="yolov8n",
                            n_train_images=len(list((D/'train'/'images').glob('*'))),
                            eval_set="real held-out split of SignverOD+StaVer",
                            conf_threshold=CONF, iou_match_threshold=0.5)
payload["_invoice_inference"] = {
    "note": "No ground truth on invoices - counts only, never precision/recall.",
    "invoices_scored": int(len(man)),
    "invoices_with_detection": int(pred.document_id.nunique()) if not pred.empty else 0,
    "detections_by_label": pred.label.value_counts().to_dict() if not pred.empty else {},
}
met.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2)[:900])"""),
        c_publish("diana", {
            "predictions": 'OUTD / "stamp_signature_predictions.csv"',
            "metrics": "met",
            "figures": 'FIG / "stamp_signature_detection_examples.png"',
            "models": "MD",
        }),
        co("""# --- Hand off to Damir + Hessam ----------------------------------------------
up = paths.inputs / "upstream" / "diana"; up.mkdir(parents=True, exist_ok=True)
shutil.copyfile(OUTD / "stamp_signature_predictions.csv",
                up / "stamp_signature_predictions.csv")
print("handed off ->", up)"""),
        c_report("diana", [
            "One 2-class model vs two separate detectors — what you chose and why.",
            "Deriving StaVer boxes from masks: what the connected-component filter got wrong, and "
            "how often `numStamps` disagreed with what you found.",
            "The domain gap — source data isn't invoices. How did detections look on real invoices?",
            "Per-class precision/recall/mean-IoU, and which class is weaker + your theory why.",
            "Why category_id 2/3/4 (initials/redaction/date) were excluded.",
        ]),
    ]
    return c


# ================================================================= 03 JORDAN
def nb_jordan():
    c = [
        c_title("03", "Jordan", "Region Detection & IoU",
                "Trains a region detector on the **OCR Dataset of Multi-type Documents** — which "
                "ships **52,331 real polygon boxes with transcriptions**. No synthetic or "
                "heuristic boxes are needed.",
                "Drive: `datasets/ocr_multitype/`, invoice manifest",
                "`region_predictions.csv`, `region_iou_metrics.json`, figure, weights",
                "~45–75 min on a T4"),
        md("""### Read this — your brief changed

An earlier plan said *"region bboxes are NOT in the annotation CSVs, so use a heuristic/synthetic
region-box approach."* **That is obsolete.** The `OCR Dataset of Multi-type Documents` was found
sitting unused in the raw data and it contains exactly what this stage needs:

| | |
|---|---|
| Images | 973, pre-split **778 / 97 / 98** |
| Annotation pairing | **100%** |
| **Polygon boxes + text** | **52,331** (median 50/image) |
| Entity fields | `company`, `date`, `address`, `total` |

```json
{"file_id": "X00016469612",
 "entities": {"company": "...", "date": "...", "address": "...", "total": "9.00"},
 "ocr_boxes": [{"points": [[72,25],[326,25],[326,64],[72,64]], "text": "TAN WOON YANN"}]}
```

### How unlabeled text boxes become *labeled regions*
`ocr_boxes` are text lines with no class. `entities` give field **values** but no coordinates.
We join them: **match entity text against box text** to label those boxes `company` / `date` /
`address` / `total`, and everything else becomes `other_text`. That yields a real 5-class region
detection problem with real geometry — and it feeds Damir directly.

### Domain gap
These are **receipts** (~460 px wide); the invoice corpus is **full-page** (1654×2339). A detector
trained here will not transfer perfectly. Metrics come from the dataset's own test split; invoice
inference is reported as counts."""),
        c_gpu(),
        c_bootstrap(["ultralytics", "opencv-python-headless", "pandas", "rapidfuzz"]),
        c_profile(),
        c_drive_data({"ocr_multitype": "ocr_multitype"},
                     "548 MB, pre-downloaded into Drive. This is the dataset with the 52,331 "
                     "real polygon boxes."),
        co("""# --- Parse the JSON annotations ----------------------------------------------
import pandas as pd, numpy as np, cv2
from rapidfuzz import fuzz

BASE = DATA / "ocr_multitype"
print("dataset root:", BASE)
for sp in ["train", "val", "test"]:
    print(f"  {sp}: {len(list((BASE/sp/'annotations').glob('*.json')))} ann, "
          f"{len(list((BASE/sp/'images').glob('*')))} imgs")

def load(sp):
    out = []
    for ap in sorted((BASE / sp / "annotations").glob("*.json")):
        d = json.loads(ap.read_text(encoding="utf-8"))
        img = next((BASE / sp / "images").glob(ap.stem + ".*"), None)
        if img is None:
            continue
        out.append({"split": sp, "file_id": d.get("file_id", ap.stem), "img": img,
                    "entities": d.get("entities", {}), "boxes": d.get("ocr_boxes", [])})
    return out

data = {sp: load(sp) for sp in ["train", "val", "test"]}
tot = sum(len(v) for v in data.values())
nbox = sum(len(r["boxes"]) for v in data.values() for r in v)
print(f"\\nloaded {tot} documents, {nbox} boxes")"""),
        co("""# --- Label boxes by matching entity text -------------------------------------
FIELDS = ["company", "date", "address", "total"]
CLASSES = FIELDS + ["other_text"]          # index order is fixed - do not reorder

def norm(s):
    return " ".join(str(s).upper().split())

def quad_to_xyxy(points):
    a = np.asarray(points, dtype=float)
    return [float(a[:, 0].min()), float(a[:, 1].min()),
            float(a[:, 0].max()), float(a[:, 1].max())]

def label_boxes(rec, thresh=88):
    ents = {k: norm(v) for k, v in rec["entities"].items() if v}
    out = []
    for b in rec["boxes"]:
        t = norm(b.get("text", ""))
        cls, best = 4, 0                       # default other_text
        if t:
            for i, f in enumerate(FIELDS):
                e = ents.get(f)
                if not e:
                    continue
                s = max(fuzz.partial_ratio(t, e), fuzz.ratio(t, e))
                if s > best and s >= thresh:
                    best, cls = s, i
        out.append((cls, quad_to_xyxy(b["points"])))
    return out

dist = {c: 0 for c in CLASSES}
for r in data["train"]:
    for ci, _ in label_boxes(r):
        dist[CLASSES[ci]] += 1
print("train box class distribution:")
for k, v in dist.items():
    print(f"  {k:12s} {v:7d}")
print("\\nNOTE the imbalance: other_text dominates. Report per-class metrics, not just mAP.")"""),
        co("""# --- Build the YOLO dataset (use the dataset's own splits) -------------------
D = Path("/content/yolo_regions")
for sp in ["train", "val", "test"]:
    (D / sp / "images").mkdir(parents=True, exist_ok=True)
    (D / sp / "labels").mkdir(parents=True, exist_ok=True)

cap = P.get("max_images_per_class") or 10**9
counts = {}
for sp, recs in data.items():
    n = 0
    for rec in recs[:cap]:
        im = cv2.imread(str(rec["img"]))
        if im is None:
            continue
        H, W = im.shape[:2]
        dst = D / sp / "images" / f"{rec['file_id']}.jpg"
        cv2.imwrite(str(dst), im)
        lines = []
        for ci, (x1, y1, x2, y2) in label_boxes(rec):
            cx, cy = (x1+x2)/2/W, (y1+y2)/2/H
            bw, bh = (x2-x1)/W, (y2-y1)/H
            if bw <= 0 or bh <= 0:
                continue
            lines.append(f"{ci} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        (D / sp / "labels" / f"{rec['file_id']}.txt").write_text("\\n".join(lines))
        n += 1
    counts[sp] = n

yaml = D / "data.yaml"
yaml.write_text(f"path: {D}\\ntrain: train/images\\nval: val/images\\ntest: test/images\\n"
                f"nc: {len(CLASSES)}\\nnames: {CLASSES}\\n")
print(counts)"""),
        co("""# --- Train --------------------------------------------------------------------
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
model.train(data=str(yaml), epochs=P["epochs"], imgsz=P["imgsz"], batch=P["batch"],
            workers=P.get("workers", 2), device=0, patience=P.get("patience", 20),
            project="/content/runs", name="regions", exist_ok=True, verbose=True)
BEST = Path("/content/runs/regions/weights/best.pt")
print("best:", BEST.exists())"""),
        co("""# --- Per-class IoU on the dataset's real TEST split ---------------------------
from src.iou import compute_iou
m = YOLO(str(BEST)); CONF = 0.25

stats = {c: {"tp": 0, "fp": 0, "fn": 0, "ious": []} for c in CLASSES}
for ip in sorted((D/"test"/"images").glob("*.jpg")):
    im = cv2.imread(str(ip)); H, W = im.shape[:2]
    gt = []
    for ln in (D/"test"/"labels"/f"{ip.stem}.txt").read_text().splitlines():
        if not ln.strip():
            continue
        ci, cx, cy, bw, bh = ln.split(); ci = int(ci)
        cx, cy, bw, bh = map(float, (cx, cy, bw, bh))
        gt.append((ci, [(cx-bw/2)*W, (cy-bh/2)*H, (cx+bw/2)*W, (cy+bh/2)*H]))
    pr = m.predict(str(ip), conf=CONF, verbose=False)[0]
    preds = [(int(c), b.tolist()) for c, b in
             zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy())]
    for ci, name in enumerate(CLASSES):
        g = [b for k, b in gt if k == ci]
        p_ = [b for k, b in preds if k == ci]
        used = set()
        for pb in p_:
            best, bi = 0.0, -1
            for j, gb in enumerate(g):
                if j in used:
                    continue
                v = compute_iou(pb, gb)
                if v > best:
                    best, bi = v, j
            if best >= 0.5:
                stats[name]["tp"] += 1; stats[name]["ious"].append(best); used.add(bi)
            else:
                stats[name]["fp"] += 1
        stats[name]["fn"] += len(g) - len(used)

region_metrics = {}
for n_, s in stats.items():
    tp, fp, fn = s["tp"], s["fp"], s["fn"]
    region_metrics[n_] = {
        "precision": round(tp/(tp+fp), 4) if tp+fp else 0.0,
        "recall":    round(tp/(tp+fn), 4) if tp+fn else 0.0,
        "mean_iou":  round(float(np.mean(s["ious"])), 4) if s["ious"] else 0.0,
        "support":   tp+fn,
    }
print(json.dumps(region_metrics, indent=2))"""),
        c_runblock("jordan"),
        co("""# --- Predictions on the dataset test split + on real invoices ----------------
OUTD = Path("/content/out"); OUTD.mkdir(exist_ok=True)
rows = []
for ip in sorted((D/"test"/"images").glob("*.jpg")):
    pr = m.predict(str(ip), conf=CONF, verbose=False)[0]
    for cls, box, cf in zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy(),
                            pr.boxes.conf.cpu().numpy()):
        rows.append({"document_id": ip.stem, "image_path": f"ocrset/test/{ip.name}",
                     "region_label": CLASSES[int(cls)],
                     "xmin": float(box[0]), "ymin": float(box[1]),
                     "xmax": float(box[2]), "ymax": float(box[3]),
                     "confidence": round(float(cf), 4), "source": "ocr_dataset_test"})

man = pd.read_csv(paths.inputs / "invoice_manifest.csv")
for r in man.itertuples():
    ip = root / r.image_path
    if not ip.exists():
        continue
    pr = m.predict(str(ip), conf=CONF, verbose=False)[0]
    for cls, box, cf in zip(pr.boxes.cls.cpu().numpy(), pr.boxes.xyxy.cpu().numpy(),
                            pr.boxes.conf.cpu().numpy()):
        rows.append({"document_id": r.document_id, "image_path": r.image_path,
                     "region_label": CLASSES[int(cls)],
                     "xmin": float(box[0]), "ymin": float(box[1]),
                     "xmax": float(box[2]), "ymax": float(box[3]),
                     "confidence": round(float(cf), 4), "source": "invoice"})

reg = pd.DataFrame(rows)
reg.to_csv(OUTD / "region_predictions.csv", index=False)
print(reg.groupby(["source", "region_label"]).size())"""),
        co("""# --- Figure + metrics ---------------------------------------------------------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

FIG = Path("/content/out/figures"); FIG.mkdir(parents=True, exist_ok=True)
COL = {"company": "tab:red", "date": "tab:green", "address": "tab:orange",
       "total": "tab:purple", "other_text": "tab:gray"}
te = reg[reg.source == "ocr_dataset_test"]
fig, ax = plt.subplots(1, 4, figsize=(16, 7))
for a, d in zip(ax.ravel(), te.document_id.drop_duplicates().head(4)):
    a.imshow(plt.imread(D/"test"/"images"/f"{d}.jpg")); a.axis("off"); a.set_title(d, fontsize=8)
    for q in te[te.document_id == d].itertuples():
        a.add_patch(Rectangle((q.xmin, q.ymin), q.xmax-q.xmin, q.ymax-q.ymin,
                              fill=False, lw=1.4, ec=COL.get(q.region_label, "k")))
fig.suptitle("Region detection on the OCR Dataset test split "
             "(red=company, green=date, orange=address, purple=total, gray=other)", fontsize=11)
fig.tight_layout(); fig.savefig(FIG/"region_detection_examples.png", dpi=150); plt.close(fig)

MD = Path("/content/out/models/region_detector"); MD.mkdir(parents=True, exist_ok=True)
shutil.copyfile(BEST, MD/"best.pt")
(MD/"README.md").write_text(
    f"# region_detector\\n\\nYOLOv8n, {len(CLASSES)} classes: {CLASSES}\\n\\n"
    f"Trained on the OCR Dataset of Multi-type Documents (real polygon boxes; entity text "
    f"matched to box text to assign field labels).\\nProfile colab_gpu: epochs={P['epochs']}, "
    f"imgsz={P['imgsz']}.\\n\\nMetrics: {json.dumps(region_metrics)}\\n", encoding="utf-8")

met = Path("/content/out/region_iou_metrics.json")
payload = {"per_class": region_metrics,
           "macro_mean_iou": round(float(np.mean([v["mean_iou"] for v in region_metrics.values()])), 4),
           "_run": run_block(model="yolov8n", classes=CLASSES,
                             n_train_images=counts.get("train"),
                             eval_set="OCR Dataset official test split (98 imgs)",
                             conf_threshold=CONF, iou_match_threshold=0.5),
           "_invoice_inference": {
               "note": "Receipts -> full-page invoices is a domain shift; counts only, no GT.",
               "invoices_with_regions": int(reg[reg.source == 'invoice'].document_id.nunique()),
           }}
met.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2)[:900])"""),
        c_publish("jordan", {
            "predictions": 'OUTD / "region_predictions.csv"',
            "metrics": "met",
            "figures": 'FIG / "region_detection_examples.png"',
            "models": 'Path("/content/out/models")',
        }),
        co("""# --- Hand off to Damir + Hessam ----------------------------------------------
up = paths.inputs / "upstream" / "jordan"; up.mkdir(parents=True, exist_ok=True)
shutil.copyfile(OUTD/"region_predictions.csv", up/"region_predictions.csv")
print("handed off ->", up)"""),
        c_report("jordan", [
            "The entity-text → box-text matching trick: what fuzzy threshold, and what did it mislabel?",
            "Class imbalance — `other_text` dwarfs the four field classes. What did you do about it?",
            "Per-class precision/recall/IoU on the real test split; which field is hardest and why.",
            "The receipt → full-page-invoice domain gap: what did predictions look like on invoices?",
            "How this compares to the heuristic-box approach originally planned (which you avoided).",
        ]),
    ]
    return c


# ================================================================= 04 DAMIR
def nb_damir():
    c = [
        c_title("04", "Damir", "OCR, Business Parameters & Terms",
                "Runs GPU OCR over invoices/receipts, scores it against **real transcriptions**, "
                "then checks business-parameter presence and extracts payment terms.",
                "Drive: `datasets/ocr_multitype/`, `inputs/annotations/`, `inputs/images/`",
                "`ocr_outputs.csv`, `parameter_presence_results.csv`, "
                "`terms_extraction_results.csv`, metrics JSON",
                "~40–70 min on a T4"),
        md("""### You have two evaluation sets, with very different strength

| | OCR Dataset (**primary**) | Batch CSVs (**secondary**) |
|---|---|---|
| Images | 973, pre-split | 5,201, of which **1,413 annotated** |
| Coverage | **100%** | ~27% |
| Text GT | per-box transcription (52,331) | page-level blob |
| Fields | company, date, address, total | invoice, items, subtotal, payment_instructions |

Report the **primary** numbers as your headline — they have full coverage and per-box text, so
CER/WER is meaningful. Use the batch subset as a secondary, real-full-page-invoice check, and
**always state the denominator** (only ~197 of the 750 manifest images have any GT at all).

### Don't reimplement the shared logic
`src/parameter_checker.py` and `src/terms_extraction.py` already exist and are unit-tested. Import
them. If you find a real bug, report it rather than forking the logic."""),
        c_gpu(),
        c_bootstrap(["easyocr", "rapidfuzz", "pandas", "opencv-python-headless", "jiwer"]),
        c_profile(),
        c_drive_data({"ocr_multitype": "ocr_multitype"},
                     "Primary eval set. The secondary invoice check reads inputs/images/ + "
                     "inputs/annotations/, which are already in Drive."),
        co("""# --- Load the primary GT (per-box transcriptions + entities) -----------------
import pandas as pd, numpy as np, cv2

BASE = DATA / "ocr_multitype"
def load(sp):
    out = []
    for ap in sorted((BASE/sp/"annotations").glob("*.json")):
        d = json.loads(ap.read_text(encoding="utf-8"))
        img = next((BASE/sp/"images").glob(ap.stem+".*"), None)
        if img:
            out.append({"file_id": d.get("file_id", ap.stem), "img": img,
                        "entities": d.get("entities", {}),
                        "text": "\\n".join(b.get("text", "") for b in d.get("ocr_boxes", []))})
    return out
test = load("test")
print("primary eval docs:", len(test), "(100% have GT text + entities)")
print("sample GT text:\\n", test[0]["text"][:300])"""),
        co("""# --- GPU OCR ------------------------------------------------------------------
import easyocr, time
reader = easyocr.Reader(["en"], gpu=True)

N = P.get("max_images_per_class") or len(test)
rows, t0 = [], time.time()
for r in test[:N]:
    res = reader.readtext(str(r["img"]), detail=1, paragraph=False)
    txt = "\\n".join(t for _, t, _ in res)
    conf = float(np.mean([c for _, _, c in res])) if res else 0.0
    rows.append({"document_id": r["file_id"], "image_path": str(r["img"]),
                 "ocr_text": txt, "mean_confidence": round(conf, 4),
                 "n_boxes": len(res), "source": "ocr_dataset_test"})
ocr = pd.DataFrame(rows)
print(f"OCR'd {len(ocr)} docs in {time.time()-t0:.0f}s "
      f"({(time.time()-t0)/max(len(ocr),1):.2f}s/doc)")
ocr.head(2)"""),
        co("""# --- Score OCR against the real transcriptions (CER / WER) -------------------
import jiwer
gtmap = {r["file_id"]: r["text"] for r in test}

def clean(s):
    return " ".join(str(s).upper().split())

cers, wers = [], []
for r in ocr.itertuples():
    g, h = clean(gtmap.get(r.document_id, "")), clean(r.ocr_text)
    if not g:
        continue
    cers.append(jiwer.cer(g, h))
    wers.append(jiwer.wer(g, h))

ocr_metrics = {
    "n_scored": len(cers),
    "cer_mean": round(float(np.mean(cers)), 4) if cers else None,
    "cer_median": round(float(np.median(cers)), 4) if cers else None,
    "wer_mean": round(float(np.mean(wers)), 4) if wers else None,
    "wer_median": round(float(np.median(wers)), 4) if wers else None,
}
print(json.dumps(ocr_metrics, indent=2))
print("\\nLower is better. CER ~0.1 = roughly 1 character in 10 wrong.")"""),
        co("""# --- Business-parameter presence (shared module - do not reimplement) --------
from src import parameter_checker as PC
print("parameter_checker exposes:", [x for x in dir(PC) if not x.startswith('_')][:15])

def check(text):
    \"\"\"Adapt to whatever entry point the shared module provides.\"\"\"
    for fn in ("check_parameters", "check_presence", "evaluate", "run"):
        if hasattr(PC, fn):
            try:
                return getattr(PC, fn)(text)
            except TypeError:
                pass
    # Fallback: presence of the four primary entity fields.
    t = text.upper()
    return {"has_company": any(k in t for k in ["LTD", "SDN", "BHD", "INC", "CO."]),
            "has_date": bool(__import__("re").search(r"\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}", t)),
            "has_total": "TOTAL" in t,
            "has_address": any(k in t for k in ["JALAN", "STREET", "ROAD", "NO."])}

pres = pd.DataFrame([{"document_id": r.document_id, **check(r.ocr_text)}
                     for r in ocr.itertuples()])
print(pres.drop(columns=["document_id"]).mean(numeric_only=True).round(3))

# Truth from the entities block, so presence can actually be scored.
ent = {r["file_id"]: r["entities"] for r in test}
truth = pd.DataFrame([{"document_id": k,
                       "gt_company": bool(v.get("company")), "gt_date": bool(v.get("date")),
                       "gt_address": bool(v.get("address")), "gt_total": bool(v.get("total"))}
                      for k, v in ent.items()])
pres = pres.merge(truth, on="document_id", how="left")
pres.to_csv("/content/out_parameter_presence_results.csv", index=False)
pres.head(3)"""),
        co("""# --- Terms extraction (shared module) ----------------------------------------
from src import terms_extraction as TE
print("terms_extraction exposes:", [x for x in dir(TE) if not x.startswith('_')][:15])

def extract(text):
    for fn in ("extract_terms", "extract", "run", "get_terms"):
        if hasattr(TE, fn):
            try:
                return getattr(TE, fn)(text)
            except TypeError:
                pass
    return {}

terms = []
for r in ocr.itertuples():
    out = extract(r.ocr_text)
    terms.append({"document_id": r.document_id,
                  **(out if isinstance(out, dict) else {"terms": str(out)})})
tdf = pd.DataFrame(terms)
tdf.to_csv("/content/out_terms_extraction_results.csv", index=False)
print(tdf.head(3))
print("\\nnon-empty extraction rate:",
      round(float(tdf.drop(columns=['document_id']).notna().any(axis=1).mean()), 3))"""),
        co("""# --- SECONDARY eval: real full-page invoices (state the denominator!) --------
# The batch annotation CSVs and the 750 invoice images are already in Drive inputs/.
ann = sorted((paths.inputs / "annotations").glob("batch1_*.csv"))
sec_metrics = {"skipped": True, "reason": "no batch annotation CSVs in inputs/annotations/"}

if ann:
    gt2 = pd.concat([pd.read_csv(p) for p in ann], ignore_index=True)
    gt2["stem"] = gt2["File Name"].astype(str).str.replace(".jpg", "", regex=False).str.strip()
    gt2 = gt2.drop_duplicates("stem").set_index("stem")

    man = pd.read_csv(paths.inputs / "invoice_manifest.csv")
    have = man[man.document_id.isin(gt2.index)]
    print(f"manifest rows WITH GT: {len(have)} / {len(man)} ({len(have)/len(man):.1%})")

    M = min(len(have), 120)          # keep it bounded - this is a secondary check
    c2 = []
    for r in have.head(M).itertuples():
        ip = root / r.image_path
        if not ip.exists():
            continue
        res = reader.readtext(str(ip), detail=1, paragraph=False)
        hyp = clean("\\n".join(t for _, t, _ in res))
        ref = clean(gt2.loc[r.document_id, "OCRed Text"])
        if ref:
            c2.append(jiwer.cer(ref, hyp))
        rows.append({"document_id": r.document_id, "image_path": r.image_path,
                     "ocr_text": hyp, "mean_confidence": None,
                     "n_boxes": len(res), "source": "invoice_batch1"})
    sec_metrics = {"skipped": False, "n_scored": len(c2),
                   "cer_mean": round(float(np.mean(c2)), 4) if c2 else None,
                   "denominator_note": f"only {len(have)} of {len(man)} manifest images have GT"}
print(json.dumps(sec_metrics, indent=2))"""),
        c_runblock("damir"),
        co("""# --- Write the four contracted outputs ---------------------------------------
OUTD = Path("/content/out"); OUTD.mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(OUTD/"ocr_outputs.csv", index=False)
shutil.copyfile("/content/out_parameter_presence_results.csv",
                OUTD/"parameter_presence_results.csv")
shutil.copyfile("/content/out_terms_extraction_results.csv",
                OUTD/"terms_extraction_results.csv")

met = Path("/content/out/ocr_parameter_metrics.json")
met.write_text(json.dumps({
    "ocr_primary": ocr_metrics,
    "ocr_secondary_invoices": sec_metrics,
    "parameter_presence_rate": pres.drop(columns=["document_id"])
                                   .mean(numeric_only=True).round(4).to_dict(),
    "_run": run_block(model="easyocr-en", engine="easyocr",
                      n_train_images=None, eval_set="OCR Dataset test split (98, 100% GT)"),
}, indent=2), encoding="utf-8")
print(met.read_text()[:900])"""),
        c_publish("damir", {
            "predictions": 'OUTD / "ocr_outputs.csv"',
            "metrics": "met",
        }),
        co("""# --- publish the two remaining CSVs + hand off -------------------------------
for f in ["parameter_presence_results.csv", "terms_extraction_results.csv"]:
    CB.publish("damir", OUTD/f, "predictions", paths=paths, run_timestamp=RUN_TS)

up = paths.inputs/"upstream"/"damir"; up.mkdir(parents=True, exist_ok=True)
for f in ["ocr_outputs.csv", "parameter_presence_results.csv", "terms_extraction_results.csv"]:
    shutil.copyfile(OUTD/f, up/f)
print("handed off ->", up)"""),
        c_report("damir", [
            "Which OCR engine, and why (EasyOCR vs PaddleOCR vs Tesseract) — did you compare any?",
            "Headline CER/WER on the primary set, plus how preprocessing changed them.",
            "The secondary invoice eval: your number AND its denominator (~197 of 750 have GT).",
            "Where parameter_checker / terms_extraction needed adapting, and any bug you found.",
            "Which business parameters are hardest to detect and what that means for Pistac.io readiness.",
        ]),
    ]
    return c


# ================================================================= 05 HESSAM
def nb_hessam():
    c = [
        c_title("05", "Hessam", "Integration, Final JSON & Report Assets",
                "Merges every member's outputs into the final per-invoice JSON, builds the "
                "comparison/evaluation charts for the report and deck, and packages the "
                "Streamlit demo. **Run this last.**",
                "All members' outputs from Drive `inputs/upstream/` + `outputs/`",
                "`sample_invoice_outputs/*.json`, `final_pipeline_report.md`, report charts",
                "~10–20 min (no training — GPU optional)"),
        md("""### Run order
This notebook consumes what the other four publish. Before running, confirm Drive has:

```
inputs/upstream/diana/stamp_signature_predictions.csv
inputs/upstream/jordan/region_predictions.csv
inputs/upstream/damir/{ocr_outputs,parameter_presence_results,terms_extraction_results}.csv
```

Missing pieces don't crash the notebook — it degrades gracefully and records exactly what was
absent, so you can integrate partial results and re-run later."""),
        c_gpu(),
        c_bootstrap(["pandas", "matplotlib"]),
        c_profile(),
        co("""# --- Collect whatever upstream members have published ------------------------
import pandas as pd, numpy as np

UP = paths.inputs / "upstream"
WANT = {
    "diana_preds":  UP/"diana"/"stamp_signature_predictions.csv",
    "jordan_preds": UP/"jordan"/"region_predictions.csv",
    "damir_ocr":    UP/"damir"/"ocr_outputs.csv",
    "damir_params": UP/"damir"/"parameter_presence_results.csv",
    "damir_terms":  UP/"damir"/"terms_extraction_results.csv",
}
got, missing = {}, []
for k, p in WANT.items():
    if p.exists():
        got[k] = pd.read_csv(p)
        print(f"  OK      {k:14s} {len(got[k]):6d} rows")
    else:
        missing.append(k)
        print(f"  MISSING {k:14s} ({p})")

man = pd.read_csv(paths.inputs/"invoice_manifest.csv")
print(f"\\nmanifest: {len(man)} invoices | missing upstream: {missing or 'none'}")"""),
        co("""# --- Build the final per-invoice JSON ----------------------------------------
try:
    from src.final_json_builder import build_final_json      # preferred: shared module
    HAVE_BUILDER = True
except Exception as e:
    HAVE_BUILDER = False
    print("final_json_builder unavailable, using inline fallback:", e)

OUTJ = Path("/content/out/final_json/sample_invoice_outputs")
OUTJ.mkdir(parents=True, exist_ok=True)

def rows_for(df, doc, col="document_id"):
    return [] if df is None or col not in df else df[df[col] == doc].to_dict("records")

SAMPLE = man.head(50)          # a representative sample for the deliverable
for r in SAMPLE.itertuples():
    doc = r.document_id
    stamps = [x for x in rows_for(got.get("diana_preds"), doc) if x.get("label") == "stamp"]
    sigs   = [x for x in rows_for(got.get("diana_preds"), doc) if x.get("label") == "signature"]
    regions = rows_for(got.get("jordan_preds"), doc)
    ocr = rows_for(got.get("damir_ocr"), doc)
    params = rows_for(got.get("damir_params"), doc)

    payload = {
        "document_id": doc,
        "image_path": r.image_path,
        "dimensions": {"width": int(r.width), "height": int(r.height)},
        "stamp": {"detected": bool(stamps), "count": len(stamps), "boxes": stamps},
        "signature": {"detected": bool(sigs), "count": len(sigs), "boxes": sigs},
        "regions": regions,
        "ocr": {"text": (ocr[0].get("ocr_text") if ocr else None),
                "mean_confidence": (ocr[0].get("mean_confidence") if ocr else None)},
        "business_parameters": (params[0] if params else {}),
        "pistac_ready": bool(stamps) and bool(sigs),
        "_provenance": {"upstream_present": sorted(got), "upstream_missing": missing},
    }
    if HAVE_BUILDER:
        try:
            payload = build_final_json(payload)
        except Exception:
            pass
    (OUTJ/f"{doc}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

print("wrote", len(list(OUTJ.glob('*.json'))), "JSON files")
print(json.dumps(json.loads(next(OUTJ.glob('*.json')).read_text()), indent=2)[:700])"""),
        co("""# --- Gather every members' metrics for the comparison charts -----------------
metrics = {}
for mem in ["rolando", "diana", "jordan", "damir"]:
    d = paths.outputs(mem)/"metrics"
    for f in sorted(d.glob("*.json")):
        try:
            metrics[f"{mem}/{f.name}"] = json.loads(f.read_text())
        except Exception as e:
            print("  unreadable:", f, e)
print("metrics files found:")
for k in metrics:
    print("  ", k)

# The _run block is what makes cross-run comparison possible.
runs = []
for k, v in metrics.items():
    rb = v.get("_run")
    if rb:
        runs.append({"source": k, **{kk: rb.get(kk) for kk in
                    ["member", "profile", "device", "epochs", "imgsz", "batch",
                     "wall_clock_sec", "model", "timestamp_utc"]}})
runs_df = pd.DataFrame(runs)
print("\\n", runs_df if not runs_df.empty else "no _run blocks yet")"""),
        co("""# --- Report charts (also written to outputs/_shared/) ------------------------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
try:
    from src.reporting_charts import save_figure, per_class_metrics_bar, profile_comparison
    SHARED = True
except Exception:
    SHARED = False

FIG = Path("/content/out/figures"); FIG.mkdir(parents=True, exist_ok=True)

# 1) per-class detection quality across members
per_class = {}
for k, v in metrics.items():
    if "stamp_signature" in k:
        for cls in ("stamp", "signature"):
            if cls in v:
                per_class[cls] = v[cls]
    if "region_iou" in k and "per_class" in v:
        per_class.update(v["per_class"])

if per_class:
    labels = list(per_class)
    fig, ax = plt.subplots(figsize=(max(7, 1.3*len(labels)), 4.5))
    x = np.arange(len(labels)); w = .27
    for i, (mkey, lbl) in enumerate([("precision", "Precision"), ("recall", "Recall"),
                                     ("mean_iou", "Mean IoU")]):
        ax.bar(x + (i-1)*w, [per_class[l].get(mkey, 0) or 0 for l in labels], w, label=lbl)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylim(0, 1); ax.set_ylabel("score"); ax.legend(frameon=False)
    ax.set_title("Detection quality by class (real held-out data)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG/"model_comparison_per_class.png", dpi=200); plt.close(fig)
    print("wrote model_comparison_per_class.png")

# 2) runtime / budget comparison across runs
if not runs_df.empty and runs_df.wall_clock_sec.notna().any():
    fig, ax = plt.subplots(figsize=(7, 4))
    d = runs_df.dropna(subset=["wall_clock_sec"])
    ax.barh(d["source"], d["wall_clock_sec"]/60)
    ax.set_xlabel("wall clock (minutes)"); ax.set_title("Run cost by stage / profile")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG/"model_comparison_runtime.png", dpi=200); plt.close(fig)
    print("wrote model_comparison_runtime.png")

for f in FIG.glob("*.png"):
    shutil.copyfile(f, paths.shared("model_comparison")/f.name)
    shutil.copyfile(f, paths.shared("report_assets")/f.name)
print("charts ->", paths.shared("model_comparison"))"""),
        c_runblock("hessam"),
        co("""# --- Final pipeline report ----------------------------------------------------
ready = sum(1 for f in OUTJ.glob("*.json") if json.loads(f.read_text()).get("pistac_ready"))
REP = Path("/content/out/final_pipeline_report.md")
REP.write_text(f'''# Final Pipeline Report

Generated {RUN_TS} (Colab, profile `colab_gpu`).

## Coverage
- Invoices in manifest: **{len(man)}**
- Final JSON produced for: **{len(list(OUTJ.glob("*.json")))}** (sample)
- Both stamp AND signature detected ("Pistac.io ready"): **{ready}**

## Upstream stages integrated
{chr(10).join(f"- OK {k}" for k in sorted(got)) or "- (none)"}

## Missing / not yet run
{chr(10).join(f"- MISSING {k}" for k in missing) or "- none"}

## Runs compared
{runs_df.to_markdown(index=False) if not runs_df.empty else "_no _run blocks found yet_"}

## Caveats that must appear in the group report
- Diana's detector is trained on SignverOD/StaVer, **not** invoices — a real domain gap.
- Jordan's regions come from the OCR Dataset (**receipts**, ~460px wide) while the invoice
  corpus is full-page 1654x2339. Transfer is imperfect by construction.
- Damir's secondary invoice OCR score has a small denominator (only ~197 of 750 manifest
  images carry ground truth; annotations exist for batch_1 only).
- `batch_3/` duplicates batches 1 and 2; those copies are excluded from the manifest to
  prevent train/test leakage. True unique invoice count is 5,201, not 8,181.
''', encoding="utf-8")
print(REP.read_text()[:1000])"""),
        c_publish("hessam", {
            "logs": "REP",
            "predictions": 'Path("/content/out/final_json")',
        }),
        co("""# --- Streamlit demo package ---------------------------------------------------
APP = Path("/content/out/app"); APP.mkdir(parents=True, exist_ok=True)
src_app = paths.code/"app"/"streamlit_app.py"
if src_app.exists():
    shutil.copyfile(src_app, APP/"streamlit_app.py")
    print("copied streamlit_app.py from Drive code/")
else:
    print("NOTE: app/streamlit_app.py not in Drive code/ - copy it there, or run the app "
          "from the local repo against these JSON outputs.")

(APP/"RUN_LOCALLY.md").write_text(f'''# Running the demo locally

1. Copy `outputs/hessam/predictions/final_json/sample_invoice_outputs/*.json` from Drive into
   the repo at `outputs/final_json/sample_invoice_outputs/`.
2. Copy each member's CSVs from `outputs/<member>/predictions/` into `outputs/predictions/`.
3. From the repo root:  `streamlit run app/streamlit_app.py`

Generated {RUN_TS}.
''', encoding="utf-8")
CB.publish("hessam", APP, "logs", paths=paths, run_timestamp=RUN_TS)
print("done")"""),
        c_report("hessam", [
            "Which stages were integrated vs missing, and how you handled the gaps.",
            "The end-to-end story: how many invoices came out Pistac.io-ready, and what blocked the rest.",
            "Which caveat you judge most important for the audience to understand.",
            "What you'd do next with more compute or better ground truth.",
        ]),
    ]
    return c


# ================================================================= write
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    books = {
        "01_rolando_data_ingestion_colab.ipynb": nb_rolando(),
        "02_diana_stamp_signature_colab.ipynb": nb_diana(),
        "03_jordan_region_detection_colab.ipynb": nb_jordan(),
        "04_damir_ocr_terms_colab.ipynb": nb_damir(),
        "05_hessam_integration_colab.ipynb": nb_hessam(),
    }
    for name, cells in books.items():
        nb = nbf.v4.new_notebook(cells=cells)
        nb.metadata.update({
            "accelerator": "GPU",
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        })
        p = OUT / name
        nbf.write(nb, str(p))
        # validate what we just wrote
        nbf.validate(nbf.read(str(p), as_version=4))
        print(f"  {name:44s} {len(cells):2d} cells  {p.stat().st_size/1024:6.1f} KB")
    print(f"\\nwrote {len(books)} notebooks -> {OUT}")


if __name__ == "__main__":
    main()
