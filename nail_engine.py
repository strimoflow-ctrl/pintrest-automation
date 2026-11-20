import os
import sys
import time
import json
import requests
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import database
import firebase_db
from notifier import send_telegram_alert

BANNERS_DIR = config.MEDIA_DIR / "nail_banners"
BANNERS_DIR.mkdir(parents=True, exist_ok=True)

class BannerGenerator:
    @staticmethod
    def create_pinterest_banner(image_urls: list, slug: str, title: str) -> Optional[Path]:
        """
        Downloads a source nail image (tries featured first, then falls back to any in all_images),
        resizes/crops to optimal Pinterest 2:3 vertical format,
        and adds a high-converting luxury aesthetic text banner overlay.
        """
        out_path = BANNERS_DIR / f"{slug}.jpg"
        if out_path.exists() and out_path.stat().st_size > 10000:
            return out_path

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        img_bytes = None
        for img_url in image_urls:
            if not img_url or not img_url.startswith("http"):
                continue
            try:
                resp = requests.get(img_url, headers=headers, timeout=8)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    img_bytes = resp.content
                    break
            except Exception as e:
                continue

        if not img_bytes:
            print(f"[-] Could not download any valid image for {slug}")
            return None

        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            orig_w, orig_h = img.size

            # Target 1000x1500 (2:3 Pinterest standard)
            target_w = 1000
            target_h = 1500

            # Resize while keeping aspect ratio and center crop
            scale = max(target_w / orig_w, target_h / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            img_cropped = img_resized.crop((left, top, left + target_w, top + target_h))

            # Overlay Canvas
            overlay = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            # Fonts
            try:
                font_top = ImageFont.truetype("arialbd.ttf", 34)
                font_main = ImageFont.truetype("arialbd.ttf", 48)
                font_sub = ImageFont.truetype("arialbd.ttf", 30)
            except Exception:
                font_top = ImageFont.load_default()
                font_main = ImageFont.load_default()
                font_sub = ImageFont.load_default()

            # 1. Top Luxury Badge
            badge_h = 60
            badge_w = 460
            badge_x = (target_w - badge_w) // 2
            badge_y = 50
            draw.rounded_rectangle(
                [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                radius=30,
                fill=(26, 11, 20, 230),
                outline=(224, 168, 153, 255),
                width=3
            )
            draw.text((target_w // 2, badge_y + (badge_h // 2)), "✨ 2026 TRENDING NAIL ART", fill=(255, 255, 255, 255), font=font_top, anchor="mm")

            # 2. Bottom Luxury Dark-Rose Banner (300px height)
            banner_h = 240
            banner_y = target_h - banner_h
            draw.rectangle([0, banner_y, target_w, target_h], fill=(22, 10, 18, 240))
            # Gold Divider Line
            draw.line([(0, banner_y), (target_w, banner_y)], fill=(224, 168, 153, 255), width=6)

            # Main text & Subtext
            draw.text((target_w // 2, banner_y + 80), "AESTHETIC NAIL LOOKBOOK 💅", fill=(255, 255, 255, 255), font=font_main, anchor="mm")
            draw.text((target_w // 2, banner_y + 160), "TAP VISIT TO VIEW ALL LOOKS & SHADES ✨", fill=(244, 194, 194, 255), font=font_sub, anchor="mm")

            # Composite and save
            final_img = Image.alpha_composite(img_cropped, overlay).convert("RGB")
            final_img.save(out_path, "JPEG", quality=92, optimize=True)
            print(f"[✓] Created Pinterest banner: {out_path.name}")
            return out_path

        except Exception as e:
            print(f"[-] Error creating banner for {slug}: {e}")
            return None


class PinterestPoster:
    def __init__(self, session_cookie: str):
        self.session_cookie = session_cookie
        self.http = requests.Session()
        self.http.cookies.set("_pinterest_sess", session_cookie, domain=".pinterest.com")
        self.app_version = "4fc27a6"
        self.csrf_token = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.pinterest.com/pin-builder/",
            "X-Pinterest-AppState": "active",
            "X-Pinterest-PWS-Handler": "www/pin-builder/index.js",
            "X-APP-VERSION": self.app_version
        }

    def refresh_csrf(self) -> bool:
        try:
            self.http.get("https://www.pinterest.com/pin-builder/", headers=self.headers, timeout=15)
            self.csrf_token = self.http.cookies.get("csrftoken", "")
            self.headers["X-CSRFToken"] = self.csrf_token
            return bool(self.csrf_token)
        except Exception as e:
            print(f"[-] Failed to get CSRF token: {e}")
            return False

    def get_user_boards(self) -> list:
        if not self.csrf_token:
            self.refresh_csrf()
        try:
            resp = self.http.get(
                "https://www.pinterest.com/resource/BoardPickerBoardsResource/get/",
                headers=self.headers,
                params={"source_url": "/pin-builder/", "data": json.dumps({"options": {"allow_stale": True}, "context": {}})},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json().get("resource_response", {}).get("data", {})
                return data.get("all_boards", [])
        except Exception as e:
            print(f"[-] Error fetching boards: {e}")
        return []

    def get_or_pick_board(self) -> Optional[str]:
        if config.PINTEREST_BOARD_ID:
            return config.PINTEREST_BOARD_ID
        boards = self.get_user_boards()
        if boards and len(boards) > 0:
            # Prefer a board with 'nail' in the name
            for b in boards:
                if "nail" in b.get("name", "").lower():
                    return str(b.get("id"))
            return str(boards[0].get("id"))
        return None

    def create_pin(self, board_id: str, title: str, description: str, link: str, image_url: str) -> Dict[str, Any]:
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

        url = "https://www.pinterest.com/resource/PinResource/create/"
        try:
            resp = self.http.post(url, headers=self.headers, data=post_payload, timeout=20)
            if resp.status_code == 200:
                res_data = resp.json()
                pin_data = res_data.get("resource_response", {}).get("data", {})
                pin_id = pin_data.get("id")
                if pin_id:
                    return {"success": True, "pin_id": pin_id, "url": f"https://www.pinterest.com/pin/{pin_id}/"}
            return {"success": False, "error": f"Status {resp.status_code}: {resp.text[:250]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def post_next_nail_pin() -> bool:
    """
    Main execution pipeline:
    1. Grabs next unposted nail tutorial from SQLite.
    2. Generates high-converting Pinterest banner.
    3. Posts to Pinterest session.
    4. Marks posted and alerts owner via Telegram.
    """
    tutorial = database.get_next_unposted_tutorial()
    if not tutorial:
        print("[*] No unposted nail tutorials found in database!")
        return False

    tutorial_id = tutorial["tutorial_id"]
    slug = tutorial["slug"]
    title = tutorial["title"]
    featured_img = tutorial["featured_image"]
    
    # Cloud check: If already in Firebase RTDB, mark and skip
    if firebase_db.is_pin_posted_in_firebase(tutorial_id):
        print(f"[*] Tutorial #{tutorial_id} already exists in Firebase RTDB. Skipping...")
        database.mark_tutorial_posted(tutorial_id, "firebase_synced")
        return post_next_nail_pin()
    
    print(f"\n[+] Processing Tutorial #{tutorial['id']}: {title}")
    
    # 1. Create Pinterest Banner
    all_imgs = [featured_img] + tutorial.get("all_images", [])
    banner_path = BannerGenerator.create_pinterest_banner(all_imgs, slug, title)
    
    # Target Destination URL on our website (SPA Lookbook)
    landing_url = f"{config.SITE_BASE_URL}/#/nail/{slug}"
    
    # Direct image url to provide to Pinterest
    # If site is deployed on render, we can use our hosted banner URL, or fallback to original high-res image
    image_url_for_pin = f"{config.SITE_BASE_URL}/media/nail_banners/{slug}.jpg"
    
    # 2. Pinterest Posting
    if not config.PINTEREST_SESSION:
        print("[-] PINTEREST_SESSION missing in .env! Cannot post to Pinterest.")
        return False

    poster = PinterestPoster(config.PINTEREST_SESSION)
    board_id = poster.get_or_pick_board()
    if not board_id:
        print("[-] No valid Pinterest board found! Please set PINTEREST_BOARD_ID in .env.")
        return False

    pin_title = tutorial.get("pinterest_title") or f"{title} | Easy DIY Tutorial ✨"
    pin_desc = tutorial.get("pinterest_description") or f"Step-by-step DIY tutorial for {title}. Tap visit for the full guide! 💅"

    print(f"[*] Posting to Pinterest board {board_id}...")
    res = poster.create_pin(
        board_id=board_id,
        title=pin_title,
        description=pin_desc,
        link=landing_url,
        image_url=image_url_for_pin
    )

    if res.get("success"):
        pin_id = res.get("pin_id")
        pin_url = res.get("url")
        print(f"[✓] PIN POSTED SUCCESSFULLY: {pin_url}")
        database.mark_tutorial_posted(tutorial["tutorial_id"], pin_id)
        
        # Cloud Record in Firebase RTDB
        firebase_db.record_posted_pin_in_firebase(tutorial["tutorial_id"], {
            "pin_id": pin_id,
            "pin_url": pin_url,
            "title": title,
            "slug": slug,
            "landing_url": landing_url,
            "posted_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Telegram Notification
        caption = (
            f"💅 <b>NEW NAIL TUTORIAL PIN POSTED!</b>\n\n"
            f"📌 <b>Title:</b> {title}\n"
            f"🔗 <b>Pinterest Pin:</b> <a href='{pin_url}'>View on Pinterest</a>\n"
            f"🌐 <b>Website Landing:</b> <a href='{landing_url}'>View Article</a>\n"
            f"✨ <b>Steps:</b> {len(tutorial.get('tutorial_steps', []))} Steps Included\n"
            f"🖼 <b>Gallery:</b> {tutorial.get('image_count', 0)} HD Photos"
        )
        send_telegram_alert(caption, photo_path=banner_path)
        return True
    else:
        print(f"[-] Pinterest posting failed: {res.get('error')}")
        # Retry with original high-res image URL if local render banner isn't reachable yet
        print("[*] Retrying with source image URL...")
        res_retry = poster.create_pin(
            board_id=board_id,
            title=pin_title,
            description=pin_desc,
            link=landing_url,
            image_url=featured_img
        )
        if res_retry.get("success"):
            pin_id = res_retry.get("pin_id")
            pin_url = res_retry.get("url")
            print(f"[✓] PIN POSTED VIA SOURCE URL: {pin_url}")
            database.mark_tutorial_posted(tutorial["tutorial_id"], pin_id)
            
            # Cloud Record in Firebase RTDB
            firebase_db.record_posted_pin_in_firebase(tutorial["tutorial_id"], {
                "pin_id": pin_id,
                "pin_url": pin_url,
                "title": title,
                "slug": slug,
                "landing_url": landing_url,
                "posted_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            caption = (
                f"💅 <b>NEW NAIL PIN POSTED (Source CDN)!</b>\n\n"
                f"📌 <b>Title:</b> {title}\n"
                f"🔗 <b>Pinterest Pin:</b> <a href='{pin_url}'>View on Pinterest</a>\n"
                f"🌐 <b>Website:</b> <a href='{landing_url}'>View Article</a>"
            )
            send_telegram_alert(caption, photo_path=banner_path)
            return True
        else:
            print(f"[-] Retry also failed: {res_retry.get('error')}")
            return False

if __name__ == "__main__":
    database.populate_catalogs_if_empty()
    stats = database.get_stats()
    print(f"[*] Database stats: {stats}")
