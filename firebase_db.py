import re
import requests
from typing import Optional, Dict, Any
import config

def _sanitize_key(key: str) -> str:
    """Replaces characters forbidden in Firebase RTDB keys (. $ # [ ] /)"""
    return re.sub(r'[\.\$#\[\]/]', '_', str(key))

def is_pin_posted_in_firebase(tutorial_id: str) -> bool:
    """Checks if tutorial was already recorded as posted in Firebase RTDB."""
    if not config.FIREBASE_DB_URL:
        return False
    try:
        safe_key = _sanitize_key(tutorial_id)
        url = f"{config.FIREBASE_DB_URL}/nail_posts/{safe_key}.json"
        resp = requests.get(url, timeout=7)
        if resp.status_code == 200 and resp.json() is not None:
            return True
    except Exception as e:
        print(f"[!] Firebase check error: {e}")
    return False

def record_posted_pin_in_firebase(tutorial_id: str, pin_data: Dict[str, Any]) -> bool:
    """Records posted pin details into Firebase RTDB under /nail_posts/{tutorial_id}."""
    if not config.FIREBASE_DB_URL:
        return False
    try:
        safe_key = _sanitize_key(tutorial_id)
        url = f"{config.FIREBASE_DB_URL}/nail_posts/{safe_key}.json"
        resp = requests.put(url, json=pin_data, timeout=10)
        if resp.status_code == 200:
            print(f"[✓] Recorded in Firebase RTDB: /nail_posts/{safe_key}")
            return True
        else:
            print(f"[-] Firebase record failed with status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[!] Firebase record error: {e}")
    return False
