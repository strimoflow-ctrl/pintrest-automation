import time
import requests
from config import FIREBASE_DB_URL

BASE_URL = FIREBASE_DB_URL.rstrip('/') if FIREBASE_DB_URL else "https://secret-gpt-default-rtdb.asia-southeast1.firebasedatabase.app"
TIMEOUT = 8

def get_posted_ids() -> set:
    """Returns a set of all telegram_msg_ids that have already been posted to Pinterest."""
    try:
        url = f"{BASE_URL}/pinterest_automation/posted_pins.json?shallow=true"
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200 and resp.json():
            # Keys in shallow GET are the msg_ids as strings
            return set(resp.json().keys())
    except Exception as e:
        print(f"[-] Firebase get_posted_ids error: {e}")
    return set()

def is_pin_posted(telegram_msg_id: int) -> bool:
    """Checks if a specific Telegram message photo has already been posted to Pinterest."""
    try:
        url = f"{BASE_URL}/pinterest_automation/posted_pins/{telegram_msg_id}.json"
        resp = requests.get(url, timeout=TIMEOUT)
        return resp.status_code == 200 and resp.json() is not None
    except Exception as e:
        print(f"[-] Firebase check error for #{telegram_msg_id}: {e}")
        return False

def record_posted_pin(telegram_msg_id: int, pin_id: str, title: str, link: str):
    """Permanently records that this pin was posted, preventing duplicate posts across restarts."""
    try:
        url = f"{BASE_URL}/pinterest_automation/posted_pins/{telegram_msg_id}.json"
        data = {
            "pin_id": str(pin_id),
            "title": title,
            "link": link,
            "posted_at": int(time.time())
        }
        requests.put(url, json=data, timeout=TIMEOUT)
        
        # Increment total posted count in Firebase
        stats_url = f"{BASE_URL}/pinterest_automation/stats.json"
        cur_stats = get_firebase_stats()
        cur_stats["total_posted"] = cur_stats.get("total_posted", 0) + 1
        requests.patch(stats_url, json={"total_posted": cur_stats["total_posted"]}, timeout=TIMEOUT)
    except Exception as e:
        print(f"[-] Firebase record_posted_pin error: {e}")

def get_firebase_stats() -> dict:
    """Returns persistent stats from Firebase."""
    try:
        url = f"{BASE_URL}/pinterest_automation/stats.json"
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200 and isinstance(resp.json(), dict):
            return resp.json()
    except Exception:
        pass
    return {"total_posted": 0, "total_views": 0, "total_downloads": 0}

def increment_firebase_views():
    try:
        cur = get_firebase_stats()
        new_views = cur.get("total_views", 0) + 1
        url = f"{BASE_URL}/pinterest_automation/stats.json"
        requests.patch(url, json={"total_views": new_views}, timeout=4)
    except Exception:
        pass

def increment_firebase_downloads():
    try:
        cur = get_firebase_stats()
        new_dl = cur.get("total_downloads", 0) + 1
        url = f"{BASE_URL}/pinterest_automation/stats.json"
        requests.patch(url, json={"total_downloads": new_dl}, timeout=4)
    except Exception:
        pass

def get_last_scraped_id() -> int:
    try:
        url = f"{BASE_URL}/pinterest_automation/last_scraped_id.json"
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200 and resp.json() is not None:
            return int(resp.json())
    except Exception:
        pass
    return 0

def set_last_scraped_id(msg_id: int):
    try:
        url = f"{BASE_URL}/pinterest_automation/last_scraped_id.json"
        requests.put(url, json=int(msg_id), timeout=TIMEOUT)
    except Exception:
        pass
