# models/

Trained detector weights. Binary weight files (`.pt`, `.pth`, `.h5`, `.onnx`, `.weights`,
`checkpoints/`) are excluded from git via `.gitignore` — they're too large and not meaningful
to diff. Each subfolder should contain a short `README.md` documenting what's actually
inside once a member trains something (framework, version, training data subset, date).

| Folder | Owner | Contents |
|---|---|---|
| `region_detector/` | Jordan | SSD-style (or YOLOv8 fallback) detector for the 14 invoice region labels in `config/label_schema.json`. |
| `stamp_detector/` | Diana | Detector for the `stamp` label. |
| `signature_detector/` | Diana | Detector for the `signature` label. |

If your weights are too large for git even with Git LFS, host them externally (Google Drive,
a GitHub Release asset) and put the download link + instructions in that folder's README
instead of the binary.
