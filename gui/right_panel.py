"""Right panel: tabview containing Data Preview and Primary Analysis tabs."""

from __future__ import annotations
from queue import Queue

import customtkinter as ctk

from .data_preview_tab import DataPreviewTab
from .analysis_tab import AnalysisTab


class RightPanel(ctk.CTkFrame):
    def __init__(self, master, log_queue: Queue, **kwargs):
        super().__init__(master, **kwargs)

        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=4, pady=4)
        self._tabs.add("Data Preview")
        self._tabs.add("Primary Analysis")

        self.preview = DataPreviewTab(self._tabs.tab("Data Preview"))
        self.preview.pack(fill="both", expand=True)

        self.analysis = AnalysisTab(self._tabs.tab("Primary Analysis"),
                                    log_queue=log_queue)
        self.analysis.pack(fill="both", expand=True)
