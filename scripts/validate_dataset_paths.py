"""
validate_dataset_paths.py

Sanity-checks that expected data/ and outputs/ files exist and are non-empty, and reports
which pipeline stages (Rolando/Diana/Jordan/Damir/Hessam) have and have not produced their
contractual outputs yet. Intended to be run:
  - after scripts/download_datasets.py, to confirm raw data landed correctly
  - before running Hessam's integration notebook, to confirm upstream outputs exist

Usage:
    python scripts/validate_dataset_paths.py
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (description, path, "raw_data" | "output") -- raw_data dirs just need >=1 file somewhere
# inside them; output paths need to exist as a file.
RAW_DATA_CHECKS = [
    ("Rolando: raw invoices", "data/raw/invoices"),
    ("Diana: raw signatures", "data/raw/signatures"),
    ("Diana: raw stamps", "data/raw/stamps"),
]

MEMBER_OUTPUT_CHECKS = {
    "Rolando (data ingestion)": [
        "data/processed/invoice_manifest.csv",
        "outputs/reports/data_quality_report.md",
        "outputs/figures/sample_invoice_grid.png",
        "outputs/figures/preprocessing_examples.png",
    ],
    "Diana (stamp/signature)": [
        "outputs/predictions/stamp_signature_predictions.csv",
        "outputs/metrics/stamp_signature_metrics.json",
        "outputs/figures/stamp_signature_detection_examples.png",
    ],
    "Jordan (region/IoU)": [
        "outputs/predictions/region_predictions.csv",
        "outputs/metrics/region_iou_metrics.json",
        "outputs/figures/region_detection_examples.png",
    ],
    "Damir (OCR/parameters/terms)": [
        "outputs/predictions/ocr_outputs.csv",
        "outputs/predictions/parameter_presence_results.csv",
        "outputs/predictions/terms_extraction_results.csv",
        "outputs/metrics/ocr_parameter_metrics.json",
    ],
    "Hessam (integration)": [
        "outputs/reports/final_pipeline_report.md",
        "app/streamlit_app.py",
    ],
}


def has_any_file(dir_path: Path) -> bool:
    if not dir_path.exists():
        return False
    return any(p.is_file() and p.name != ".gitkeep" for p in dir_path.rglob("*"))


def main() -> None:
    print("=== Raw data folders ===")
    any_missing_raw = False
    for label, rel_path in RAW_DATA_CHECKS:
        full = REPO_ROOT / rel_path
        ok = has_any_file(full)
        status = "OK" if ok else "MISSING/EMPTY"
        if not ok:
            any_missing_raw = True
        print(f"  [{status:14}] {label} -> {rel_path}")

    print("\n=== Member output contracts (see model_interface_contract.md) ===")
    any_missing_output = False
    for member, rel_paths in MEMBER_OUTPUT_CHECKS.items():
        print(f"\n  {member}:")
        for rel_path in rel_paths:
            full = REPO_ROOT / rel_path
            ok = full.exists() and full.stat().st_size > 0
            status = "OK" if ok else "MISSING"
            if not ok:
                any_missing_output = True
            print(f"    [{status:8}] {rel_path}")

    print("\n=== Summary ===")
    if any_missing_raw:
        print("- Some raw datasets are missing. Run scripts/download_datasets.py --dataset all")
    if any_missing_output:
        print(
            "- Some member outputs are missing. This is expected before that member's "
            "notebook has been run — not an error at repo-scaffold time."
        )
    if not any_missing_raw and not any_missing_output:
        print("Everything present. Pipeline is ready end-to-end.")


if __name__ == "__main__":
    main()
