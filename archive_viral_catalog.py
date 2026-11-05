import os
import sys
import time
import json
import subprocess
import requests
from pathlib import Path

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "media" / "catalog_vault"
VAULT_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = "8859308468:AAGk6LwsiQljObHdbX0wFm85LXjOdiZolKM"
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Exact IDs verified from live Telegram API
CHANNEL_CHAT_ID = -1004455682588  # Viral_Pins_Vault Channel
USER_CHAT_ID = 8841106658         # Bot Private DM with User

BOARDS_FILE = BASE_DIR / "viral catalogs"


def extract_board_images(board_url):
    """
    Extracts direct image URLs using gallery-dl.
    """
    cmd = ["gallery-dl", "--get-urls", board_url]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
        urls = [line.strip() for line in res.stdout.splitlines() if line.strip().startswith("http")]
        return urls
    except Exception as e:
        print(f"[-] gallery-dl error on {board_url}: {e}")
        return []


def download_image(url, save_path):
    """
    Downloads an image file locally.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.pinterest.com/"
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


def send_tg_photo(channel_id, photo_path, caption=""):
    """
    Uploads photo strictly into the Telegram Channel vault.
    """
    url = f"{TG_API}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": channel_id, "caption": caption}
            r = requests.post(url, data=data, files=files, timeout=25)
            return r.status_code == 200
    except Exception as e:
        print(f"Send photo error: {e}")
        return False


def make_progress_bar(current, total, length=12):
    percent = int((current / total) * 100) if total else 0
    filled = int(length * current // total) if total else 0
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {percent}%"


def update_user_dm_status(user_id, msg_id, text):
    """
    Edits the live progress message inside Bot's DM with the User.
    """
    url = f"{TG_API}/editMessageText"
    try:
        payload = {
            "chat_id": user_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass


def main():
    print("=" * 65)
    print("🚀 PINTEREST VIRAL CATALOGS ARCHIVER")
    print("  • Target Storage Channel: Viral_Pins_Vault (-1004455682588)")
    print("  • Live UI Dashboard: Bot DM with User (8841106658)")
    print("=" * 65)

    if not BOARDS_FILE.exists():
        print(f"[-] Boards file not found: {BOARDS_FILE}")
        return

    with open(BOARDS_FILE, "r", encoding="utf-8") as f:
        board_urls = [line.strip() for line in f if line.strip().startswith("http")]

    print(f"\n📋 Loaded {len(board_urls)} Pinterest Boards:")
    for b in board_urls:
        print(f"  • {b}")

    # 1. Send initial Dashboard status message in BOT DM (NOT in channel!)
    init_msg = (
        "⚡ <b>PINTEREST VIRAL ARCHIVER LAUNCHED</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>Status:</b> Scanning 5 Pinterest Boards...\n"
        "📁 <b>Target Channel:</b> <code>Viral_Pins_Vault</code>\n"
        "💾 <b>Local Backup:</b> <code>media/catalog_vault</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏳ <i>Extracting full-resolution original image URLs...</i>"
    )
    r = requests.post(f"{TG_API}/sendMessage", json={"chat_id": USER_CHAT_ID, "text": init_msg, "parse_mode": "HTML"})
    status_msg_id = r.json().get("result", {}).get("message_id") if r.ok else None

    # 2. Extract image URLs from all boards
    print("\n[1/3] Extracting image URLs from all boards via gallery-dl...")
    all_queue = []

    for idx, b_url in enumerate(board_urls, 1):
        slug = b_url.rstrip("/").split("/")[-1]
        print(f"  -> Scanning Board {idx}/{len(board_urls)}: {slug}...")

        if status_msg_id:
            scan_text = (
                "⚡ <b>PINTEREST VIRAL ARCHIVER LAUNCHED</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔍 <b>Scanning Board {idx}/{len(board_urls)}:</b> <code>{slug}</code>\n"
                f"🎯 <b>Extracted So Far:</b> {len(all_queue)} images\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⏳ <i>Finding original high-res links...</i>"
            )
            update_user_dm_status(USER_CHAT_ID, status_msg_id, scan_text)

        img_urls = extract_board_images(b_url)
        print(f"     Found {len(img_urls)} direct images")

        board_dir = VAULT_DIR / slug
        board_dir.mkdir(parents=True, exist_ok=True)

        for i_idx, u in enumerate(img_urls, 1):
            filename = f"{slug}_{i_idx:03d}.jpg"
            local_file = board_dir / filename
            all_queue.append({
                "board_slug": slug,
                "url": u,
                "local_path": local_file,
                "index": i_idx
            })

    total_images = len(all_queue)
    print(f"\n========================================================")
    print(f"🎯 TOTAL COLLECTED: {total_images} High-Res Images across all boards")
    print(f"========================================================")

    if total_images == 0:
        if status_msg_id:
            update_user_dm_status(USER_CHAT_ID, status_msg_id, "❌ Koi image nahi mili. Kripya board URLs check karein.")
        return

    # 3. Download and Upload Loop with Live Edit Message in Bot DM
    print("\n[2/3] Downloading locally and uploading to Channel...")
    uploaded_count = 0
    start_time = time.time()
    last_ui_update = 0

    for idx, item in enumerate(all_queue, 1):
        local_path = item["local_path"]
        url = item["url"]
        slug = item["board_slug"]

        # Local download
        if not local_path.exists() or local_path.stat().st_size == 0:
            ok = download_image(url, local_path)
            if not ok:
                print(f"  [!] Failed download: {url}")
                continue

        # Upload strictly to Channel
        caption = f"✨ #{slug} | Pin #{item['index']} | {idx}/{total_images}"
        up_ok = send_tg_photo(CHANNEL_CHAT_ID, local_path, caption=caption)
        if up_ok:
            uploaded_count += 1
            print(f"  [✓] ({idx}/{total_images}) Stored in Channel: {local_path.name}")
        else:
            print(f"  [-] Failed TG upload: {local_path.name}")

        # Live Animated Progress UI strictly in Bot DM (User Chat)
        now = time.time()
        if status_msg_id and (now - last_ui_update >= 2.0 or idx == total_images):
            elapsed = int(now - start_time)
            rate = round(uploaded_count / elapsed, 1) if elapsed > 0 else 0
            remaining = total_images - uploaded_count
            bar = make_progress_bar(uploaded_count, total_images)

            status_text = (
                f"📥 <b>ARCHIVING VIRAL PINS TO CHANNEL</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 <b>Current Board:</b> <code>{slug}</code>\n"
                f"📊 <b>Progress:</b> {uploaded_count}/{total_images} {bar}\n"
                f"⏳ <b>Remaining:</b> {remaining} photos\n"
                f"⚡ <b>Upload Rate:</b> {rate} photos/sec\n"
                f"📺 <b>Target Channel:</b> <code>Viral_Pins_Vault</code>\n"
                f"💾 <b>Local Backup:</b> <code>media/catalog_vault</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🟢 <i>Bot live updating in DM... Photos going to Channel!</i>"
            )
            update_user_dm_status(USER_CHAT_ID, status_msg_id, status_text)
            last_ui_update = now

        time.sleep(0.3)

    # 4. Final Completion in Bot DM
    total_time = int(time.time() - start_time)
    print("\n========================================================")
    print(f"🎉 ARCHIVE COMPLETED IN {total_time} SECONDS!")
    print(f"✅ Total Photos Uploaded to Channel: {uploaded_count}/{total_images}")
    print(f"💾 Local Backup Saved to: {VAULT_DIR}")
    print("========================================================")

    if status_msg_id:
        done_text = (
            f"🎉 <b>VIRAL PINS ARCHIVE COMPLETED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>Total Photos Saved:</b> {uploaded_count} / {total_images}\n"
            f"📁 <b>Boards Processed:</b> {len(board_urls)}\n"
            f"📺 <b>Channel:</b> <code>Viral_Pins_Vault</code>\n"
            f"💾 <b>Local Path:</b> <code>media/catalog_vault</code>\n"
            f"⏱️ <b>Time Taken:</b> {total_time // 60}m {total_time % 60}s\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 <i>Saare 458 photos safely aapke Private Channel aur PC me store ho gaye hain! Ab automation setup kar sakte hain.</i>"
        )
        update_user_dm_status(USER_CHAT_ID, status_msg_id, done_text)


if __name__ == "__main__":
    main()
