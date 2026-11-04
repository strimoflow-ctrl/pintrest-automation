import sys
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def send_telegram_notification(message: str) -> bool:
    """
    Sends notification message to the Telegram bot owner.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_OWNER_ID:
        print("[!] Telegram Bot Token or Owner ID missing. Notification skipped.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_OWNER_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[✓] Telegram notification sent to Owner ({TELEGRAM_OWNER_ID})")
            return True
        else:
            print(f"[-] Telegram Bot API Error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"[-] Failed to send Telegram notification: {e}")
        return False

if __name__ == "__main__":
    test_msg = "⚡ <b>NOX PFP Pinterest Automation</b>\n\nNotification system connected successfully! 🚀"
    send_telegram_notification(test_msg)
