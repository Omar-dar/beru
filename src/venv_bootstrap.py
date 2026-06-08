"""Re-launch scripts with the project .venv Python when needed."""

import os
import sys


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _running_in_project_venv(root):
    venv_dir = os.path.join(root, '.venv')
    return (
        sys.prefix == os.path.realpath(venv_dir)
        or sys.prefix.startswith(venv_dir + os.sep)
    )


def ensure_project_venv():
    """
    Homebrew `python3 beru_api.py` uses the same binary as `.venv/bin/python3`
    but WITHOUT venv site-packages — pymupdf/torch won't load.

    Re-exec via `.venv/bin/python3` so the virtualenv is active.
    """
    root = _project_root()
    venv_python = os.path.join(root, '.venv', 'bin', 'python3')
    if not os.path.isfile(venv_python):
        return

    if _running_in_project_venv(root):
        return

    print(f"Using Beru venv Python: {venv_python}")
    os.execv(venv_python, [venv_python] + sys.argv)
