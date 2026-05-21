"""
fresh_analysis.py — Analyses pipeline output and generates figures + report.

Usage:
    python fresh_analysis.py <output_folder>

Detects output type from the folder contents:
  - sumeeta_gait_parameters.xlsx or custom_gait_outcomes.xlsx
    → condition comparison analysis (8 figures)
  - Outcomes for *.csv  → default pipeline descriptive analysis (5 figures)

All figures are saved as fig*.png in <output_folder>.
Report is saved as fresh_analysis_report.md in <output_folder>.
"""

from __future__ import annotations
import sys
import re
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy import stats


# ── Colour palette ────────────────────────────────────────────────────────────

COND_COLORS = {
    "Baseline":        "#4C9BE8",
    "Stroop":          "#E87B4C",
    "CountingBackward":"#5CDB5C",
    "PhysicalLoad":    "#C16FE8",
}
DEFAULT_COLORS = plt.cm.tab10.colors

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "figure.facecolor": "white",
    "axes.facecolor": "#F8F9FA",
    "axes.grid": True,
    "grid.alpha": 0.4,
})


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python fresh_analysis.py <output_folder>")
        sys.exit(1)

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"ERROR: folder not found: {folder}")
        sys.exit(1)

    output_type = _detect_type(folder)
    print(f"Detected output type: {output_type}")

    if output_type == "condition_comparison":
        df, source = _load_gait_xlsx(folder)
        print(f"Loaded {len(df)} rows from {source}")
        figs, report = analyse_conditions(df, folder)
    elif output_type == "default":
        df = _load_default_csvs(folder)
        print(f"Loaded {len(df)} rows from Outcomes for *.csv files")
        figs, report = analyse_default(df, folder)
    else:
        print("ERROR: No recognisable pipeline output found in folder.")
        sys.exit(1)

    for fname in figs:
        print(f"Saved figure: {fname}")

    report_path = folder / "fresh_analysis_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Saved report: {report_path}")


# ── Detection & loading ───────────────────────────────────────────────────────

def _detect_type(folder: Path) -> str:
    for name in ("sumeeta_gait_parameters.xlsx", "custom_gait_outcomes.xlsx"):
        if (folder / name).exists():
            return "condition_comparison"
    if list(folder.glob("Outcomes for *.csv")):
        return "default"
    return "unknown"


def _load_gait_xlsx(folder: Path) -> tuple[pd.DataFrame, str]:
    for name in ("sumeeta_gait_parameters.xlsx", "custom_gait_outcomes.xlsx"):
        path = folder / name
        if path.exists():
            if "sumeeta" in name:
                df = pd.read_excel(path, sheet_name="Gait Parameters", engine="openpyxl")
            else:
                df = pd.read_excel(path, engine="openpyxl")
            return df, name
    raise FileNotFoundError("No gait XLSX found.")


def _load_default_csvs(folder: Path) -> pd.DataFrame:
    dfs = []
    for p in sorted(folder.glob("Outcomes for *.csv")):
        participant = p.stem.replace("Outcomes for ", "")
        df = pd.read_csv(p)
        df.insert(0, "Participant", participant)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
#  CONDITION COMPARISON ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

GAIT_METRICS = {
    "WalkingSpeed_m_s":           ("Walking Speed",          "m/s"),
    "StepLength_m":               ("Step Length",            "m"),
    "WalkingBalance_pct":         ("Walking Balance",        "%"),
    "StepTime_s":                 ("Step Time",              "s"),
    "StepLength_Variability_pct": ("Step Length Variability","%"),
    "StepTime_Variability_pct":   ("Step Time Variability",  "%"),
    "StepLength_Asymmetry_pct":   ("Step Length Asymmetry",  "%"),
    "StepTime_Asymmetry_pct":     ("Step Time Asymmetry",    "%"),
}


