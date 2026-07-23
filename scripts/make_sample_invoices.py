"""Build app/sample_invoices/ for the demo — a small, repo-friendly set."""
import shutil
from pathlib import Path
from PIL import Image

REPO = Path(r"C:\Users\hessa\OneDrive\Dropbox Backup\WorkSpace\GBC_AIML_Dev_2026\Deep Learning II\invoice-image-processing")
DST = REPO / "app" / "sample_invoices"
DST.mkdir(parents=True, exist_ok=True)

INV = REPO / "data/raw/invoices/batch_1/batch_1/batch1_1"
# 3 clean invoices (region + reference-based verdict demo)
clean = {
    "invoice_clean_01.jpg": INV / "batch1-0461.jpg",
    "invoice_clean_02.jpg": INV / "batch1-0074.jpg",
    "invoice_clean_03.jpg": INV / "batch1-0232.jpg",
}
for name, src in clean.items():
    if src.exists():
        shutil.copy2(src, DST / name)

# a signature document (SignverOD) — demonstrates the signature detector firing
sig = REPO / "data/raw/signatures/images/aah97e00-page02_2.png"
if sig.exists():
    shutil.copy2(sig, DST / "signed_document_example.png")

# a stamp scan (StaVer) — downscaled to keep the repo light
stamp = REPO / "data/raw/stamps/StaVer/scans/scans/stampDS-00001.png"
if stamp.exists():
    im = Image.open(stamp).convert("RGB")
    im.thumbnail((1200, 1200))
    im.save(DST / "stamped_document_example.jpg", quality=85)

readme = DST / "README.md"
readme.write_text(
    "# Sample images for the Streamlit demo\n\n"
    "Upload these in the **Live Demo** view.\n\n"
    "| File | What it demonstrates |\n|---|---|\n"
    "| `invoice_clean_01/02/03` | Real clean invoices — region detection fires; the verdict runs "
    "on reference + date signals. The visual rule (if enabled) correctly reports *no mark* — these "
    "digital templates are unsigned. |\n"
    "| `signed_document_example.png` | A signature document (SignverOD) — shows Diana's **signature** "
    "detector firing, so the visual rule can flip to pass. |\n"
    "| `stamped_document_example.jpg` | A stamp scan (StaVer, downscaled) — shows the **stamp** "
    "detector firing. |\n\n"
    "The clean invoices show the everyday path; the two document samples show the visual detector "
    "works when a mark is actually present.\n",
    encoding="utf-8")

print("built", DST)
tot = 0
for f in sorted(DST.iterdir()):
    kb = f.stat().st_size / 1024
    tot += kb
    print(f"  {f.name:32s} {kb:8.1f} KB")
print(f"total {tot/1024:.1f} MB")
