"""
Classifies CSV files as 'walking', 'static', or 'unknown' for Custom+Both mode.
Two-tier: filename keyword matching first (no I/O), then row-count fallback.
"""

from __future__ import annotations
import re
from pathlib import Path

# Filename substrings that definitively indicate a static balance recording
_STATIC_KW = [
    "firm eo", "firm ec", "compliant eo", "compliant ec",
    "firm_eo", "firm_ec", "compliant_eo", "compliant_ec",
    " eo", " ec",                                  # trailing suffix variants
    "static", "standing",
]

# Filename substrings that definitively indicate a walking recording
_WALK_KW = ["walk hf", "walk ht", "walk_hf", "walk_ht", "walking", "gait"]

# Sumeeta-style filename: p<N> <cond> <trial>  (p|pl, then id, then bl/b/st/cb/pl)
_SUMEETA_RE = re.compile(
    r"^(?:p|pl)\s*\d+\s*[,\s]+(?:bl|b|st|cb|pl)\s*\d+\s*$",
    re.IGNORECASE,
)

# Files above this row count are treated as continuous-walking recordings
# (Sumeeta ≈ 5000 rows; standard GnB static ≈ 3000; standard GnB walking ≈ 2400)
_ROW_THRESHOLD = 4000


def classify_csv(filepath: Path) -> str:
    """Return 'walking', 'static', or 'unknown'."""
    stem = filepath.stem.lower()

    # Tier 1 — static keywords
    for kw in _STATIC_KW:
        if kw in stem:
            return "static"

    # Tier 1 — walking keywords
    for kw in _WALK_KW:
        if kw in stem:
            return "walking"

    # Tier 1 — Sumeeta filename pattern
    if _SUMEETA_RE.match(stem):
        return "walking"

    # Tier 2 — row count
    try:
        with open(filepath, "rb") as f:
            n_lines = sum(1 for _ in f)
        n_rows = max(0, n_lines - 1)   # subtract header
        if n_rows >= _ROW_THRESHOLD:
            return "walking"
        if n_rows > 0:
            return "static"
    except OSError:
        pass

    return "unknown"


def classify_folder(folder: Path) -> dict[str, list[Path]]:
    """Scan folder for CSVs and return {'walking': [...], 'static': [...], 'unknown': [...]}."""
    result: dict[str, list[Path]] = {"walking": [], "static": [], "unknown": []}
    for f in sorted(folder.glob("*.csv")):
        label = classify_csv(f)
        result[label].append(f)
    return result