def analyse_conditions(df: pd.DataFrame, folder: Path) -> tuple[list[str], str]:
    conditions = df["Condition"].unique().tolist() if "Condition" in df.columns else []
    colors = {c: COND_COLORS.get(c, "#888") for c in conditions}
    saved = []

    # Figure 1: Walking Speed violin
    saved.append(_violin_figure(df, "WalkingSpeed_m_s", "Walking Speed (m/s)",
                                 "Walking Speed", conditions, colors, folder,
                                 "fig1_speed_by_condition.png"))

    # Figure 2: Step Length violin
    saved.append(_violin_figure(df, "StepLength_m", "Step Length (m)",
                                 "Step Length", conditions, colors, folder,
                                 "fig2_step_length_by_condition.png"))

    # Figure 3: Walking Balance violin
    saved.append(_violin_figure(df, "WalkingBalance_pct", "Walking Balance (%)",
                                 "Walking Balance", conditions, colors, folder,
                                 "fig3_balance_by_condition.png"))

    # Figure 4: Step Time violin
    saved.append(_violin_figure(df, "StepTime_s", "Step Time (s)",
                                 "Step Time", conditions, colors, folder,
                                 "fig4_step_time_by_condition.png"))

    # Figure 5: Variability comparison
    saved.append(_dual_metric_figure(
        df, "StepLength_Variability_pct", "StepTime_Variability_pct",
        "Step Length Variability (%)", "Step Time Variability (%)",
        "Step Variability by Condition", conditions, colors, folder,
        "fig5_variability_by_condition.png"))

    # Figure 6: Asymmetry comparison
    saved.append(_dual_metric_figure(
        df, "StepLength_Asymmetry_pct", "StepTime_Asymmetry_pct",
        "Step Length Asymmetry (%)", "Step Time Asymmetry (%)",
        "Step Asymmetry by Condition", conditions, colors, folder,
        "fig6_asymmetry_by_condition.png"))

    # Figure 7: p-value heatmap
    p_matrix, cond_list = _pairwise_pvalues(df, "WalkingSpeed_m_s", conditions)
    saved.append(_heatmap_figure(p_matrix, cond_list, folder,
                                  "fig7_stats_heatmap.png"))

    # Figure 8: Summary dashboard (4 key metrics mean ± SEM)
    saved.append(_summary_dashboard(df, conditions, colors, folder,
                                     "fig8_summary_dashboard.png"))

    # Stats table for report
    stats_table = _compute_stats_table(df, conditions)
    report = _build_condition_report(df, conditions, stats_table)

    return [str(s) for s in saved if s is not None], report


