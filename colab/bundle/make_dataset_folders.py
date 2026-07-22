"""
Create the inputs/datasets/ folder structure in the Drive staging bundle, and print an exact
SOURCE -> DESTINATION copy map.

The Drive layout deliberately FLATTENS the vendors' double-nesting
(e.g. StaVer/scans/scans/ -> stamps/scans/) so notebook paths stay readable.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(r"C:\Users\hessa\OneDrive\Dropbox Backup\WorkSpace\GBC_AIML_Dev_2026\Deep Learning II\invoice-image-processing")
RAW = REPO / "data" / "raw"
STAGE = Path(r"C:\Users\hessa\DL2_InvoiceAI_upload")
DS = STAGE / "inputs" / "datasets"

OCR = RAW / "invoices" / "OCR Dataset of Multi-type Documents" / "invoice"
STAVER = RAW / "stamps" / "StaVer"

# (destination folder, source folder, who needs it, note)
MAP = [
    ("ocr_multitype/train/images",       OCR / "train" / "images",            "Jordan, Damir", "778 receipt images"),
    ("ocr_multitype/train/annotations",  OCR / "train" / "annotations",       "Jordan, Damir", "778 JSON"),
    ("ocr_multitype/val/images",         OCR / "val" / "images",              "Jordan, Damir", "97 images"),
    ("ocr_multitype/val/annotations",    OCR / "val" / "annotations",         "Jordan, Damir", "97 JSON"),
    ("ocr_multitype/test/images",        OCR / "test" / "images",             "Jordan, Damir", "98 images"),
    ("ocr_multitype/test/annotations",   OCR / "test" / "annotations",        "Jordan, Damir", "98 JSON"),
    ("signatures/images",                RAW / "signatures" / "images",       "Diana",         "2,765 signature PNGs"),
    ("stamps/scans",                     STAVER / "scans" / "scans",          "Diana",         "427 stamp scans (FLATTEN: scans/scans -> scans)"),
    ("stamps/ground-truth-maps",         STAVER / "ground-truth-maps" / "ground-truth-maps", "Diana", "400 binary GT masks (FLATTEN)"),
    ("stamps/info",                      STAVER / "info" / "info",            "Diana",         "400 txt (numStamps)"),
]

# loose files that sit at the root of a dataset folder
FILES = [
    ("signatures", RAW / "signatures" / "train.csv",      "Diana", "signature boxes (normalized)"),
    ("signatures", RAW / "signatures" / "test.csv",       "Diana", "held-out boxes"),
    ("signatures", RAW / "signatures" / "image_ids.csv",  "Diana", "image_id -> file_name + dims"),
    ("signatures", RAW / "signatures" / "categories.csv", "Diana", "1=signature 2=initials 3=redaction 4=date"),
    ("signatures", RAW / "signatures" / "labelmap.txt",   "Diana", "same, protobuf form"),
]

OPTIONAL = [
    ("invoices_raw/batch_1", RAW / "invoices" / "batch_1" / "batch_1",
     "Rolando (optional)", "1,489 imgs + the 3 batch1_*.csv - ONLY if re-deriving the manifest"),
]


def size_of(p: Path) -> tuple[int, float]:
    if not p.exists():
        return 0, 0.0
    fs = [f for f in p.rglob("*") if f.is_file()]
    return len(fs), sum(f.stat().st_size for f in fs) / 1024 / 1024


def main():
    print("Creating folders under", DS, "\n")
    rows, total_mb = [], 0.0

    for dest, src, who, note in MAP:
        d = DS / dest
        d.mkdir(parents=True, exist_ok=True)
        n, mb = size_of(src)
        total_mb += mb
        rows.append((dest, src, who, n, mb, note))

    for dest, src, who, note in FILES:
        (DS / dest).mkdir(parents=True, exist_ok=True)
        mb = src.stat().st_size / 1024 / 1024 if src.exists() else 0.0
        total_mb += mb
        rows.append((f"{dest}/{src.name}", src, who, 1 if src.exists() else 0, mb, note))

    for dest, src, who, note in OPTIONAL:
        (DS / dest).mkdir(parents=True, exist_ok=True)
        n, mb = size_of(src)
        rows.append((dest + "  [OPTIONAL]", src, who, n, mb, note))

    # A marker file in each leaf so the empty folders actually survive a browser upload.
    for dest, *_ in MAP + OPTIONAL:
        (DS / dest / "_PUT_FILES_HERE.txt").write_text(
            f"Copy the CONTENTS of the matching local folder into this folder.\n"
            f"See inputs/datasets/COPY_MAP.md for the exact source path.\n"
            f"Delete this marker once populated.\n", encoding="utf-8")

    # Write the copy map into the bundle itself.
    lines = ["# Drive copy map — what goes where", "",
             "Local repo root:", "", f"`{REPO}`", "",
             "Copy the **contents** of each SOURCE folder into the matching DESTINATION folder",
             "under `MyDrive/DL2_InvoiceAI/inputs/datasets/`.", "",
             "Note the FLATTENING: the vendors double-nest some folders "
             "(`StaVer/scans/scans/`); Drive uses the flat form.", "",
             "| # | Destination (in Drive) | Source (local, under `data/raw/`) | For | Files | MB |",
             "|---|---|---|---|---|---|"]
    for i, (dest, src, who, n, mb, note) in enumerate(rows, 1):
        try:
            rel = src.relative_to(RAW)
        except ValueError:
            rel = src
        lines.append(f"| {i} | `inputs/datasets/{dest}` | `{rel}` | {who} | {n:,} | {mb:,.0f} |")
    lines += ["", f"**Total to upload: ~{total_mb:,.0f} MB** (excluding the optional Rolando folder).", ""]
    (DS / "COPY_MAP.md").write_text("\n".join(lines), encoding="utf-8")

    w = max(len(r[0]) for r in rows) + 2
    print(f"{'DESTINATION':<{w}} {'FILES':>7} {'MB':>8}  SOURCE")
    print("-" * (w + 60))
    for dest, src, who, n, mb, note in rows:
        try:
            rel = src.relative_to(RAW)
        except ValueError:
            rel = src
        print(f"{dest:<{w}} {n:>7,} {mb:>8,.0f}  data/raw/{rel}")
    print("-" * (w + 60))
    print(f"{'TOTAL (required)':<{w}} {'':>7} {total_mb:>8,.0f} MB")
    print(f"\nCOPY_MAP.md written to {DS / 'COPY_MAP.md'}")


if __name__ == "__main__":
    main()
