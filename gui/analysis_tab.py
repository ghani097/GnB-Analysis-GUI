"""
Analysis tab: runs fresh_analysis.py on pipeline output, then
displays generated figures (2-column scrollable grid) and the
markdown report.
"""

from __future__ import annotations
import re
import sys
import subprocess
import threading
from pathlib import Path
from queue import Queue

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from PIL import Image


_ANALYSIS_SCRIPT = Path(__file__).resolve().parent.parent / "analysis" / "fresh_analysis.py"


class AnalysisTab(ctk.CTkFrame):
    def __init__(self, master, log_queue: Queue, **kwargs):
        super().__init__(master, **kwargs)
        self._log_queue = log_queue
        self._output_folder: str = ""
        self._img_refs: list = []   # prevent GC of CTkImage objects

        # Top control bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))
        self._run_btn = ctk.CTkButton(
            top, text="Run Primary Analysis",
            command=self._on_run,
            fg_color="#4CA376", hover_color="#3A8A60",
            width=180, height=36,
        )
        self._run_btn.pack(side="left", padx=4)
        self._status_lbl = ctk.CTkLabel(top, text="", anchor="w")
        self._status_lbl.pack(side="left", padx=8)

        # Mini log for analysis output
        self._mini_log = ctk.CTkTextbox(
            self, height=70,
            font=ctk.CTkFont(family="Consolas", size=9),
            wrap="word",
        )
        self._mini_log.configure(state="disabled")
        self._mini_log.pack(fill="x", padx=8, pady=(0, 4))

        # Inner tabs: Figures | Report
        self._inner = ctk.CTkTabview(self)
        self._inner.pack(fill="both", expand=True, padx=4, pady=4)
        self._inner.add("Figures")
        self._inner.add("Report")

        self._build_figures_panel(self._inner.tab("Figures"))
        self._build_report_panel(self._inner.tab("Report"))

    def set_output_folder(self, folder: str):
        self._output_folder = folder

    # ── Figures panel ─────────────────────────────────────────────────────────

    def _build_figures_panel(self, parent):
        self._canvas = tk.Canvas(parent, bg="#1a1a2e", highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._fig_frame = ctk.CTkFrame(self._canvas, fg_color="#1a1a2e")
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._fig_frame, anchor="nw"
        )
        self._fig_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _build_report_panel(self, parent):
        self._report_box = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family="Georgia", size=11),
            wrap="word",
        )
        self._report_box.pack(fill="both", expand=True, padx=4, pady=4)
        self._report_box.configure(state="disabled")

    # ── Run ───────────────────────────────────────────────────────────────────

    def _on_run(self):
        if not self._output_folder:
            self._status("No output folder — run the pipeline first.", error=True)
            return
        self._run_btn.configure(state="disabled")
        self._status("Running analysis…")
        self._mini_log_clear()
        self._img_refs.clear()

        def _worker():
            try:
                proc = subprocess.Popen(
                    [sys.executable, str(_ANALYSIS_SCRIPT), self._output_folder],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                for line in iter(proc.stdout.readline, ""):
                    self._mini_log_append(line.rstrip())
                proc.stdout.close()
                rc = proc.wait()
                if rc == 0:
                    self.after(0, self._load_results)
                else:
                    self.after(0, lambda: self._status(
                        f"Analysis failed (exit {rc}). Check log.", error=True))
            except Exception as exc:
                self.after(0, lambda: self._status(str(exc), error=True))
            finally:
                self.after(0, lambda: self._run_btn.configure(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _load_results(self):
        folder = Path(self._output_folder)
        self._load_figures(folder)
        self._load_report(folder)
        self._status("Analysis complete.")

    # ── Figures ───────────────────────────────────────────────────────────────

    def _load_figures(self, folder: Path):
        for w in self._fig_frame.winfo_children():
            w.destroy()

        pngs = sorted(folder.glob("fig*.png"))
        if not pngs:
            ctk.CTkLabel(self._fig_frame, text="No figures found.").grid(
                row=0, column=0, padx=20, pady=20)
            return

        for idx, png in enumerate(pngs):
            try:
                pil = Image.open(png)
                pil.thumbnail((480, 360), Image.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
                self._img_refs.append(ctk_img)

                row, col = divmod(idx, 2)
                card = ctk.CTkFrame(self._fig_frame)
                card.grid(row=row, column=col, padx=8, pady=8, sticky="n")

                ctk.CTkLabel(card, image=ctk_img, text="").pack(padx=4, pady=(4, 0))
                cap = png.stem.replace("_", " ").title()
                ctk.CTkLabel(card, text=cap,
                             font=ctk.CTkFont(size=9),
                             wraplength=460).pack(padx=4, pady=(0, 4))
            except Exception:
                pass

    # ── Report ────────────────────────────────────────────────────────────────

    def _load_report(self, folder: Path):
        md_path = folder / "fresh_analysis_report.md"
        if not md_path.exists():
            return
        raw = md_path.read_text(encoding="utf-8")
        # Strip markdown syntax for plain-text display
        text = re.sub(r"^#{1,6}\s+", "", raw, flags=re.MULTILINE)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*",   r"\1", text)
        text = re.sub(r"`(.+?)`",     r"\1", text)
        self._report_box.configure(state="normal")
        self._report_box.delete("1.0", "end")
        self._report_box.insert("end", text)
        self._report_box.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _status(self, msg: str, error: bool = False):
        color = "#FF6B6B" if error else "#AAAAAA"
        self._status_lbl.configure(text=msg, text_color=color)

    def _mini_log_clear(self):
        self._mini_log.configure(state="normal")
        self._mini_log.delete("1.0", "end")
        self._mini_log.configure(state="disabled")

    def _mini_log_append(self, text: str):
        self._mini_log.configure(state="normal")
        self._mini_log.insert("end", text + "\n")
        self._mini_log.see("end")
        self._mini_log.configure(state="disabled")
