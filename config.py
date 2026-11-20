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
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "").strip().rstrip("/")

# ================= PINTEREST CONFIG =================
PINTEREST_SESSION = os.getenv("PINTEREST_SESSION", "").strip()
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID", "").strip()
PINTEREST_USERNAME = os.getenv("PINTEREST_USERNAME", "").strip()
POST_INTERVAL_MINUTES = get_int_env("POST_INTERVAL_MINUTES", 35)

# ================= WEB APP & MONETAG CONFIG =================
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://pintrest-automation.onrender.com").strip().rstrip("/")
MONETAG_DIRECT_LINK = os.getenv("MONETAG_DIRECT_LINK", "https://uplcm.com/4/12271752").strip()
MONETAG_SCRIPT_TAG = os.getenv("MONETAG_SCRIPT_TAG", '<script src="https://quge5.com/88/tag.min.js" data-zone="310710" async data-cfasync="false"></script>').strip()

# ================= TELEGRAM NOTIFIER CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = get_int_env("OWNER_ID", 0)

# ================= DIRECTORIES & DATABASE =================
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

NAIL_CATALOGS_DIR = BASE_DIR / "nail_catalogs"
DB_PATH = BASE_DIR / "nail_tutorials.db"
