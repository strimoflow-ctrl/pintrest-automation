import os
import sys
import time
import json
import requests
from pathlib import Path

# Force UTF-8 for console output on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import (
    PINTEREST_SESSION, PINTEREST_BOARD_ID, PINTEREST_USERNAME,
    SITE_BASE_URL, FALLBACK_LANDING_URL, MEDIA_DIR, POST_INTERVAL_MINUTES
)
import database
from notifier import send_telegram_notification

DEFAULT_BOARD_ID = PINTEREST_BOARD_ID

class PinterestSessionPoster:
    def __init__(self, session_cookie: str):
        self.session_cookie = session_cookie
        self.http = requests.Session()
        self.http.cookies.set('_pinterest_sess', session_cookie, domain='.pinterest.com')
        self.app_version = '4fc27a6'
        self.csrf_token = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.pinterest.com/pin-builder/',
            'X-Pinterest-AppState': 'active',
            'X-Pinterest-PWS-Handler': 'www/pin-builder/index.js',
            'X-APP-VERSION': self.app_version
        }

    def refresh_csrf(self):
        try:
            resp = self.http.get('https://www.pinterest.com/pin-builder/', headers=self.headers, timeout=15)
            self.csrf_token = self.http.cookies.get('csrftoken', '')
            self.headers['X-CSRFToken'] = self.csrf_token
            return bool(self.csrf_token)
        except Exception as e:
            print(f"[-] Failed to get CSRF token: {e}")
            return False

    def get_user_boards(self, username=None):
        if not username:
            username = PINTEREST_USERNAME
        if not self.csrf_token:
            self.refresh_csrf()
        data = {'options': {'username': username, 'field_set_key': 'detailed'}, 'context': {}}
        try:
            resp = self.http.get(
                'https://www.pinterest.com/resource/BoardsResource/get/',
                headers=self.headers,
                params={'source_url': f'/{username}/', 'data': json.dumps(data)},
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get('resource_response', {}).get('data', [])
        except Exception as e:
            print(f"[-] Error fetching boards: {e}")
        return []

    def create_pin(self, board_id: str, title: str, description: str, link: str, image_url: str):
        if not self.csrf_token:
            self.refresh_csrf()

        data = {
            "options": {
                "board_id": str(board_id),
                "field_set_key": "create_success",
                "title": title[:100],
                "description": description[:500],
                "link": link,
                "image_url": image_url
            },
            "context": {}
        }
        
        post_payload = {
            "source_url": "/pin-builder/",
            "data": json.dumps(data)
        }

        url = 'https://www.pinterest.com/resource/PinResource/create/'
        resp = self.http.post(url, headers=self.headers, data=post_payload, timeout=20)
        
        if resp.status_code == 200:
            res_data = resp.json()
            pin_data = res_data.get('resource_response', {}).get('data', {})
            pin_id = pin_data.get('id')
            if pin_id:
                return {"success": True, "pin_id": pin_id, "url": f"https://www.pinterest.com/pin/{pin_id}/"}
                
        return {"success": False, "error": f"Status {resp.status_code}: {resp.text[:200]}"}

def post_single_item(item: dict, board_id: str = DEFAULT_BOARD_ID) -> bool:
    item_id = item["id"]
    
    # Destination link for the Pin
    # Pinterest requires a valid public web link (not localhost)
    base = SITE_BASE_URL.rstrip('/') if SITE_BASE_URL else ""
    if not base or "localhost" in base or not base.startswith("http"):
        base = "https://pintrest-automation.onrender.com"
        
    # Exactly target the individual pin landing page
    landing_url = f"{base}/p/{item_id}"

    # Use direct Telegram CDN for image source (saves 100% Render server bandwidth)
    if item.get("cdn_url") and item["cdn_url"].startswith("http"):
        image_url = item["cdn_url"]
    else:
        image_url = f"{base}/media/{item['file_path']}"

    poster = PinterestSessionPoster(PINTEREST_SESSION)
    result = poster.create_pin(
        board_id=board_id,
        title=item["seo_title"],
        description=item["seo_description"],
        link=landing_url,
        image_url=image_url
    )

    if result.get("success"):
        pin_id = result["pin_id"]
        pin_url = result["url"]
        database.mark_item_posted(item_id, pin_id)
        stats = database.get_stats()
        print(f"[✓] Pin #{item_id} successfully created on Pinterest! URL: {pin_url}")

        # Send Detailed Telegram Bot Notification to Owner
        notif_msg = (
            f"✅ <b>Pinterest Pin Uploaded Successfully!</b>\n\n"
            f"🏷️ <b>Title:</b> {item['seo_title']}\n"
            f"📌 <b>Pinterest Pin:</b> <a href=\"{pin_url}\">{pin_url}</a>\n"
            f"🌐 <b>Landing Page:</b> <a href=\"{landing_url}\">{landing_url}</a>\n\n"
            f"📊 <b>Live System Stats:</b>\n"
            f"• 📌 Total Posted Pins: <b>{stats['posted_pins']}</b>\n"
            f"• ⏳ Remaining in Queue: <b>{stats['pending_pins']}</b>\n"
            f"• 📦 Total Scraped Media: <b>{stats['total_media']}</b>\n"
            f"• 👁️ Landing Views: <b>{stats['total_views']}</b>\n"
            f"• ⬇️ Downloads: <b>{stats['total_downloads']}</b>\n\n"
            f"⚡ <i>Auto-posted via NOX Automation</i>"
        )
        send_telegram_notification(notif_msg)
        return True
    else:
        err = result.get("error", "Unknown error")
        print(f"[-] Failed to post Pin #{item_id}: {err}")
        database.mark_item_error(item_id, err)
        stats = database.get_stats()
        
        # Send Detailed Error Alert to Owner
        err_msg = (
            f"❌ <b>Pinterest Pin Upload Failed!</b>\n\n"
            f"🏷️ <b>Title:</b> {item['seo_title']}\n"
            f"⚠️ <b>Error Reason:</b> <code>{err}</code>\n\n"
            f"📊 <b>Queue Status:</b>\n"
            f"• 📌 Uploaded so far: <b>{stats['posted_pins']}</b>\n"
            f"• ⏳ Pending in Queue: <b>{stats['pending_pins']}</b>\n\n"
            f"⚡ <i>Worker will retry next scheduled interval.</i>"
        )
        send_telegram_notification(err_msg)
        return False

def start_posting_worker():
    database.init_db()
    print("================ PINTEREST AUTO-POSTER STARTED ================")
    print(f"Posting Interval: Every {POST_INTERVAL_MINUTES} minutes")
    print(f"Target Board ID: {DEFAULT_BOARD_ID}")
    print("===============================================================")

    # Test Telegram connection alert
    send_telegram_notification("🚀 <b>Pinterest Auto-Poster Worker Started!</b>\n\nPins will be posted automatically.")

    while True:
        item = database.get_next_unposted_item()
        if not item:
            print("[*] No unposted items found in database. Waiting 5 minutes for new scraper batch...")
            time.sleep(300)
            continue

        print(f"\n[*] Preparing to post Pin #{item['id']}: '{item['seo_title']}'")
        post_single_item(item, board_id=DEFAULT_BOARD_ID)

        # Sleep interval
        sleep_secs = POST_INTERVAL_MINUTES * 60
        print(f"[*] Sleeping for {POST_INTERVAL_MINUTES} minutes until next pin...")
        time.sleep(sleep_secs)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        database.init_db()
        item = database.get_next_unposted_item()
        if item:
            post_single_item(item)
        else:
            print("No unposted items in DB.")
    else:
        start_posting_worker()
