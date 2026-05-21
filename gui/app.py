"""Main application window."""

from __future__ import annotations
from pathlib import Path
from queue import Queue

import customtkinter as ctk

from .left_panel import LeftPanel
from .right_panel import RightPanel
from core.pipeline_runner import PipelineRunner
from core.result_loader import load_outputs


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class GnBApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GnB Gait & Balance Analysis")
        self.geometry("1400x860")
        self.minsize(1100, 700)

        self._log_queue: Queue = Queue()
        self._runner: PipelineRunner | None = None

        # Layout: left panel fixed width, right panel expands
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._left = LeftPanel(
            self, log_queue=self._log_queue,
            on_run=self._on_run_pipeline,
            on_cancel=self._on_cancel,
        )
        self._left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)

        self._right = RightPanel(self, log_queue=self._log_queue)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)

    # ── Pipeline control ──────────────────────────────────────────────────────

    def _on_run_pipeline(self):
        config = self._left.get_config()
        if config is None:
            return  # validation errors already logged

        # Ensure output folder exists
        Path(config["output_folder"]).mkdir(parents=True, exist_ok=True)

        self._left.set_running(True)
        self._log_queue.put(("LOG", "=" * 60))
        self._log_queue.put(("LOG", f"Starting pipeline — mode: {config['mode']}"))

        # Tell analysis tab which folder to watch
        self._right.analysis.set_output_folder(config["output_folder"])

        self._runner = PipelineRunner(config, self._log_queue)
        self._runner.run(
            on_complete=self._on_pipeline_complete,
            on_error=self._on_pipeline_error,
        )

    def _on_cancel(self):
        if self._runner:
            self._runner.terminate()
            self._log_queue.put(("LOG", "Pipeline cancelled by user."))
        self._left.set_running(False)

    def _on_pipeline_complete(self):
        self.after(0, self._pipeline_done)

    def _on_pipeline_error(self, msg: str):
        self.after(0, lambda: self._pipeline_failed(msg))

    def _pipeline_done(self):
        self._left.set_running(False)
        config = self._runner.config if self._runner else {}
        output_folder = config.get("output_folder", "")
        if output_folder:
            try:
                dfs = load_outputs(output_folder)
                self._right.preview.load(dfs)
                self._log_queue.put(("DONE", f"Results loaded from {output_folder}"))
            except Exception as exc:
                self._log_queue.put(("ERROR", f"Could not load results: {exc}"))

    def _pipeline_failed(self, msg: str):
        self._left.set_running(False)
        self._log_queue.put(("ERROR", f"Pipeline failed: {msg}"))
