import os
import sys
import time
import json
import random
import hashlib
import subprocess
import requests
from pathlib import Path
from PIL import Image

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import config
import database
from notifier import send_telegram_notification

VIRAL_MEDIA_DIR = config.VIRAL_MEDIA_DIR
VIRAL_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# 4 High-Converting Target Board Names
TARGET_BOARD_NAMES = [
    "Casual & Classy Looks 💃",
    "Usa College Beauty ✨",
    "Trending Glamour & Fashion 🔥",
    "Exclusive Viral Looks 🔞"
]

# High-CTR Viral Title Variations
VIRAL_TITLES = [
    "Click Visit Site to Watch 🔞🙈",
    "Tap Visit Site to Watch Full Video 🔞👀",
    "Click Visit Site to Unlock 🔞🔥",
    "Watch What Happened Next... 🫣 Tap Visit Site 🔞",
    "Private VIP Stream 🔞 Click Visit Site 🔗",
    "Uncensored HD Stream 🔞 Click Visit Site Now 🔥"
]


class PinterestViralClient:
    """
    Manages Board Creation, Board Listing, and Pin Posting for Viral Bot 2.
    Uses VIRAL_PINTEREST_SESSION and VIRAL_PINTEREST_USERNAME.
    """
    def __init__(self, session_cookie: str, username: str):
        self.session_cookie = session_cookie
        self.username = username
        self.http = requests.Session()
        self.http.cookies.set("_pinterest_sess", session_cookie, domain=".pinterest.com")
        self.csrf_token = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.pinterest.com/pin-builder/",
            "X-Pinterest-AppState": "active",
            "X-Pinterest-PWS-Handler": "www/pin-builder/index.js",
            "X-APP-VERSION": "4fc27a6"
        }

    def refresh_csrf(self):
        try:
            resp = self.http.get("https://www.pinterest.com/pin-builder/", headers=self.headers, timeout=15)
            self.csrf_token = self.http.cookies.get("csrftoken", "")
            self.headers["X-CSRFToken"] = self.csrf_token
            return bool(self.csrf_token)
        except Exception as e:
            print(f"[-] Failed to get CSRF token: {e}")
            return False

    def get_user_boards(self):
        if not self.csrf_token:
            self.refresh_csrf()
        data = {"options": {"username": self.username, "field_set_key": "detailed"}, "context": {}}
        try:
            resp = self.http.get(
                "https://www.pinterest.com/resource/BoardsResource/get/",
                headers=self.headers,
                params={"source_url": f"/{self.username}/", "data": json.dumps(data)},
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get("resource_response", {}).get("data", [])
        except Exception as e:
            print(f"[-] Error fetching boards: {e}")
        return []

    def create_board(self, name: str, description: str = "Trending viral aesthetics and looks."):
        if not self.csrf_token:
            self.refresh_csrf()

        data = {
            "options": {
                "name": name,
                "privacy": "PUBLIC",
                "description": description
            },
            "context": {}
        }
        payload = {
            "source_url": "/pin-builder/",
            "data": json.dumps(data)
        }
        try:
            resp = self.http.post(
                "https://www.pinterest.com/resource/BoardResource/create/",
                headers=self.headers,
                data=payload,
                timeout=20
            )
            if resp.status_code == 200:
                res = resp.json().get("resource_response", {}).get("data", {})
                b_id = res.get("id")
                if b_id:
                    print(f"[✓] Created New Board: '{name}' (ID: {b_id})")
                    return b_id
        except Exception as e:
            print(f"[-] Error creating board '{name}': {e}")
        return None

    def ensure_viral_boards(self):
        """
        Ensures the 4 high-converting target boards exist on Pinterest account.
        Returns a list of board IDs.
        """
        existing = self.get_user_boards()
        existing_map = {b.get("name"): b.get("id") for b in existing if b.get("name") and b.get("id")}
        
        target_ids = []
        for name in TARGET_BOARD_NAMES:
            if name in existing_map:
                target_ids.append(existing_map[name])
                print(f"[✓] Found existing board: '{name}' (ID: {existing_map[name]})")
            else:
                # Create it
                new_id = self.create_board(name)
                if new_id:
                    target_ids.append(new_id)
                elif existing:
                    # Fallback to first existing board if creation blocked
                    target_ids.append(existing[0].get("id"))

        if not target_ids and existing:
            target_ids = [b.get("id") for b in existing[:4]]
            
        return target_ids

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
        payload = {
            "source_url": "/pin-builder/",
            "data": json.dumps(data)
        }
        try:
            resp = self.http.post(
                "https://www.pinterest.com/resource/PinResource/create/",
                headers=self.headers,
                data=payload,
                timeout=25
            )
            if resp.status_code == 200:
                res_data = resp.json()
                pin_data = res_data.get("resource_response", {}).get("data", {})
                pin_id = pin_data.get("id")
                if pin_id:
                    return {"success": True, "pin_id": pin_id, "url": f"https://www.pinterest.com/pin/{pin_id}/"}
            return {"success": False, "error": f"Status {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def uniquify_image(source_img_path: Path, output_img_path: Path):
    """
    Applies image manipulation so Pinterest Visual AI sees it as a 100% Brand-New Image:
    1. Horizontal Flip (Mirror)
    2. 2-3% Micro-Crop (changes aspect ratio and edge pixels)
    3. EXIF metadata strip
    """
    try:
        with Image.open(source_img_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 1. Horizontal Mirror Flip
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

            # 2. 2.5% Micro-Crop
            w, h = img.size
            crop_x = int(w * 0.025)
            crop_y = int(h * 0.025)
            img = img.crop((crop_x, crop_y, w - crop_x, h - crop_y))

            # 3. Save clean without original EXIF
            img.save(output_img_path, "JPEG", quality=95, optimize=True)
            return True
    except Exception as e:
        print(f"[-] Uniquify error on {source_img_path}: {e}")
        return False


def scrape_fresh_viral_batch(max_per_board: int = 15):
    """
    Scrapes fresh photos on-demand from source boards in 'viral catalogs',
    uniquifies them, and saves to database ready for posting.
    """
    catalogs_file = config.VIRAL_CATALOGS_FILE
    if not catalogs_file.exists():
        print(f"[-] Catalogs file not found: {catalogs_file}")
        return 0

    with open(catalogs_file, "r", encoding="utf-8") as f:
        board_urls = [line.strip() for line in f if line.strip().startswith("http")]

    if not board_urls:
        print("[-] No board URLs in viral catalogs file.")
        return 0

    print(f"\n🔍 [Live Scraper] Scanning {len(board_urls)} source boards for fresh images...")
    new_added = 0

    for b_url in board_urls:
        slug = b_url.rstrip("/").split("/")[-1]
        try:
            cmd = ["gallery-dl", "--get-urls", b_url]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
            img_urls = [l.strip() for l in res.stdout.splitlines() if l.strip().startswith("http")]
        except Exception as e:
            print(f"[-] gallery-dl error on {b_url}: {e}")
            continue

        for u in img_urls[:max_per_board]:
            if database.is_viral_source_scraped(u):
                continue

            # Download temporary
            url_hash = hashlib.md5(u.encode("utf-8")).hexdigest()[:12]
            temp_path = VIRAL_MEDIA_DIR / f"temp_{url_hash}.jpg"
            clean_filename = f"viral_{slug}_{url_hash}.jpg"
            final_path = VIRAL_MEDIA_DIR / clean_filename

            try:
                r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                if r.status_code == 200:
                    with open(temp_path, "wb") as f:
                        f.write(r.content)

                    # Uniquify (Mirror + Micro-Crop)
                    if uniquify_image(temp_path, final_path):
                        title = random.choice(VIRAL_TITLES)
                        desc = (
                            "Exclusive private 1080p stream unlocked on our portal. "
                            "Click Visit Site to complete quick access and watch the full uncensored video on Telegram! 🔞✨"
                        )
                        rel_path = f"viral/{clean_filename}"
                        database.insert_viral_item(u, slug, rel_path, title, desc)
                        new_added += 1

                    # Remove temp file
                    if temp_path.exists():
                        temp_path.unlink()
            except Exception as e:
                print(f"[-] Error processing {u}: {e}")

    print(f"✅ [Live Scraper] Added {new_added} fresh unique images to Viral Queue!")
    return new_added


def post_next_viral_pin(poster: PinterestViralClient, board_ids: list):
    """
    Posts the next queued viral item to one of the rotated target boards.
    """
    item = database.get_next_unposted_viral_item()
    if not item:
        return False

    item_id = item["id"]
    target_board_id = random.choice(board_ids) if board_ids else None

    if not target_board_id:
        print("[-] No target board ID available to post pin.")
        return False

    base_url = config.SITE_BASE_URL.rstrip("/") if config.SITE_BASE_URL else "https://pintrest-automation.onrender.com"
    landing_url = f"{base_url}/v/{item_id}"
    image_url = f"{base_url}/media/{item['file_path']}"

    print(f"\n[*] Posting Viral Pin #{item_id}:")
    print(f"  • Title: {item['seo_title']}")
    print(f"  • Target Board ID: {target_board_id}")
    print(f"  • Video Gate Link: {landing_url}")

    res = poster.create_pin(
        board_id=target_board_id,
        title=item["seo_title"],
        description=item["seo_description"],
        link=landing_url,
        image_url=image_url
    )

    if res.get("success"):
        pin_id = res["pin_id"]
        pin_url = res["url"]
        database.mark_viral_item_posted(item_id, pin_id, target_board_id)
        stats = database.get_viral_stats()
        print(f"[✓] Viral Pin #{item_id} successfully created on Pinterest! URL: {pin_url}")

        notif_msg = (
            f"🔥 <b>Viral 18+ Pin Posted!</b>\n\n"
            f"🏷️ <b>Title:</b> {item['seo_title']}\n"
            f"📌 <b>Pin URL:</b> <a href=\"{pin_url}\">{pin_url}</a>\n"
            f"🎬 <b>5-Click Video Gate:</b> <a href=\"{landing_url}\">{landing_url}</a>\n"
            f"🤖 <b>Telegram Redirect:</b> {config.TELEGRAM_REDIRECT_BOT}\n\n"
            f"📊 <b>Progress:</b> Total Posted: <b>{stats['posted_viral_pins']}</b> | In Queue: <b>{stats['pending_viral_pins']}</b>\n"
            f"⚡ <i>Auto-posted via Viral Engine</i>"
        )
        send_telegram_notification(notif_msg)
        return True
    else:
        err = res.get("error", "Unknown error")
        print(f"[-] Failed to post Viral Pin #{item_id}: {err}")
        database.mark_viral_item_error(item_id, err)
        return False


def run_viral_worker():
    database.init_db()
    print("=" * 65)
    print("🚀 VIRAL 18+ CLICKBAIT PINTEREST AUTO-POSTER STARTED")
    print(f"  • Session User: {config.VIRAL_PINTEREST_USERNAME or 'Not configured'}")
    print(f"  • Post Interval: Every {config.VIRAL_POST_INTERVAL_MINUTES} minutes")
    print(f"  • Ad Monetization: 5-Click Smartlink -> {config.TELEGRAM_REDIRECT_BOT}")
    print("=" * 65)

    session_cookie = config.VIRAL_PINTEREST_SESSION
    username = config.VIRAL_PINTEREST_USERNAME

    if not session_cookie:
        print("\n⚠️ [CONFIG NOTICE] VIRAL_PINTEREST_SESSION is not set in .env yet!")
        print("Kripya naye Pinterest account ka '_pinterest_sess' cookie .env me dalein.")
        return

    poster = PinterestViralClient(session_cookie, username)

    # 1. Ensure target boards exist
    print("\n[Step 1/2] Connecting to Pinterest & Ensuring Target Boards...")
    board_ids = poster.ensure_viral_boards()
    if not board_ids:
        print("[-] Could not retrieve or create boards on Pinterest. Please check session cookie.")
        return

    print(f"[✓] Active Board Pool: {board_ids}")

    # 2. Main 24x7 Loop
    print("\n[Step 2/2] Entering 24x7 Live Scrape & Auto-Post Loop...")
    send_telegram_notification("🚀 <b>Viral 18+ Pinterest Engine Started!</b>\n\nAuto-posting live pins with 5-Click Video Player gate.")

    while True:
        # Check if queue has unposted items
        next_item = database.get_next_unposted_viral_item()
        if not next_item:
            print("[*] Viral queue is empty. Scraping fresh batch from catalogs...")
            count = scrape_fresh_viral_batch(max_per_board=10)
            if count == 0:
                print("[!] No new images could be scraped right now. Retrying in 10 minutes...")
                time.sleep(600)
                continue

        # Post next pin
        post_next_viral_pin(poster, board_ids)

        # Sleep interval
        sleep_secs = max(config.VIRAL_POST_INTERVAL_MINUTES * 60, 600)
        print(f"\n[*] Sleeping {config.VIRAL_POST_INTERVAL_MINUTES} minutes until next scheduled pin...")
        time.sleep(sleep_secs)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scrape-only":
        database.init_db()
        scrape_fresh_viral_batch(max_per_board=10)
    else:
        run_viral_worker()

