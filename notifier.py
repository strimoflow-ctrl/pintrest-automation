import sys
from pathlib import Path
from typing import Optional
import requests
import config

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def send_telegram_alert(message: str, photo_path: Optional[Path] = None) -> bool:
    """Sends HTML notification or photo with caption to the Telegram bot owner."""
    if not config.BOT_TOKEN or not config.OWNER_ID:
        print("[!] Telegram Bot Token or Owner ID missing. Alert skipped.")
        return False

    try:
        if photo_path and Path(photo_path).exists():
            url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto"
            with open(photo_path, "rb") as f:
                data = {
                    "chat_id": config.OWNER_ID,
                    "caption": message[:1024],
                    "parse_mode": "HTML"
                }
                resp = requests.post(url, data=data, files={"photo": f}, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": config.OWNER_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            resp = requests.post(url, json=payload, timeout=10)

        if resp.status_code == 200:
            print(f"[✓] Telegram notification sent to Owner ({config.OWNER_ID})")
            return True
        else:
            print(f"[-] Telegram Bot API Error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[-] Failed to send Telegram notification: {e}")
        return False
