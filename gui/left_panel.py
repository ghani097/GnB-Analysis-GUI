"""
Left configuration panel: data paths, recording mode, MATLAB config, run button, log.
"""

from __future__ import annotations
from pathlib import Path
from queue import Queue

import customtkinter as ctk

from .widgets import FolderPicker, FilePicker, SectionLabel, find_matlab_exe
from .log_console import LogConsole


class LeftPanel(ctk.CTkFrame):
    def __init__(self, master, log_queue: Queue, on_run, on_cancel, **kwargs):
        kwargs.setdefault("width", 400)
        super().__init__(master, **kwargs)
        self._log_queue = log_queue
        self._on_run = on_run
        self._on_cancel = on_cancel

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 4, "fill": "x"}

        # ── Data Configuration ───────────────────────────────────────────────
        SectionLabel(self, text="Data Configuration").pack(**pad, pady=(12, 2))

        self.raw_folder   = FolderPicker(self, "Root Data Folder")
        self.raw_folder.pack(**pad)

        self.heights_file = FilePicker(
            self, "Heights/Weights File",
            filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("All files", "*.*")],
        )
        self.heights_file.pack(**pad)

        self.output_folder = FolderPicker(self, "Output Folder")
        self.output_folder.pack(**pad)

        # ── Recording Mode ───────────────────────────────────────────────────
        SectionLabel(self, text="Recording Mode").pack(**pad, pady=(12, 2))

        self._mode_var = ctk.StringVar(value="Default")
        self._mode_seg = ctk.CTkSegmentedButton(
            self, values=["Default", "Custom"],
            variable=self._mode_var,
            command=self._on_mode_change,
        )
        self._mode_seg.pack(**pad)

        # Custom sub-frame (hidden by default)
        self._custom_frame = ctk.CTkFrame(self, fg_color="#1e2a35", corner_radius=6)
        ctk.CTkLabel(self._custom_frame, text="Task types to process:",
                     anchor="w").pack(fill="x", padx=8, pady=(6, 2))
        self._walk_var    = ctk.BooleanVar(value=True)
        self._static_var  = ctk.BooleanVar(value=False)
        self._walk_cb  = ctk.CTkCheckBox(self._custom_frame, text="Walking tasks",
                                          variable=self._walk_var,
                                          command=self._validate_custom)
        self._static_cb = ctk.CTkCheckBox(self._custom_frame,
                                           text="Standing / Static tasks",
                                           variable=self._static_var,
                                           command=self._validate_custom)
        self._walk_cb.pack(fill="x", padx=16, pady=2)
        self._static_cb.pack(fill="x", padx=16, pady=(2, 8))
        self._custom_warning = ctk.CTkLabel(
            self._custom_frame, text="", text_color="#FF6B6B", anchor="w")
        self._custom_warning.pack(fill="x", padx=8, pady=(0, 4))

        # ── MATLAB ───────────────────────────────────────────────────────────
        SectionLabel(self, text="MATLAB").pack(**pad, pady=(12, 2))

        self.matlab_exe = FilePicker(
            self, "MATLAB Executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        self.matlab_exe.pack(**pad)
        ctk.CTkButton(self, text="Auto-Detect MATLAB",
                      command=self._auto_detect_matlab,
                      height=28).pack(**pad)

        # ── Repo Root ────────────────────────────────────────────────────────
        SectionLabel(self, text="Existing Analysis Repo").pack(**pad, pady=(12, 2))
        self.repo_root = FolderPicker(self, "Repo Root")
        self.repo_root.pack(**pad)

        # Try to pre-fill repo root from known path
        known = r"E:\GIT_HUB_MAIN\Gait and Balance\Gait-and-Balance-Streamlined-Analysis"
        if Path(known).is_dir():
            self.repo_root.set(known)

        # Pre-fill MATLAB
        found = find_matlab_exe()
        if found:
            self.matlab_exe.set(found)

        # ── Run / Cancel ─────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(**pad, pady=(14, 4))
        self._run_btn = ctk.CTkButton(
            btn_frame, text="Run Pipeline ▶",
            command=self._on_run,
            fg_color="#2C5F8A", hover_color="#1E4A70",
            height=40, font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._run_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel",
            command=self._on_cancel,
            fg_color="#555", hover_color="#333",
            height=40, width=80,
        )
        self._cancel_btn.pack(side="left")

        # ── Log ──────────────────────────────────────────────────────────────
        SectionLabel(self, text="Log").pack(**pad, pady=(10, 2))
        self._log = LogConsole(self, log_queue=self._log_queue, height=220)
        self._log.pack(**pad, pady=(0, 10))

    # ── Mode transitions ──────────────────────────────────────────────────────

    def _on_mode_change(self, value: str):
        if value == "Custom":
            self._custom_frame.pack(padx=10, pady=4, fill="x",
                                    after=self._mode_seg)
        else:
            self._custom_frame.pack_forget()
        self._validate_custom()

    def _validate_custom(self):
        if self._mode_var.get() != "Custom":
            self._run_btn.configure(state="normal")
            self._custom_warning.configure(text="")
            return
        if not self._walk_var.get() and not self._static_var.get():
            self._custom_warning.configure(
                text="Select at least one task type.")
            self._run_btn.configure(state="disabled")
        else:
            self._custom_warning.configure(text="")
            self._run_btn.configure(state="normal")

    # ── MATLAB auto-detect ────────────────────────────────────────────────────

    def _auto_detect_matlab(self):
        found = find_matlab_exe()
        if found:
            self.matlab_exe.set(found)
            self._log_queue.put(("LOG", f"Auto-detected MATLAB: {found}"))
        else:
            self._log_queue.put(("ERROR",
                "MATLAB not found in standard locations. Please browse manually."))

    # ── Config extraction ─────────────────────────────────────────────────────

    def get_config(self) -> dict | None:
        """Build and validate config dict. Returns None if validation fails."""
        errors = []

        raw     = self.raw_folder.get()
        heights = self.heights_file.get()
        output  = self.output_folder.get()
        matlab  = self.matlab_exe.get()
        repo    = self.repo_root.get()

        if not raw or not Path(raw).is_dir():
            errors.append("Root Data Folder does not exist.")
        if not output:
            errors.append("Output Folder must be specified.")
        if not matlab or not Path(matlab).is_file():
            errors.append("MATLAB executable not found.")
        if not repo or not Path(repo).is_dir():
            errors.append("Repo Root does not exist.")

        mode_raw = self._mode_var.get()
        walk    = self._walk_var.get()
        static  = self._static_var.get()

        if mode_raw == "Custom" and not walk and not static:
            errors.append("Select at least one Custom task type.")

        if errors:
            for e in errors:
                self._log_queue.put(("ERROR", e))
            return None

        # Determine effective mode
        if mode_raw == "Default":
            mode = "default"
        elif walk and static:
            mode = "custom_both"
        else:
            mode = "custom_walking"   # walking only (static-only not currently supported)

        # Derive helper paths from repo root
        gui_root = Path(__file__).resolve().parent.parent
        sumeeta_analysis = (
            Path(repo) / "Sumeeta data collection files" / "analysis"
        )

        return {
            "mode":                 mode,
            "matlab_exe":           matlab,
            "raw_folder":           raw,
            "output_folder":        output,
            "heights_file":         heights,
            "repo_root":            repo,
            "gui_matlab_dir":       str(gui_root / "matlab"),
            "sumeeta_analysis_dir": str(sumeeta_analysis),
        }

    def set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self._run_btn.configure(state=state)
