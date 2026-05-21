"""Allow `python -m py2exe_gui` to launch the application."""

import sys

from py2exe_gui.app import main

if __name__ == "__main__":
    sys.exit(main())
