"""Data Preview tab: scrollable Treeview table + summary stats."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
import pandas as pd

from core.result_loader import compute_summary


class DataPreviewTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Summary label
        self._summary_var = tk.StringVar(value="No data loaded yet. Run the pipeline first.")
        ctk.CTkLabel(self, textvariable=self._summary_var,
                     anchor="w", justify="left",
                     font=ctk.CTkFont(family="Consolas", size=10),
                     wraplength=900).pack(fill="x", padx=10, pady=(8, 4))

        # Inner tabview for multiple output types (Walking / Static)
        self._inner = ctk.CTkTabview(self)
        self._inner.pack(fill="both", expand=True, padx=6, pady=4)
        self._tabs: dict[str, _TableFrame] = {}

    def load(self, dataframes: dict[str, pd.DataFrame]) -> None:
        """Populate tabs from a dict of label → DataFrame."""
        # Remove old tabs
        for name in list(self._tabs):
            self._inner.delete(name)
        self._tabs.clear()

        if not dataframes:
            self._summary_var.set("Pipeline produced no recognisable output files.")
            return

        summary_parts = []
        for label, df in dataframes.items():
            self._inner.add(label)
            frame = _TableFrame(self._inner.tab(label), df)
            frame.pack(fill="both", expand=True)
            self._tabs[label] = frame
            summary_parts.append(f"[{label}]  " + compute_summary(df))

        self._summary_var.set("\n\n".join(summary_parts))


class _TableFrame(ctk.CTkFrame):
    """A Treeview table with horizontal + vertical scrollbars."""

    def __init__(self, master, df: pd.DataFrame, **kwargs):
        super().__init__(master, **kwargs)

        cols = list(df.columns)
        self._tree = ttk.Treeview(self, columns=cols, show="headings",
                                   selectmode="browse")
        vsb = ttk.Scrollbar(self, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Style columns
        for col in cols:
            w = max(90, min(200, len(str(col)) * 9))
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor="center", minwidth=60)

        # Populate rows (limit to 2000 for performance)
        for _, row in df.head(2000).iterrows():
            values = []
            for v in row:
                if isinstance(v, float):
                    values.append(f"{v:.4g}")
                else:
                    values.append(str(v))
            self._tree.insert("", "end", values=values)

        # Style alternating rows
        self._tree.tag_configure("odd",  background="#1e2a35")
        self._tree.tag_configure("even", background="#162030")
        for i, item in enumerate(self._tree.get_children()):
            self._tree.item(item, tags=("even" if i % 2 == 0 else "odd",))
