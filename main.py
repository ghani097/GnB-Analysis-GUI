"""Entry point — launch the GnB Analysis GUI."""

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `gui` and `core` are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gui.app import GnBApp


def main():
    app = GnBApp()
    app.mainloop()


if __name__ == "__main__":
    main()
