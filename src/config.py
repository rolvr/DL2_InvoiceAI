"""
config.py — central, path-safe project configuration.

Every notebook should get its paths from here instead of hardcoding strings, so the same
notebook works unmodified on Colab, on Windows, and on Linux/Mac.

Usage:
    from src.config import PATHS, load_label_schema, load_required_fields

    manifest_path = PATHS.processed_dir / "invoice_manifest.csv"
"""

import json
from dataclasses import dataclass
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from `start` (or this file) until a folder containing requirements.txt
    is found. This lets the same code work whether it's imported from src/, from a
    members/*/*.ipynb notebook, or from a Colab working directory after a git clone."""
    current = (start or Path(__file__).resolve()).parent
    for candidate in [current, *current.parents]:
        if (candidate / "requirements.txt").exists() and (candidate / "config").exists():
            return candidate
    # Fallback: assume two levels up from src/config.py (repo_root/src/config.py)
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ProjectPaths:
    repo_root: Path

    @property
    def config_dir(self) -> Path:
        return self.repo_root / "config"

    @property
    def data_dir(self) -> Path:
        return self.repo_root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def interim_dir(self) -> Path:
        return self.data_dir / "interim"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def annotations_dir(self) -> Path:
        return self.data_dir / "annotations"

    @property
    def ocr_text_dir(self) -> Path:
        return self.data_dir / "ocr_text"

    @property
    def models_dir(self) -> Path:
        return self.repo_root / "models"

    @property
    def outputs_dir(self) -> Path:
        return self.repo_root / "outputs"

    @property
    def figures_dir(self) -> Path:
        return self.outputs_dir / "figures"

    @property
    def metrics_dir(self) -> Path:
        return self.outputs_dir / "metrics"

    @property
    def predictions_dir(self) -> Path:
        return self.outputs_dir / "predictions"

    @property
    def final_json_dir(self) -> Path:
        return self.outputs_dir / "final_json" / "sample_invoice_outputs"

    @property
    def reports_dir(self) -> Path:
        return self.outputs_dir / "reports"

    def member_outputs_dir(self, member_folder: str) -> Path:
        """e.g. member_outputs_dir('rolando_data_ingestion')"""
        return self.repo_root / "members" / member_folder / "outputs"


PATHS = ProjectPaths(repo_root=find_repo_root())


def load_label_schema() -> dict:
    """Returns dict with 'region_labels' and 'visual_element_labels' lists."""
    with open(PATHS.config_dir / "label_schema.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_required_fields() -> dict:
    """Returns dict with 'default_required_fields' (list) and 'custom_fields' (list)."""
    with open(PATHS.config_dir / "required_fields_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dirs(*dirs: Path) -> None:
    """Create any of the given directories if they don't already exist."""
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
