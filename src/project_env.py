"""Load .env from the repo root regardless of process cwd."""

from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_project_dotenv():
    load_dotenv(PROJECT_ROOT / '.env')
