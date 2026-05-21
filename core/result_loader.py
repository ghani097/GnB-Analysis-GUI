"""
Loads pipeline output files into DataFrames for the Data Preview tab.
Detects output type from the output folder contents.
"""

from __future__ import annotations
from pathlib import Path

import pandas as pd


def detect_output_type(output_folder: str) -> str:
    """
    Returns: 'sumeeta_xlsx' | 'custom_walking' | 'custom_both' | 'default' | 'empty'
    """
    folder = Path(output_folder)
    if (folder / "sumeeta_gait_parameters.xlsx").exists():
        return "sumeeta_xlsx"
    has_gait   = (folder / "custom_gait_outcomes.xlsx").exists()
    has_static = (folder / "custom_static_outcomes.xlsx").exists()
    if has_gait and has_static:
        return "custom_both"
    if has_gait:
        return "custom_walking"
    if list(folder.glob("Outcomes for *.csv")):
        return "default"
    return "empty"


def load_outputs(output_folder: str) -> dict[str, pd.DataFrame]:
    """
    Returns a dict of label → DataFrame.
    Keys: 'Gait Parameters', 'Static Parameters', 'Outcomes' (default pipeline)
    """
    kind = detect_output_type(output_folder)
    folder = Path(output_folder)
    result: dict[str, pd.DataFrame] = {}

    if kind == "sumeeta_xlsx":
        df = pd.read_excel(folder / "sumeeta_gait_parameters.xlsx",
                           sheet_name="Gait Parameters", engine="openpyxl")
        result["Gait Parameters"] = df

    elif kind in ("custom_walking", "custom_both"):
        gait_path = folder / "custom_gait_outcomes.xlsx"
        if gait_path.exists():
            result["Gait Parameters"] = pd.read_excel(gait_path, engine="openpyxl")
        if kind == "custom_both":
            static_path = folder / "custom_static_outcomes.xlsx"
            if static_path.exists():
                result["Static Parameters"] = pd.read_excel(static_path,
                                                             engine="openpyxl")

    elif kind == "default":
        dfs = []
        for csv_path in sorted(folder.glob("Outcomes for *.csv")):
            participant = csv_path.stem.replace("Outcomes for ", "")
            try:
                df = pd.read_csv(csv_path)
                df.insert(0, "Participant", participant)
                dfs.append(df)
            except Exception:
                pass
        if dfs:
            result["Outcomes"] = pd.concat(dfs, ignore_index=True)

    return result


def compute_summary(df: pd.DataFrame) -> str:
    """Return a human-readable summary string for a DataFrame."""
    lines = [f"Rows: {len(df)}   Columns: {len(df.columns)}"]
    for col in ("Participant", "Condition", "Test"):
        if col in df.columns:
            counts = df[col].value_counts()
            lines.append(f"\n{col} breakdown:")
            for k, v in counts.items():
                lines.append(f"  {k}: {v}")
    return "\n".join(lines)
