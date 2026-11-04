import os
import sys
import re
import time
import requests
from pathlib import Path
from urllib.parse import urljoin

# Force UTF-8 for console output on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import TELEGRAM_CHANNEL, MEDIA_DIR
import database
import seo_generator
import firebase_db
from notifier import send_telegram_notification

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

def clean_html_text(raw_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw_html)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def scrape_telegram_web(channel: str = TELEGRAM_CHANNEL, max_items: int = 50):
    """
    Scrapes photos, videos, and captions directly from Telegram public web interface:
    https://t.me/s/{channel}
    No bot admin rights, phone number, or OTP required!
    """
    database.init_db()
    channel = channel.replace("https://t.me/", "").replace("@", "").strip()
    base_url = f"https://t.me/s/{channel}"
    
    print(f"\n================ TELEGRAM WEB SCRAPER ================")
    print(f"Target Channel: https://t.me/{channel}")
    print(f"Target Count:   Up to {max_items} media items")
    print("======================================================")

    current_url = base_url
    saved_count = 0
    skipped_count = 0
    before_id = None

    # Load all already posted pins from Firebase (permanent cloud record)
    posted_in_firebase = firebase_db.get_posted_ids()
    print(f"[*] Loaded {len(posted_in_firebase)} previously posted pins from Firebase.")

    while saved_count < max_items:
        fetch_url = f"{base_url}?before={before_id}" if before_id else base_url
        print(f"\n[*] Fetching batch from: {fetch_url}")
        
        try:
            resp = requests.get(fetch_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"[-] HTTP Error {resp.status_code}")
                break
        except Exception as e:
            print(f"[-] Request error: {e}")
            break

        html = resp.text
        
        # Find all message blocks: tgme_widget_message
        msg_blocks = re.findall(
            r'(<div class="tgme_widget_message\b[^"]*"[^>]*data-post="([^"]+)"[^>]*>.*?)(?=<div class="tgme_widget_message\b|\Z)',
            html,
            re.DOTALL
        )

        if not msg_blocks:
            print("[*] No more message blocks found.")
            break

        first_msg_id = None
        for block_html, data_post in msg_blocks:
            # data_post format: Nox_oo1/1234
            try:
                msg_id = int(data_post.split("/")[-1])
            except (ValueError, IndexError):
                continue

            if first_msg_id is None or msg_id < first_msg_id:
                first_msg_id = msg_id

            # Check if already posted in Firebase (permanent cloud check)
            if str(msg_id) in posted_in_firebase:
                skipped_count += 1
                continue

            # Check if already scraped in local DB
            conn = database.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM media_items WHERE telegram_msg_id = ?", (msg_id,))
            exists = cursor.fetchone()
            conn.close()

            if exists:
                skipped_count += 1
                continue

            # Extract image URL
            # Look for background-image:url('...')
            img_matches = re.findall(r"background-image:url\('([^']+)'\)", block_html)
            valid_imgs = [img for img in img_matches if "telegram.org/img/emoji" not in img]
            
            # Extract video URL
            vid_matches = re.findall(r'<video[^>]+src="([^"]+)"', block_html)

            # Extract caption
            text_match = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block_html, re.DOTALL)
            caption = clean_html_text(text_match.group(1)) if text_match else ""

            media_type = None
            media_url = None
            filename = None

            if valid_imgs:
                media_type = "photo"
                media_url = valid_imgs[0]
                filename = f"photo_{msg_id}.jpg"
            elif vid_matches:
                media_type = "video"
                media_url = vid_matches[0]
                filename = f"video_{msg_id}.mp4"

            if not media_type or not media_url:
                continue

            dest_path = MEDIA_DIR / filename
            print(f"[↓] Downloading #{msg_id} ({media_type}) -> {filename}...")
            
            try:
                media_resp = requests.get(media_url, headers=HEADERS, timeout=20)
                if media_resp.status_code == 200:
                    dest_path.write_bytes(media_resp.content)
                else:
                    print(f"[-] Failed to download #{msg_id} (HTTP {media_resp.status_code})")
                    continue
            except Exception as e:
                print(f"[-] Error downloading #{msg_id}: {e}")
                continue

            file_size = dest_path.stat().st_size if dest_path.exists() else 0
            
            # Generate SEO title, description & tags
            seo = seo_generator.generate_seo_metadata(caption=caption, media_type=media_type, msg_id=msg_id)
            
            # Insert into database with cdn_url for zero-storage mode
            item_id = database.insert_media_item(
                msg_id=msg_id,
                media_type=media_type,
                file_path=filename,
                original_filename=filename,
                file_size=file_size,
                caption=caption,
                title=seo["title"],
                description=seo["description"],
                tags=seo["tags"],
                cdn_url=media_url
            )
            saved_count += 1
            print(f"[✓] Saved Item #{item_id} | Title: {seo['title']}")

            if saved_count >= max_items:
                break

        # Check pagination
        if first_msg_id and (before_id is None or first_msg_id < before_id):
            before_id = first_msg_id
        else:
            print("[*] Reached end of accessible channel history.")
            break

        time.sleep(1) # respectful rate limit

    print("\n================ SCRAPING SUMMARY ================")
    print(f"Total New Items Saved: {saved_count}")
    print(f"Items Already in DB:   {skipped_count}")
    stats = database.get_stats()
    print(f"Total Media in DB:     {stats['total_media']} (Pending pins: {stats['pending_pins']})")
    print("==================================================")

    if saved_count > 0:
        msg = (
            f"📥 <b>Telegram Media Scraped!</b>\n\n"
            f"• <b>New Wallpapers Added:</b> +{saved_count}\n"
            f"• <b>In Queue Ready to Post:</b> {stats['pending_pins']}\n"
            f"• <b>Source:</b> <code>t.me/{channel}</code>\n\n"
            f"⚡ <i>Auto-Scraper Active</i>"
        )
        send_telegram_notification(msg)

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    scrape_telegram_web(max_items=limit)
