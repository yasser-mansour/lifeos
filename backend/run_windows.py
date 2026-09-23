"""PyInstaller entry point for the Windows desktop build ONLY — lives here
in backend/, next to run_server.py, purely so PyInstaller's own Django hook
can find lifeos/ as a sibling directory and auto-discover INSTALLED_APPS,
migrations, templatetags and context processors, exactly the way it already
does for the proven macOS build (see packaging/macos/lifeos-backend.spec —
PyInstaller.utils.hooks.django.django_find_root_dir() locates the Django
project relative to whichever script is the Analysis entry point). The
Windows wrapper's real logic lives in desktop/windows/lifeos_windows.py;
this file exists only to satisfy that detection and calls straight through.
Never used by macOS, by a dev checkout, or by `manage.py`/`run_server.py`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "desktop", "windows"))

from lifeos_windows import main  # noqa: E402

if __name__ == "__main__":
    main()
