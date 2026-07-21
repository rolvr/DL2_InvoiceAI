"""
data_loader.py — helpers for reading the invoice manifest and locating images.

Owner: Rolando (data ingestion). Others should import from here rather than re-parsing
the manifest CSV themselves.
"""

from pathlib import Path

import pandas as pd

from src.config import PATHS

MANIFEST_COLUMNS = ["document_id", "image_path", "width", "height", "file_type", "is_corrupt", "split"]


def load_manifest(manifest_path: Path | None = None) -> pd.DataFrame:
    """Load data/processed/invoice_manifest.csv produced by Rolando's notebook.

    Raises FileNotFoundError with a clear message if it hasn't been generated yet.
    """
    manifest_path = manifest_path or (PATHS.processed_dir / "invoice_manifest.csv")
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found at {manifest_path}. Run Rolando's notebook "
            "(members/rolando_data_ingestion/01_rolando_data_ingestion_preparation.ipynb) first."
        )
    return pd.read_csv(manifest_path)


def list_raw_images(raw_subdir: str = "invoices", extensions=(".jpg", ".jpeg", ".png", ".tif", ".tiff")) -> list[Path]:
    """List image files under data/raw/<raw_subdir>, recursively."""
    target = PATHS.raw_dir / raw_subdir
    if not target.exists():
        raise FileNotFoundError(
            f"{target} does not exist. Run scripts/download_datasets.py first."
        )
    return sorted(p for p in target.rglob("*") if p.suffix.lower() in extensions)


def get_split(manifest: pd.DataFrame, split: str) -> pd.DataFrame:
    """Filter the manifest to one of 'train' / 'val' / 'test'."""
    return manifest[manifest["split"] == split].reset_index(drop=True)


def resolve_image_path(document_id: str, manifest: pd.DataFrame) -> Path:
    """Given a document_id, resolve the absolute path to its image via the manifest."""
    row = manifest.loc[manifest["document_id"] == document_id]
    if row.empty:
        raise KeyError(f"document_id '{document_id}' not found in manifest.")
    rel_path = row.iloc[0]["image_path"]
    return PATHS.repo_root / rel_path
