from pathlib import Path

# Base directory for the Friday project
BASE_DIR = Path(__file__).parent.parent

# Configuration file for the LM Studio API endpoint
CONFIG_FILE = BASE_DIR / "api_endpoint.txt"

# Directory containing reference images
IMAGE_DIR = BASE_DIR / "refs"

# Index file for image captions
INDEX_FILE = BASE_DIR / "captions_multi_lens.json"

# API Settings
DEFAULT_ENDPOINT = "http://10.146.227.7:1234/v1/chat/completions"
API_KEY = "lm-studio"
MODEL_NAME = "bartowski/qwen2-vl-2b-instruct"

# Indexer Settings
MAX_IMAGE_DIM = 1024

# GUI/Display Settings
XP_X = 0
XP_Y = 0
WINDOW_TITLE_BASE = "friday-ref"
