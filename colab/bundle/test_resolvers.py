"""Smoke-test the Drive path resolvers against the REAL local data layouts."""
import sys
from pathlib import Path

REPO = Path(r"C:\Users\hessa\OneDrive\Dropbox Backup\WorkSpace\GBC_AIML_Dev_2026\Deep Learning II\invoice-image-processing")
sys.path.insert(0, str(REPO / "colab"))
import colab_bootstrap as CB

RAW = REPO / "data" / "raw"

print("=== TEST 1: flat layout (what was uploaded) ===")
p = CB.resolve_dataset_root(RAW / "signatures", ["images", "image_ids.csv"])
print("  signatures root ->", p.name)
d = CB.resolve_files_dir(RAW / "signatures" / "images", "*.png")
print("  images          ->", d.name, len(list(d.glob("*.png"))), "png")

print("\n=== TEST 2: vendor double-nesting (StaVer as shipped) ===")
p = CB.resolve_dataset_root(RAW / "stamps", ["scans", "ground-truth-maps"])
print("  stamps root ->", p.name)
for sub, pat, exp in [("scans", "*.png", 427), ("ground-truth-maps", "*.png", 400),
                      ("info", "*.txt", 400)]:
    d = CB.resolve_files_dir(p / sub, pat)
    n = len(list(d.glob(pat)))
    print(f"  {sub:20s} -> {n:4d} files (expect {exp})  {'OK' if n >= exp else 'LOW'}")

print("\n=== TEST 3: extra parent level (the mistake guarded against) ===")
p = CB.resolve_dataset_root(RAW / "invoices" / "OCR Dataset of Multi-type Documents",
                            ["train/annotations", "val/annotations", "test/annotations"])
print("  resolved ->", p.name)
for sp, exp in [("train", 778), ("val", 97), ("test", 98)]:
    ni = len(list((p / sp / "images").glob("*")))
    na = len(list((p / sp / "annotations").glob("*.json")))
    print(f"    {sp:6s} {ni:4d} imgs / {na:4d} json (expect {exp})  "
          f"{'OK' if ni == exp == na else 'MISMATCH'}")

print("\n=== TEST 4: missing folder -> actionable error ===")
try:
    CB.resolve_dataset_root(RAW / "stamps", ["definitely_not_here"])
    print("  !! should have raised")
except FileNotFoundError as e:
    print("  raised OK:", str(e).splitlines()[0])

print("\n=== TEST 5: nonexistent base -> actionable error ===")
try:
    CB.resolve_files_dir(RAW / "no_such_folder", "*.png")
    print("  !! should have raised")
except FileNotFoundError as e:
    print("  raised OK:", str(e).splitlines()[0])

print("\nall resolver tests done")