def _violin_figure(df, col, ylabel, title, conditions, colors, folder, fname):
    if col not in df.columns:
        return None
    fig, ax = plt.subplots(figsize=(9, 5))
    data = [df[df["Condition"] == c][col].dropna().values for c in conditions]
    clr  = [colors[c] for c in conditions]

    parts = ax.violinplot(data, showmedians=True, showextrema=True)
    for i, (pc, c) in enumerate(zip(parts["bodies"], clr)):
        pc.set_facecolor(c)
        pc.set_alpha(0.6)
    for key in ("cmedians", "cmaxes", "cmins", "cbars"):
        parts[key].set_color("#333")

    # Overlay box
    bp = ax.boxplot(data, positions=range(1, len(conditions)+1),
                    widths=0.12, patch_artist=True,
                    whiskerprops=dict(color="#333"), capprops=dict(color="#333"),
                    medianprops=dict(color="#FF4444", linewidth=2),
                    boxprops=dict(facecolor="white", alpha=0.7))

    ax.set_xticks(range(1, len(conditions)+1))
    ax.set_xticklabels(conditions, rotation=15, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} by Condition")

    # Annotate n
    for i, (cond, d) in enumerate(zip(conditions, data)):
        ax.text(i+1, ax.get_ylim()[0], f"n={len(d)}",
                ha="center", va="bottom", fontsize=8, color="#555")

    fig.tight_layout()
    out = folder / fname
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _dual_metric_figure(df, col1, col2, label1, label2, title,
                          conditions, colors, folder, fname):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)
    for ax, col, lbl in zip(axes, [col1, col2], [label1, label2]):
        if col not in df.columns:
            continue
        data = [df[df["Condition"]==c][col].dropna().values for c in conditions]
        clr  = [colors[c] for c in conditions]
        bp   = ax.boxplot(data, patch_artist=True,
                          medianprops=dict(color="#FF4444", linewidth=2))
        for patch, c in zip(bp["boxes"], clr):
            patch.set_facecolor(c)
            patch.set_alpha(0.7)
        ax.set_xticks(range(1, len(conditions)+1))
        ax.set_xticklabels(conditions, rotation=15, ha="right")
        ax.set_ylabel(lbl)
        ax.set_title(lbl.split("(")[0].strip())
    fig.suptitle(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    out = folder / fname
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _pairwise_pvalues(df, col, conditions) -> tuple[np.ndarray, list[str]]:
    n = len(conditions)
    matrix = np.ones((n, n))
    if col not in df.columns:
        return matrix, conditions
    for i, c1 in enumerate(conditions):
        for j, c2 in enumerate(conditions):
            if i >= j:
                continue
            g1 = df[df["Condition"]==c1][col].dropna()
            g2 = df[df["Condition"]==c2][col].dropna()
            if len(g1) >= 3 and len(g2) >= 3:
                _, p = stats.mannwhitneyu(g1, g2, alternative="two-sided")
                matrix[i, j] = matrix[j, i] = p
    return matrix, conditions


def _heatmap_figure(matrix, cond_list, folder, fname):
    n = len(cond_list)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(matrix, vmin=0, vmax=0.1, cmap="RdYlGn_r", aspect="auto")
    ax.set_xticks(range(n));  ax.set_xticklabels(cond_list, rotation=30, ha="right")
    ax.set_yticks(range(n));  ax.set_yticklabels(cond_list)
    for i in range(n):
        for j in range(n):
            v = matrix[i, j]
            text = "—" if i == j else (f"{v:.3f}" if v < 0.001 else f"{v:.3f}")
            ax.text(j, i, text, ha="center", va="center", fontsize=8,
                    color="white" if v < 0.05 else "black")
    ax.set_title("Pairwise Condition Comparison\n(Mann-Whitney U p-values, Walking Speed)",
                 fontsize=10)
    fig.colorbar(im, ax=ax, label="p-value")
    fig.tight_layout()
    out = folder / fname
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _summary_dashboard(df, conditions, colors, folder, fname):
    metrics = [
        ("WalkingSpeed_m_s",   "Walking Speed (m/s)"),
        ("StepLength_m",       "Step Length (m)"),
        ("WalkingBalance_pct", "Walking Balance (%)"),
        ("StepTime_s",         "Step Time (s)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.flatten()
    clrs = [colors.get(c, "#888") for c in conditions]

    for ax, (col, label) in zip(axes, metrics):
        if col not in df.columns:
            ax.set_visible(False)
            continue
        means  = [df[df["Condition"]==c][col].mean()   for c in conditions]
        sems   = [df[df["Condition"]==c][col].sem()    for c in conditions]
        x      = range(len(conditions))
        bars   = ax.bar(x, means, yerr=sems, color=clrs, alpha=0.8,
                        capsize=5, error_kw={"ecolor": "#333", "lw": 1.5})
        ax.set_xticks(list(x))
        ax.set_xticklabels(conditions, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel(label)
        ax.set_title(label.split("(")[0].strip())
        for bar, m in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                    f"{m:.3g}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("Summary Dashboard — Mean ± SEM by Condition",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    out = folder / fname
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _compute_stats_table(df, conditions) -> dict:
    table = {}
    for col, (name, unit) in GAIT_METRICS.items():
        if col not in df.columns:
            continue
        row = {"name": name, "unit": unit, "conditions": {}}
        for cond in conditions:
            g = df[df["Condition"]==cond][col].dropna()
            row["conditions"][cond] = {
                "n":    len(g),
                "mean": g.mean(),
                "sd":   g.std(),
                "med":  g.median(),
            }
        table[col] = row
    return table


def _build_condition_report(df, conditions, stats_table) -> str:
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Fresh Gait Analysis Report",
        f"\nGenerated: {date}",
        f"\nDataset: {len(df)} trials, {df['Participant_ID'].nunique() if 'Participant_ID' in df.columns else '?'} participants",
        f"Conditions: {', '.join(conditions)}",
        "\n---\n",
        "## Methods",
        "\nGait parameters were extracted using the SincMotion MATLAB library "
        "(estimateGnBGaitOutcomes). Each recording was divided into 4 equal segments "
        "for compatibility with the 4-lap walk algorithm. "
        "Condition comparisons use Mann-Whitney U tests (non-parametric, two-sided). "
        "Effect size reported as Cohen's d (pooled SD). "
        "Data shown as mean ± SD unless stated otherwise.",
        "\n---\n",
        "## Descriptive Statistics",
    ]

    for col, info in stats_table.items():
        lines.append(f"\n### {info['name']} ({info['unit']})")
        lines.append("| Condition | N | Mean | SD | Median |")
        lines.append("|---|---|---|---|---|")
        for cond, s in info["conditions"].items():
            lines.append(
                f"| {cond} | {s['n']} | {s['mean']:.3f} | {s['sd']:.3f} | {s['med']:.3f} |"
            )

    lines += ["\n---\n", "## Statistical Comparisons (Walking Speed)"]
    if "WalkingSpeed_m_s" in df.columns and len(conditions) >= 2:
        lines.append("\n| Condition A | Condition B | p-value | Significant |")
        lines.append("|---|---|---|---|")
        for i, c1 in enumerate(conditions):
            for c2 in conditions[i+1:]:
                g1 = df[df["Condition"]==c1]["WalkingSpeed_m_s"].dropna()
                g2 = df[df["Condition"]==c2]["WalkingSpeed_m_s"].dropna()
                if len(g1) >= 3 and len(g2) >= 3:
                    _, p = stats.mannwhitneyu(g1, g2, alternative="two-sided")
                    sig = "Yes *" if p < 0.05 else "No"
                    lines.append(f"| {c1} | {c2} | {p:.4f} | {sig} |")

    lines += [
        "\n---\n",
        "## Figures",
        "\n- **fig1_speed_by_condition.png** — Walking Speed violin + box by condition",
        "- **fig2_step_length_by_condition.png** — Step Length violin + box by condition",
        "- **fig3_balance_by_condition.png** — Walking Balance violin + box by condition",
        "- **fig4_step_time_by_condition.png** — Step Time violin + box by condition",
        "- **fig5_variability_by_condition.png** — Step Variability comparison",
        "- **fig6_asymmetry_by_condition.png** — Step Asymmetry comparison",
        "- **fig7_stats_heatmap.png** — Pairwise p-value heatmap (Walking Speed)",
        "- **fig8_summary_dashboard.png** — Summary dashboard (Mean ± SEM, 4 key metrics)",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  DEFAULT PIPELINE DESCRIPTIVE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def analyse_default(df: pd.DataFrame, folder: Path) -> tuple[list[str], str]:
    if df.empty:
        return [], "# Analysis Report\n\nNo data found."

    saved = []
    gait_cols   = [c for c in df.columns if c not in
                   ("Participant","Date","Test set","Test",
                    "Stability","Stability ML","Stability AP")]
    static_cols = ["Stability","Stability ML","Stability AP"]

    # Fig 1: Walking metrics box plot (per participant)
    walk_df = df[df["Test"].str.startswith("Walk", na=False)] if "Test" in df.columns else df
    if not walk_df.empty and "Walking speed" in walk_df.columns:
        saved.append(_default_metric_figure(
            walk_df, "Walking speed", "Walking Speed (m/s)",
            folder, "fig1_walking_speed.png"))

    if not walk_df.empty and "Step length" in walk_df.columns:
        saved.append(_default_metric_figure(
            walk_df, "Step length", "Step Length (m)",
            folder, "fig2_step_length.png"))

    # Fig 3: Static stability per participant
    static_df = df[~df["Test"].str.startswith("Walk", na=False)] if "Test" in df.columns else pd.DataFrame()
    if not static_df.empty and "Stability" in static_df.columns:
        saved.append(_default_metric_figure(
            static_df, "Stability", "Stability (−ln m/s²)",
            folder, "fig3_stability.png"))

    # Fig 4: Session trend (all tests over test-set number)
    if "Test set" in df.columns and "Walking speed" in df.columns:
        saved.append(_session_trend_figure(df, folder, "fig4_session_trend.png"))

    # Fig 5: Summary bar chart
    saved.append(_default_summary(df, folder, "fig5_summary.png"))

    report = _build_default_report(df)
    return [str(s) for s in saved if s is not None], report


def _default_metric_figure(df, col, ylabel, folder, fname):
    if col not in df.columns:
        return None
    participants = df["Participant"].unique() if "Participant" in df.columns else ["All"]
    data = [df[df["Participant"]==p][col].dropna().values for p in participants]
    clrs = [DEFAULT_COLORS[i % len(DEFAULT_COLORS)] for i in range(len(participants))]

    fig, ax = plt.subplots(figsize=(max(8, len(participants)*0.6 + 4), 5))
    bp = ax.boxplot(data, patch_artist=True,
                    medianprops=dict(color="#FF4444", linewidth=2))
    for patch, c in zip(bp["boxes"], clrs):
        patch.set_facecolor(c); patch.set_alpha(0.7)
    ax.set_xticks(range(1, len(participants)+1))
    ax.set_xticklabels(participants, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel.split('(')[0].strip()} by Participant")
    fig.tight_layout()
    out = folder / fname
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _session_trend_figure(df, folder, fname):
    fig, ax = plt.subplots(figsize=(9, 5))
    participants = df["Participant"].unique() if "Participant" in df.columns else []
    for i, p in enumerate(participants):
        sub = df[df["Participant"]==p].sort_values("Test set")
        walk = sub[sub["Test"].str.startswith("Walk", na=False)]
        if walk.empty or "Walking speed" not in walk.columns:
            continue
        grp = walk.groupby("Test set")["Walking speed"].mean()
        ax.plot(grp.index, grp.values, marker="o", linewidth=1.5,
                color=DEFAULT_COLORS[i % len(DEFAULT_COLORS)], alpha=0.7, label=p)
    ax.set_xlabel("Test Set")
    ax.set_ylabel("Mean Walking Speed (m/s)")
    ax.set_title("Walking Speed Trend by Session")
    if len(participants) <= 12:
        ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    out = folder / fname
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _default_summary(df, folder, fname):
    fig, ax = plt.subplots(figsize=(8, 5))
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cols_to_show = [c for c in ("Walking speed","Step length","Walking balance",
                                 "Stability") if c in numeric_cols][:6]
    if not cols_to_show:
        plt.close(fig)
        return None
    means = [df[c].mean() for c in cols_to_show]
    sems  = [df[c].sem()  for c in cols_to_show]
    ax.barh(cols_to_show, means, xerr=sems, color=DEFAULT_COLORS[:len(cols_to_show)],
            alpha=0.8, capsize=4)
    ax.set_xlabel("Mean value")
    ax.set_title("Overall Summary (Mean ± SEM)")
    fig.tight_layout()
    out = folder / fname
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _build_default_report(df) -> str:
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    n_participants = df["Participant"].nunique() if "Participant" in df.columns else "?"
    n_rows = len(df)
    numeric_summary = df.describe().round(3).to_string()
    return (
        f"# Fresh Analysis Report — Default Pipeline Output\n\n"
        f"Generated: {date}\n\n"
        f"Participants: {n_participants}   Total rows: {n_rows}\n\n"
        "---\n\n"
        "## Descriptive Statistics\n\n"
        f"```\n{numeric_summary}\n```\n\n"
        "---\n\n"
        "## Figures\n\n"
        "- **fig1_walking_speed.png** — Walking speed distribution by participant\n"
        "- **fig2_step_length.png** — Step length distribution by participant\n"
        "- **fig3_stability.png** — Postural stability by participant\n"
        "- **fig4_session_trend.png** — Walking speed trajectory across sessions\n"
        "- **fig5_summary.png** — Overall mean ± SEM summary bar chart\n"
    )


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
