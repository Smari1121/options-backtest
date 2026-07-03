"""
Central configuration for paths and simulation parameters.

All path resolution is relative to this file's location, so the project
can be moved around without breaking anything.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "allData"
OUTPUT_DIR = BASE_DIR / "output"

UNDERLIERS = ["NIFTY", "BANKNIFTY"]
