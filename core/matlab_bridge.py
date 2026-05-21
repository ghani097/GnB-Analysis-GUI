"""
Builds MATLAB subprocess commands and streams stdout to a Queue.
All path arguments use forward slashes (MATLAB requires them on Windows).
"""

from __future__ import annotations
import subprocess
import threading
from pathlib import Path
from queue import Queue


def _fwd(p: str) -> str:
    """Convert a Windows path to forward-slash form for MATLAB strings."""
    return str(p).replace("\\", "/")


# ── Command builders ──────────────────────────────────────────────────────────

def build_default_command(matlab_exe: str, raw_folder: str, output_folder: str,
                           heights_file: str, repo_root: str) -> list[str]:
    """Default 6-task GnB pipeline via run_gb_pipeline.m."""
    pipeline_dir = _fwd(Path(repo_root) / "Pipeline_Streamlined")
    sincmotion   = _fwd(Path(repo_root) / "sincmotion-matlab")

    ht = f"opts.heightsFile = '{_fwd(heights_file)}'; " if heights_file else ""
    batch = (
        f"addpath('{pipeline_dir}'); "
        f"addpath(genpath('{sincmotion}')); "
        f"opts = struct(); "
        f"{ht}"
        f"opts.fillMissingHeightWithMean = true; "
        f"opts.verbose = true; "
        f"run_gb_pipeline('{_fwd(raw_folder)}', '{_fwd(output_folder)}', opts);"
    )
    return [matlab_exe, "-batch", batch]


def build_custom_walking_command(matlab_exe: str, raw_folder: str,
                                  output_folder: str, heights_file: str,
                                  repo_root: str, gui_matlab_dir: str,
                                  sumeeta_analysis_dir: str) -> list[str]:
    """Custom walking-only pipeline via gnb_custom_walker.m."""
    sincmotion = _fwd(Path(repo_root) / "sincmotion-matlab")
    batch = (
        f"addpath('{_fwd(gui_matlab_dir)}'); "
        f"addpath('{_fwd(sumeeta_analysis_dir)}'); "
        f"addpath(genpath('{sincmotion}')); "
        f"gnb_custom_walker('{_fwd(raw_folder)}', "
        f"'{_fwd(output_folder)}', '{_fwd(heights_file)}');"
    )
    return [matlab_exe, "-batch", batch]


def build_custom_both_command(matlab_exe: str, raw_folder: str,
                               output_folder: str, heights_file: str,
                               repo_root: str, gui_matlab_dir: str,
                               sumeeta_analysis_dir: str) -> list[str]:
    """Custom walking + static pipeline via gnb_gui_runner.m."""
    sincmotion = _fwd(Path(repo_root) / "sincmotion-matlab")
    batch = (
        f"addpath('{_fwd(gui_matlab_dir)}'); "
        f"addpath('{_fwd(sumeeta_analysis_dir)}'); "
        f"addpath(genpath('{sincmotion}')); "
        f"gnb_gui_runner('{_fwd(raw_folder)}', "
        f"'{_fwd(output_folder)}', '{_fwd(heights_file)}');"
    )
    return [matlab_exe, "-batch", batch]


# ── Runner ────────────────────────────────────────────────────────────────────

class MatlabBridge:
    """Launches a MATLAB -batch subprocess and streams output to a Queue."""

    def __init__(self, log_queue: Queue):
        self.log_queue = log_queue
        self._proc: subprocess.Popen | None = None

    def run(self, cmd: list[str], on_complete, on_error) -> None:
        """Start MATLAB in a background thread. Calls on_complete() or on_error(msg)."""
        def _worker():
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                for line in iter(self._proc.stdout.readline, ""):
                    self.log_queue.put(("LOG", line.rstrip()))
                self._proc.stdout.close()
                rc = self._proc.wait()
                if rc == 0:
                    self.log_queue.put(("DONE", "MATLAB finished successfully."))
                    on_complete()
                else:
                    msg = f"MATLAB exited with code {rc}."
                    self.log_queue.put(("ERROR", msg))
                    on_error(msg)
            except Exception as exc:
                self.log_queue.put(("ERROR", str(exc)))
                on_error(str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def terminate(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
