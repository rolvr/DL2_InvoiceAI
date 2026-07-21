"""
prepare_folders.py

Creates every folder this project expects to exist (data/, outputs/, models/ subfolders),
including empty ones that git won't track on its own. Safe to re-run at any time.

Usage:
    python scripts/prepare_folders.py
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_DIRS = [
    "data/raw/invoices",
    "data/raw/signatures",
    "data/raw/stamps",
    "data/interim",
    "data/processed",
    "data/annotations",
    "data/ocr_text",
    "models/region_detector",
    "models/stamp_detector",
    "models/signature_detector",
    "outputs/metrics",
    "outputs/figures",
    "outputs/predictions",
    "outputs/final_json/sample_invoice_outputs",
    "outputs/reports",
    "members/hessam_pm_integration/outputs",
    "members/rolando_data_ingestion/outputs",
    "members/diana_stamp_signature/outputs",
    "members/jordan_region_iou/outputs",
    "members/damir_ocr_terms/outputs",
    "app/sample_invoices",
]


def main() -> None:
    created = []
    for rel_dir in EXPECTED_DIRS:
        target = REPO_ROOT / rel_dir
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(rel_dir)

        # Keep otherwise-empty, gitignored data/output dirs visible in git via .gitkeep.
        gitkeep = target / ".gitkeep"
        if not any(target.iterdir()):
            gitkeep.touch(exist_ok=True)

    if created:
        print("Created folders:")
        for d in created:
            print(f"  - {d}")
    else:
        print("All expected folders already exist. Nothing to do.")


if __name__ == "__main__":
    main()
