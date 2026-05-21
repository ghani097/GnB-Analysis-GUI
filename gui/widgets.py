"""Shared reusable widgets: file/folder pickers and section headers."""

from __future__ import annotations
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

import customtkinter as ctk


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        super().__init__(
            master, text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            **kwargs,
        )


class _PathPicker(ctk.CTkFrame):
    """Base class for folder/file browse rows."""

    def __init__(self, master, label: str, dialog_fn, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._dialog_fn = dialog_fn
        self.var = tk.StringVar()

        ctk.CTkLabel(self, text=label, anchor="w", width=140).pack(side="left")
        self._entry = ctk.CTkEntry(self, textvariable=self.var, width=170)
        self._entry.pack(side="left", padx=(4, 2))
        ctk.CTkButton(self, text="Browse", width=60,
                      command=self._browse).pack(side="left")

    def _browse(self):
        result = self._dialog_fn()
        if result:
            self.var.set(result)

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, value: str):
        self.var.set(value)


class FolderPicker(_PathPicker):
    def __init__(self, master, label: str, **kwargs):
        super().__init__(
            master, label,
            lambda: filedialog.askdirectory(title=label),
            **kwargs,
        )


class FilePicker(_PathPicker):
    def __init__(self, master, label: str, filetypes=None, **kwargs):
        ft = filetypes or [("All files", "*.*")]
        super().__init__(
            master, label,
            lambda: filedialog.askopenfilename(title=label, filetypes=ft),
            **kwargs,
        )


def find_matlab_exe() -> str:
    """Search common Windows paths for matlab.exe; return first found."""
    candidates = [
        r"E:\Program Files\MATLAB\R2025b\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2025b\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2024b\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2024a\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2023b\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2023a\bin\matlab.exe",
    ]
    import os
    env_root = os.environ.get("MATLAB_ROOT")
    if env_root:
        candidates.insert(0, str(Path(env_root) / "bin" / "matlab.exe"))
    for c in candidates:
        if Path(c).exists():
            return c
    return ""
