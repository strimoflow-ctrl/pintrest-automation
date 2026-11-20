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

BANNER_TEXT = 'CLICK "VISIT SITE" TO VIEW ALL'
GOLD = (224, 168, 153, 255)
DARK = (16, 9, 18, 255)

FONT_CANDIDATES = [
    str(Path(__file__).parent / "fonts" / "bold.ttf"),  # optional: apna font yaha rakh sakte ho
    "arialbd.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]


def _load_font(size: int):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        # Pillow >= 10.1 ka built-in scalable font
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox


def _load_source_image_bytes(image_urls: list) -> Optional[bytes]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    for src in image_urls:
        if not src:
            continue
        try:
            # Local file path support
            if not str(src).startswith("http"):
                if os.path.exists(src):
                    with open(src, "rb") as f:
                        data = f.read()
                    if len(data) > 5000:
                        return data
                continue
            resp = requests.get(src, headers=headers, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 5000:
                return resp.content
        except Exception:
            continue
    return None


class BannerGenerator:
    @staticmethod
    def create_pinterest_banner(image_urls: list, slug: str, title: str) -> Optional[Path]:
        """
        Source image ko download karke 1000x1500 (2:3) me crop karta hai
        aur neeche saaf, readable CTA banner lagata hai (koi emoji nahi).
        """
        out_path = BANNERS_DIR / f"{slug}_v2.jpg"
        if out_path.exists() and out_path.stat().st_size > 10000:
            return out_path

        img_bytes = _load_source_image_bytes(image_urls)
        if not img_bytes:
            print(f"[-] Could not download any valid image for {slug}")
            return None

        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            orig_w, orig_h = img.size

            target_w, target_h = 1000, 1500

            scale = max(target_w / orig_w, target_h / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            base = img_resized.crop((left, top, left + target_w, top + target_h))

            overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # 1) Neeche smooth dark gradient (text hamesha readable rahe)
            grad_h = 340
            for i in range(grad_h):
                y = target_h - grad_h + i
                alpha = int(235 * (i / grad_h) ** 1.4)
                draw.line([(0, y), (target_w, y)], fill=(16, 9, 18, alpha))

            # 2) Text size auto-fit
            pad_x = 48
            arrow_w = 44
            gap = 26
            max_pill_w = target_w - 80
            font_size = 52
            while font_size > 26:
                font = _load_font(font_size)
                text_w, text_h, bbox = _text_size(draw, BANNER_TEXT, font)
                pill_w = text_w + gap + arrow_w + pad_x * 2
                if pill_w <= max_pill_w:
                    break
                font_size -= 2
            text_w, text_h, bbox = _text_size(draw, BANNER_TEXT, font)
            pill_w = text_w + gap + arrow_w + pad_x * 2

            # 3) Rose-gold pill button, dark text (high contrast)
            pill_h = 118
            pill_x0 = (target_w - pill_w) // 2
            pill_x1 = pill_x0 + pill_w
            pill_y1 = target_h - 70
            pill_y0 = pill_y1 - pill_h
            center_y = (pill_y0 + pill_y1) // 2

            draw.rounded_rectangle(
                [pill_x0, pill_y0, pill_x1, pill_y1],
                radius=pill_h // 2,
                fill=GOLD,
            )

            # 4) Text (bbox offset ke saath perfectly centered)
            text_x = pill_x0 + pad_x - bbox[0]
            text_y = center_y - text_h // 2 - bbox[1]
            draw.text((text_x, text_y), BANNER_TEXT, fill=DARK, font=font)

            # 5) Arrow shape (font glyph nahi, to box nahi banega)
            ax = pill_x0 + pad_x + text_w + gap
            draw.polygon(
                [(ax, center_y - 20), (ax + 30, center_y), (ax, center_y + 20)],
                fill=DARK,
            )

            final_img = Image.alpha_composite(base, overlay).convert("RGB")
            final_img.save(out_path, "JPEG", quality=92, optimize=True)
            print(f"[OK] Created Pinterest banner: {out_path.name}")
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
            for b in boards:
                if "nail" in b.get("name", "").lower():
                    return str(b.get("id"))
            return str(boards[0].get("id"))
        return None

    def upload_image(self, image_path: Path) -> Optional[str]:
        """
        Banner wali image seedha Pinterest ke server par upload karta hai
        aur Pinterest ka apna image URL (pinimg) return karta hai.
        Koi external hosting nahi chahiye.
        """
        if not self.csrf_token:
            self.refresh_csrf()

        up_headers = dict(self.headers)
        up_headers["X-UPLOAD-SOURCE"] = "pinner_uploader"
        up_headers["Referer"] = "https://www.pinterest.com/pin-builder/"

        try:
            with open(image_path, "rb") as f:
                files = {"img": (image_path.name, f, "image/jpeg")}
                resp = self.http.post(
                    "https://www.pinterest.com/upload-image/",
                    headers=up_headers,
                    files=files,
                    timeout=60
                )
            if resp.status_code == 200:
                data = resp.json()
                url = (
                    data.get("image_url")
                    or (data.get("data") or {}).get("image_url")
                    or (data.get("resource_response", {}).get("data") or {}).get("image_url")
                )
                if url:
                    return url
            print(f"[-] Upload failed: status {resp.status_code}: {resp.text[:250]}")
        except Exception as e:
            print(f"[-] Upload failed: {e}")
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
            resp = self.http.post(url, headers=self.headers, data=post_payload, timeout=30)
            if resp.status_code == 200:
                res_data = resp.json()
                pin_data = res_data.get("resource_response", {}).get("data", {})
                pin_id = pin_data.get("id")
                if pin_id:
                    return {"success": True, "pin_id": pin_id, "url": f"https://www.pinterest.com/pin/{pin_id}/"}
            return {"success": False, "error": f"Status {resp.status_code}: {resp.text[:250]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def _cleanup_banner(banner_path: Optional[Path]):
    try:
        if banner_path and Path(banner_path).exists():
            Path(banner_path).unlink()
    except Exception:
        pass


def post_next_nail_pin(_depth: int = 0) -> bool:
    """
    Pipeline:
    1. Queue se next unposted pin lo.
    2. Source image (DB wala image_url) download -> banner lagao.
    3. Banner wali image seedha Pinterest par upload karo.
    4. Pin create karo, DB + Firebase me record, Telegram alert.
    """
    if _depth > 25:
        print("[-] Too many skipped pins in a row, stopping.")
        return False

    pin = database.get_next_unposted_pin()
    if not pin:
        print("[*] No unposted nail pins found in queue!")
        return False

    pin_key = pin["pin_key"]
    slug = pin["collection_slug"]
    title = pin["collection_title"]
    image_url = pin["image_url"]
    img_idx = pin["image_index"]

    if firebase_db.is_pin_posted_in_firebase(pin_key):
        print(f"[*] Pin #{pin_key} already exists in Firebase RTDB. Skipping...")
        database.mark_pin_posted(pin_key, "firebase_synced")
        return post_next_nail_pin(_depth + 1)

    print(f"\n[+] Processing Pin #{pin['id']} ({title} - Look #{img_idx})")

    # 1. Banner banao
    banner_path = BannerGenerator.create_pinterest_banner([image_url], pin_key, title)
    if not banner_path:
        print(f"[-] Banner failed for {pin_key} (source image issue). Marking skipped.")
        database.mark_pin_posted(pin_key, "skipped_bad_image")
        return post_next_nail_pin(_depth + 1)

    landing_url = f"{config.SITE_BASE_URL}/#/nail/{slug}"

    if not config.PINTEREST_SESSION:
        print("[-] PINTEREST_SESSION missing in .env! Cannot post to Pinterest.")
        return False

    poster = PinterestPoster(config.PINTEREST_SESSION)
    board_id = poster.get_or_pick_board()
    if not board_id:
        print("[-] No valid Pinterest board found! Please set PINTEREST_BOARD_ID in .env.")
        return False

    pin_title = pin.get("pin_title") or f"{title} - Look #{img_idx} | Aesthetic Nails"
    pin_desc = pin.get("pin_description") or f"Looking for aesthetic nail inspiration? Check out this stunning {title}. Tap visit for all looks & shades!"

    # 2. Banner wali image direct Pinterest par upload (2 koshish)
    uploaded_url = None
    for attempt in range(2):
        uploaded_url = poster.upload_image(banner_path)
        if uploaded_url:
            break
        time.sleep(3)

    if not uploaded_url:
        print("[-] Image upload to Pinterest failed. Pin NOT posted (bina banner ke post nahi karenge).")
        return False

    # 3. Pin create
    print(f"[*] Posting to Pinterest board {board_id}...")
    res = poster.create_pin(
        board_id=board_id,
        title=pin_title,
        description=pin_desc,
        link=landing_url,
        image_url=uploaded_url
    )

    if not res.get("success"):
        print(f"[-] Pinterest posting failed: {res.get('error')}")
        return False

    pin_id = res.get("pin_id")
    pin_url = res.get("url")
    print(f"[OK] PIN POSTED SUCCESSFULLY: {pin_url}")

    database.mark_pin_posted(pin_key, pin_id)

    firebase_db.record_posted_pin_in_firebase(pin_key, {
        "pin_id": pin_id,
        "pin_url": pin_url,
        "collection_title": title,
        "collection_slug": slug,
        "image_index": img_idx,
        "landing_url": landing_url,
        "posted_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    })

    caption = (
        f"💅 <b>NEW NAIL PIN POSTED!</b>\n\n"
        f"📌 <b>Title:</b> {title} (Look #{img_idx})\n"
        f"🔗 <b>Pinterest Pin:</b> <a href='{pin_url}'>View on Pinterest</a>\n"
        f"🌐 <b>Lookbook:</b> <a href='{landing_url}'>View Collection</a>\n"
        f"✨ <b>Source:</b> HD Nail Lookbook"
    )
    try:
        send_telegram_alert(caption, photo_path=banner_path)
    except Exception as e:
        print(f"[-] Telegram alert failed: {e}")

    _cleanup_banner(banner_path)
    return True


if __name__ == "__main__":
    database.populate_catalogs_if_empty()
    stats = database.get_stats()
    print(f"[*] Database stats: {stats}")
