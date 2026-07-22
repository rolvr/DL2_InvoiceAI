"""
rescope_bundle.py - re-run Rolando's ingestion ANNOTATION-AWARE, locally, then rebuild the
Google Drive bundle so `inputs/` matches the agreed Hybrid-by-role scope.

Why locally: the resample is pure CSV + file-copy work (no GPU, seconds). Doing it here means
Drive only ever receives the 750 images we actually want, instead of anyone re-downloading
6 GB in Colab or uploading the wrong set.

Scope changes vs the first bundle:
  * manifest is sampled ONLY from images that have a row in the batch_1 annotation CSVs
    -> ground-truth coverage goes 26.3% -> 100%
  * batch_3/batch_1/* and batch_3/batch_2/* (duplicates of batches 1 and 2) are excluded
  * split is stratified so every split keeps full GT coverage
  * adds notebooks/ to the bundle and colab_bootstrap.py into code/
  * OCR Dataset + SignverOD + StaVer are deliberately NOT bundled - Colab pulls them from Kaggle
"""
from __future__ import annotations

import csv
import glob
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

REPO = Path(r"C:\Users\hessa\OneDrive\Dropbox Backup\WorkSpace\GBC_AIML_Dev_2026\Deep Learning II\invoice-image-processing")
STAGE = Path(r"C:\Users\hessa\DL2_InvoiceAI_upload")
TARGET = 750
SEED = 42


def log(m):
    print(m, flush=True)


# ---------------------------------------------------------------- 1. resample
def resample() -> pd.DataFrame:
    inv = REPO / "data" / "raw" / "invoices"

    ann_csvs = sorted(glob.glob(str(inv / "batch_1" / "batch_1" / "*.csv")))
    gt = pd.concat([pd.read_csv(f) for f in ann_csvs], ignore_index=True)
    gt["stem"] = gt["File Name"].astype(str).str.replace(".jpg", "", regex=False).str.strip()
    gt = gt.drop_duplicates("stem")
    annotated = set(gt["stem"])
    log(f"  annotation CSVs : {[Path(f).name for f in ann_csvs]}")
    log(f"  annotated ids   : {len(annotated)}")

    # Every leaf folder holding jpgs, minus batch_3's duplicate copies of batches 1 and 2.
    leaves = [Path(d) for d in glob.glob(str(inv / "*" / "*" / "*")) if os.path.isdir(d)]
    def is_dup(p: Path) -> bool:
        return "batch_3" in p.parts and not p.name.startswith("batch3_")
    keep = sorted([p for p in leaves if not is_dup(p) and any(p.glob("*.jpg"))])
    drop = sorted([p for p in leaves if is_dup(p) and any(p.glob("*.jpg"))])
    log(f"  leaf folders    : {len(keep)} kept, {len(drop)} duplicate folders EXCLUDED "
        f"({sum(len(list(p.glob('*.jpg'))) for p in drop)} images)")

    rows = []
    for d in keep:
        for img in sorted(d.glob("*.jpg")):
            rows.append({"document_id": img.stem, "src": str(img), "leaf": d.name,
                         "has_ground_truth": img.stem in annotated})
    allimgs = pd.DataFrame(rows)
    log(f"  unique images   : {len(allimgs)}  (with GT: {int(allimgs.has_ground_truth.sum())})")

    have = allimgs[allimgs.has_ground_truth]
    if len(have) < TARGET:
        raise SystemExit(f"only {len(have)} annotated images, need {TARGET}")

    # Spread the pick evenly across batch_1's three subfolders for what diversity remains.
    per = TARGET // have.leaf.nunique()
    picked = pd.concat([g.sample(min(per, len(g)), random_state=SEED)
                        for _, g in have.groupby("leaf")])
    if len(picked) < TARGET:                      # top up any shortfall
        extra = have[~have.document_id.isin(picked.document_id)]
        picked = pd.concat([picked, extra.sample(TARGET - len(picked), random_state=SEED)])
    sample = picked.head(TARGET).reset_index(drop=True)

    assert sample.document_id.is_unique
    log(f"  sampled         : {len(sample)}  GT coverage {sample.has_ground_truth.mean():.1%}")
    log(f"  per leaf        : {sample.leaf.value_counts().to_dict()}")
    return sample


# ---------------------------------------------------------- 2. build manifest
def build_manifest(sample: pd.DataFrame, images_dir: Path) -> pd.DataFrame:
    images_dir.mkdir(parents=True, exist_ok=True)
    recs = []
    for i, r in enumerate(sample.itertuples(), 1):
        src = Path(r.src)
        try:
            with Image.open(src) as im:
                w, h = im.size
            corrupt = False
        except Exception:
            w = h = 0
            corrupt = True
        dst = images_dir / f"{r.document_id}.jpg"
        shutil.copyfile(src, dst)
        recs.append({"document_id": r.document_id,
                     "image_path": f"inputs/images/{dst.name}",
                     "width": w, "height": h, "file_type": "jpg",
                     "is_corrupt": corrupt, "split": "train",
                     "has_ground_truth": bool(r.has_ground_truth)})
        if i % 200 == 0:
            log(f"    ...{i} images")

    man = pd.DataFrame(recs)
    rng = np.random.default_rng(SEED)
    idx = np.array(man.index.to_numpy(), copy=True)
    rng.shuffle(idx)
    n = len(idx)
    man.loc[idx[: int(.16 * n)], "split"] = "val"
    man.loc[idx[int(.16 * n): int(.30 * n)], "split"] = "test"
    return man


