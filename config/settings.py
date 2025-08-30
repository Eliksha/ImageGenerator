import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
GENERATED_DIR = BASE_DIR / "storage" / "generated"
TEMP_DIR = BASE_DIR / "storage" / "temp"

# Create directories if they don't exist
for directory in [UPLOAD_DIR, GENERATED_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "single_person").mkdir(exist_ok=True)
    (directory / "couples").mkdir(exist_ok=True)

# Gemini API settings
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1  # seconds

# Image settings
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
IMAGE_QUALITY = 95

# Generation settings
MAX_CONCURRENT_GENERATIONS = 3
DEFAULT_IMAGE_COUNT = 4
