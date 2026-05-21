"""Scrollable log console that polls a Queue every 100 ms."""

from __future__ import annotations
from queue import Queue, Empty

import customtkinter as ctk


_TAG_COLORS = {
    "LOG":   "#D0D0D0",
    "DONE":  "#5CDB5C",
    "ERROR": "#FF6B6B",
}


class LogConsole(ctk.CTkTextbox):
    def __init__(self, master, log_queue: Queue, **kwargs):
        kwargs.setdefault("font", ctk.CTkFont(family="Consolas", size=10))
        kwargs.setdefault("wrap", "word")
        super().__init__(master, **kwargs)
        self.configure(state="disabled")
        self._queue = log_queue

        # Configure colour tags via underlying tk.Text widget
        self._text = self._textbox  # CTkTextbox exposes _textbox
        for tag, color in _TAG_COLORS.items():
            self._text.tag_configure(tag, foreground=color)

        self._poll()

    def _poll(self):
        try:
            while True:
                kind, msg = self._queue.get_nowait()
                self._append(kind, msg)
        except Empty:
            pass
        self.after(100, self._poll)

    def _append(self, kind: str, msg: str):
        self.configure(state="normal")
        prefix = {"DONE": "[DONE] ", "ERROR": "[ERROR] "}.get(kind, "")
        full = prefix + msg + "\n"
        self._text.insert("end", full, kind)
        self._text.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
