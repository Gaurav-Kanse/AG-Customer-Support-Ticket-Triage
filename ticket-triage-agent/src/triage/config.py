"""Application configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
KB_DIR = BASE_DIR / "data" / "knowledge_base"
TRACE_DIR = BASE_DIR / "results" / "traces"
STORE_PATH = Path(os.getenv("HELPDESK_STORE", BASE_DIR / "results" / "helpdesk.json"))
