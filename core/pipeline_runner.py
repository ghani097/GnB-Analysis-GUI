"""
Orchestrates which MATLAB command to run based on GUI configuration.
Sequences the appropriate matlab_bridge call.
"""

from __future__ import annotations
from pathlib import Path
from queue import Queue

from .matlab_bridge import (
    MatlabBridge,
    build_default_command,
    build_custom_walking_command,
    build_custom_both_command,
)
from .file_classifier import classify_folder


class PipelineRunner:
    """
    config dict keys:
        mode          : 'default' | 'custom_walking' | 'custom_both'
        matlab_exe    : full path to matlab.exe
        raw_folder    : root data folder (user-selected)
        output_folder : destination for output files
        heights_file  : path to heights XLSX/CSV (may be empty string)
        repo_root     : path to Gait-and-Balance-Streamlined-Analysis repo
        gui_matlab_dir: path to this GUI repo's matlab/ folder
        sumeeta_analysis_dir: path to Sumeeta data collection files/analysis/
    """

    def __init__(self, config: dict, log_queue: Queue):
        self.config = config
        self.log_queue = log_queue
        self.bridge = MatlabBridge(log_queue)

    def run(self, on_complete, on_error) -> None:
        mode = self.config["mode"]
        if mode == "default":
            self._run_default(on_complete, on_error)
        elif mode == "custom_walking":
            self._run_custom_walking(on_complete, on_error)
        elif mode == "custom_both":
            self._run_custom_both(on_complete, on_error)
        else:
            on_error(f"Unknown pipeline mode: {mode!r}")

    def terminate(self) -> None:
        self.bridge.terminate()

    # ── private ──────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        self.log_queue.put(("LOG", msg))

    def _run_default(self, on_complete, on_error) -> None:
        c = self.config
        self._log("Mode: Default (6-task GnB protocol)")
        cmd = build_default_command(
            c["matlab_exe"], c["raw_folder"], c["output_folder"],
            c["heights_file"], c["repo_root"],
        )
        self._log(f"MATLAB: {cmd[0]} -batch ...")
        self.bridge.run(cmd, on_complete, on_error)

    def _run_custom_walking(self, on_complete, on_error) -> None:
        c = self.config
        self._log("Mode: Custom — Walking only")
        cmd = build_custom_walking_command(
            c["matlab_exe"], c["raw_folder"], c["output_folder"],
            c["heights_file"], c["repo_root"],
            c["gui_matlab_dir"], c["sumeeta_analysis_dir"],
        )
        self._log(f"MATLAB: {cmd[0]} -batch ...")
        self.bridge.run(cmd, on_complete, on_error)

    def _run_custom_both(self, on_complete, on_error) -> None:
        c = self.config
        self._log("Mode: Custom — Walking + Static")

        # Preview classification before running
        folder = Path(c["raw_folder"])
        if folder.is_dir():
            classified = classify_folder(folder)
            n_w = len(classified["walking"])
            n_s = len(classified["static"])
            n_u = len(classified["unknown"])
            self._log(f"File classification: {n_w} walking, {n_s} static, {n_u} unknown")
            for f in classified["unknown"]:
                self._log(f"  [UNKNOWN] {f.name}")

        cmd = build_custom_both_command(
            c["matlab_exe"], c["raw_folder"], c["output_folder"],
            c["heights_file"], c["repo_root"],
            c["gui_matlab_dir"], c["sumeeta_analysis_dir"],
        )
        self._log(f"MATLAB: {cmd[0]} -batch ...")
        self.bridge.run(cmd, on_complete, on_error)
