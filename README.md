# GnB Analysis GUI

Python GUI wrapper for the Gait & Balance (GnB) MATLAB analysis pipelines.  
Points to an existing data folder, runs the appropriate MATLAB pipeline, previews results, and launches a statistical analysis with figures.

---

## Setup

```bash
pip install -r requirements.txt
python main.py
```

**Requirements:** Python 3.9+, MATLAB R2022b+ (with SincMotion library compiled).

---

## Usage

### 1. Configure inputs

| Field | Description |
|---|---|
| Root Data Folder | Folder containing raw sensor CSV files |
| Heights/Weights File | XLSX or CSV with participant heights (columns: ID/Name + Height_m or Height_cm) |
| Output Folder | Where output Excel files and figures are written |
| MATLAB Executable | Path to `matlab.exe` (auto-detected from common install locations) |
| Repo Root | Path to the `Gait-and-Balance-Streamlined-Analysis` repo (for SincMotion library) |

### 2. Recording Mode

**Default** — standard 6-task GnB protocol (4 static + 2 walking tasks).  
Calls `Pipeline_Streamlined/run_gb_pipeline.m` from the existing repo.  
File naming: `{Name} Test set {N} on {DD-MM-YYYY} {Task}.csv`

**Custom** — continuous-recording protocol (e.g., Sumeeta dual-task study).  
File naming: `p{N} {bl|st|cb|pl} {trial}.csv` and variants.

- **Walking only** — calls `matlab/gnb_custom_walker.m`; produces `custom_gait_outcomes.xlsx`
- **Walking + Standing** — calls `matlab/gnb_gui_runner.m`; classifies files automatically; produces `custom_gait_outcomes.xlsx` + `custom_static_outcomes.xlsx`

### 3. Results

After the pipeline finishes:
- **Data Preview tab** — scrollable table of output gait/static parameters with condition/participant breakdown
- **Primary Analysis tab** — click **Run Primary Analysis** to generate 8 condition-comparison figures and a markdown report from the fresh pipeline output

---

## File Classification (Custom + Walking+Standing mode)

Files are classified as walking vs static using a two-tier approach:

1. **Filename keywords** — "Firm EO/EC", "Compliant EO/EC", "Walk HF/HT" etc.
2. **Row count** — files ≥ 4000 rows at 100 Hz (≥ 40 s) are treated as continuous walking; shorter files as static balance recordings

---

## Repository Structure

```
GnB-Analysis-GUI/
├── main.py              Entry point
├── gui/                 GUI modules (customtkinter)
│   ├── app.py           Main window
│   ├── left_panel.py    Configuration panel
│   ├── right_panel.py   Results tabs
│   ├── data_preview_tab.py  Treeview data table
│   ├── analysis_tab.py  Figures + report display
│   ├── log_console.py   Real-time MATLAB log
│   └── widgets.py       Reusable widgets
├── core/                Business logic (no GUI)
│   ├── matlab_bridge.py     Subprocess MATLAB runner
│   ├── file_classifier.py   Walking vs static classifier
│   ├── pipeline_runner.py   Mode orchestrator
│   └── result_loader.py     Output file loader
├── matlab/              New MATLAB wrapper scripts
│   ├── gnb_custom_walker.m  Custom walking pipeline
│   └── gnb_gui_runner.m     Custom walking+static pipeline
└── analysis/
    └── fresh_analysis.py    Condition comparison analysis + figures
```

---

## Existing Repo Dependency

This GUI calls scripts from  
`Gait-and-Balance-Streamlined-Analysis/` (separate repo, not included here).  
Point the **Repo Root** field at that repo's root directory.

---

## Notes

- The `sincmotion-matlab/` library (inside the existing repo) must have `diff_cwtft.mexw64` compiled. See `Pipeline_Streamlined/README.md` for Windows build steps.
- MATLAB `-batch` mode is used — no desktop, no interactive prompts. All output streams to the GUI log.
- Output files (Excel, PNG, reports) are not tracked by git (see `.gitignore`).
