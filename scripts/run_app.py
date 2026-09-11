"""
Desktop Application Launcher Script for Snapdragon Document Assistant.
Usage:
    python scripts/run_app.py
"""

import os
import sys

# Force 100% offline mode before any submodules or ML frameworks load
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ui.app import run_app

if __name__ == "__main__":
    sys.exit(run_app())