# ------------------------------------------------------------- 3. rebuild bundle
def main():
    log("=" * 70)
    log("STEP 1  annotation-aware resample")
    sample = resample()

    inputs = STAGE / "inputs"
    images = inputs / "images"
    log("\nSTEP 2  rebuild inputs/ (removing the old 750-image set)")
    if images.exists():
        old = sum(f.stat().st_size for f in images.glob("*")) / 1024 / 1024
        log(f"  removing previous images/ ({old:.1f} MB)")
        shutil.rmtree(images)
    man = build_manifest(sample, images)

    man.to_csv(inputs / "invoice_manifest.csv", index=False)
    # keep the repo's canonical copy in step with what Drive holds
    (REPO / "data" / "processed").mkdir(parents=True, exist_ok=True)
    prev = REPO / "data" / "processed" / "invoice_manifest.csv"
    if prev.exists():
        shutil.copyfile(prev, prev.with_name("invoice_manifest_PREV_26pct.csv"))
    man.drop(columns=[]).to_csv(prev, index=False)
    for stale in ["invoice_manifest_original_paths.csv"]:
        p = inputs / stale
        if p.exists():
            p.unlink()

    log(f"  manifest        : {len(man)} rows, GT {man.has_ground_truth.mean():.1%}")
    log(f"  split           : {man.split.value_counts().to_dict()}")
    log(f"  GT by split     : {man.groupby('split').has_ground_truth.mean().round(3).to_dict()}")

    log("\nSTEP 3  code/ + notebooks/")
    code = STAGE / "code"
    (code / "src").mkdir(parents=True, exist_ok=True)
    (code / "scripts").mkdir(parents=True, exist_ok=True)
    for sub in ("src", "scripts"):
        for f in sorted((REPO / sub).glob("*.py")):
            shutil.copy2(f, code / sub / f.name)
    shutil.copy2(REPO / "colab" / "colab_bootstrap.py", code / "colab_bootstrap.py")
    contract = REPO / "model_interface_contract.md"
    if contract.exists():
        shutil.copy2(contract, code / contract.name)

    nbdir = STAGE / "notebooks"
    if nbdir.exists():
        shutil.rmtree(nbdir)
    nbdir.mkdir(parents=True)
    for f in sorted((REPO / "colab" / "notebooks").glob("*.ipynb")):
        shutil.copy2(f, nbdir / f.name)
    shutil.copy2(REPO / "colab" / "README.md", nbdir / "README.md")
    log(f"  notebooks       : {len(list(nbdir.glob('*.ipynb')))}")
    log(f"  code/           : {sum(1 for _ in code.rglob('*') if _.is_file())} files")

    # annotations coverage note now that coverage is 100%
    (inputs / "annotations" / "README.txt").write_text(
        "Real ground truth: File Name, Json Data{invoice,items,subtotal,payment_instructions}, "
        "OCRed Text.\n\n"
        "These CSVs exist ONLY for batch_1 (1,413 annotated images).\n"
        "The manifest is now sampled ANNOTATION-AWARE, so all 750 manifest images have a row\n"
        "here -> 100% ground-truth coverage (previously 26.3%).\n\n"
        "Trade-off: because only batch_1 is annotated, the manifest no longer spans batches\n"
        "2 and 3. Visual diversity is narrower; label availability is complete. Say so in the report.\n",
        encoding="utf-8")

    bundle = {
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Hybrid by role (2026-07-22)",
        "manifest_rows": len(man),
        "gt_coverage": round(float(man.has_ground_truth.mean()), 4),
        "split": man.split.value_counts().to_dict(),
        "images_mb": round(sum(f.stat().st_size for f in images.glob("*")) / 1024 / 1024, 1),
        "notebooks": sorted(p.name for p in nbdir.glob("*.ipynb")),
        "not_bundled_fetched_from_kaggle": {
            "ocr_dataset": "senju14/ocr-dataset-of-multi-type-documents",
            "invoices": "osamahosamabdellatif/high-quality-invoice-images-for-ocr",
            "signatures": "victordibia/signverod",
            "stamps": "rtatman/stamp-verification-staver-dataset",
        },
    }
    (STAGE / "BUNDLE_MANIFEST.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    log("\n" + "=" * 70)
    for top in ["code", "inputs", "notebooks", "outputs", "runs"]:
        d = STAGE / top
        if d.exists():
            n = sum(1 for f in d.rglob("*") if f.is_file())
            mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1024 / 1024
            log(f"  {top:<11} {n:5d} files  {mb:8.1f} MB")
    tot = sum(f.stat().st_size for f in STAGE.rglob("*") if f.is_file()) / 1024 / 1024
    log(f"  {'TOTAL':<11} {sum(1 for f in STAGE.rglob('*') if f.is_file()):5d} files  {tot:8.1f} MB")
    log("=" * 70)


if __name__ == "__main__":
    main()
