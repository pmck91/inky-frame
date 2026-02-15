from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ORIGINALS_DIR = DATA_DIR / "images" / "originals"
PROCESSED_DIR = DATA_DIR / "images" / "processed"
STATE_FILE = DATA_DIR / "state.json"

DISPLAY_WIDTH = 600
DISPLAY_HEIGHT = 448
DEFAULT_ROTATION_SECONDS = 300
