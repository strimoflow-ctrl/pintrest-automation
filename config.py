import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

def get_int_env(key: str, default: int = 0) -> int:
    val = os.getenv(key, "").strip()
    return int(val) if val.isdigit() else default

# ================= FIREBASE RTDB CONFIG =================
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "https://secret-gpt-default-rtdb.asia-southeast1.firebasedatabase.app").strip()

# ================= TELEGRAM CONFIG =================
TELEGRAM_API_ID = get_int_env("TELEGRAM_API_ID", 0)
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TELEGRAM_OWNER_ID = get_int_env("OWNER_ID", 0)
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "Nox_oo1").strip()
TELEGRAM_SESSION_NAME = str(BASE_DIR / "telegram_session")

# ================= PINTEREST CONFIG =================
PINTEREST_SESSION = os.getenv("PINTEREST_SESSION", "").strip()
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "").strip()
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID", "").strip()
PINTEREST_USERNAME = os.getenv("PINTEREST_USERNAME", "").strip()
PINTEREST_API_BASE = "https://api.pinterest.com/v5"

# ================= WEB APP & MONETAG CONFIG =================
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "").strip()
FALLBACK_LANDING_URL = os.getenv("FALLBACK_LANDING_URL", "").strip()
TIMER_SECONDS = get_int_env("TIMER_SECONDS", 9)
POST_INTERVAL_MINUTES = get_int_env("POST_INTERVAL_MINUTES", 35)

# Monetag Direct Link (triggers on Download button click)
MONETAG_DIRECT_LINK = os.getenv("MONETAG_DIRECT_LINK", "").strip()

# Monetag In-Page / Vignette / Ad Tag script code or IDs
MONETAG_SCRIPT_TAG = os.getenv("MONETAG_SCRIPT_TAG", "").strip()

# ================= STORAGE & PATHS =================
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "pins_database.db"
