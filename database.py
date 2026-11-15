import sqlite3
import datetime
from pathlib import Path
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_msg_id INTEGER UNIQUE,
        media_type TEXT NOT NULL,          -- 'photo', 'video', 'document'
        file_path TEXT NOT NULL,           -- relative path inside media/
        cdn_url TEXT,                      -- direct Telegram CDN link for zero storage
        original_filename TEXT,
        file_size INTEGER DEFAULT 0,
        caption TEXT,
        seo_title TEXT,
        seo_description TEXT,
        seo_tags TEXT,
        pinterest_pin_id TEXT,
        is_posted INTEGER DEFAULT 0,       -- 0: pending, 1: posted, -1: error
        post_error TEXT,
        posted_at TIMESTAMP,
        views_count INTEGER DEFAULT 0,
        downloads_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Add cdn_url column if table was created previously without it
    try:
        cursor.execute("ALTER TABLE media_items ADD COLUMN cdn_url TEXT;")
    except Exception:
        pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_id ON media_items(telegram_msg_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_posted ON media_items(is_posted);")

    # Table for Bot 2 (Viral 18+ Clickbait Engine)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viral_media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT UNIQUE,
        board_slug TEXT,
        target_board_id TEXT,
        file_path TEXT NOT NULL,
        seo_title TEXT,
        seo_description TEXT,
        pinterest_pin_id TEXT,
        is_posted INTEGER DEFAULT 0,
        post_error TEXT,
        posted_at TIMESTAMP,
        views_count INTEGER DEFAULT 0,
        unlocks_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viral_source ON viral_media_items(source_url);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viral_posted ON viral_media_items(is_posted);")
    conn.commit()
    conn.close()

def insert_media_item(msg_id, media_type, file_path, original_filename, file_size, caption, title, description, tags, cdn_url=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO media_items (
            telegram_msg_id, media_type, file_path, original_filename, 
            file_size, caption, seo_title, seo_description, seo_tags, cdn_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, media_type, file_path, original_filename, file_size, caption, title, description, tags, cdn_url))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_item_by_id(item_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM media_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_next_unposted_item():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM media_items WHERE is_posted = 0 ORDER BY id ASC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def mark_item_posted(item_id, pin_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE media_items 
        SET is_posted = 1, pinterest_pin_id = ?, posted_at = CURRENT_TIMESTAMP, post_error = NULL
        WHERE id = ?
        """, (pin_id, item_id))
        conn.commit()
    finally:
        conn.close()

def mark_item_error(item_id, error_msg):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE media_items 
        SET is_posted = -1, post_error = ?
        WHERE id = ?
        """, (str(error_msg), item_id))
        conn.commit()
    finally:
        conn.close()

def increment_views(item_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE media_items SET views_count = views_count + 1 WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()

def increment_downloads(item_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE media_items SET downloads_count = downloads_count + 1 WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()

def get_recent_items(limit=30, offset=0):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM media_items ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM media_items")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM media_items WHERE is_posted = 1")
        posted = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(views_count), SUM(downloads_count) FROM media_items")
        views, downloads = cursor.fetchone()
        return {
            "total_media": total,
            "posted_pins": posted,
            "pending_pins": total - posted,
            "total_views": views or 0,
            "total_downloads": downloads or 0
        }
    finally:
        conn.close()

# =============================================================
# VIRAL MEDIA FUNCTIONS (BOT 2)
# =============================================================
def insert_viral_item(source_url, board_slug, file_path, title, description):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO viral_media_items (
            source_url, board_slug, file_path, seo_title, seo_description
        ) VALUES (?, ?, ?, ?, ?)
        """, (source_url, board_slug, file_path, title, description))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def is_viral_source_scraped(source_url):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM viral_media_items WHERE source_url = ?", (source_url,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def get_viral_item_by_id(item_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM viral_media_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_next_unposted_viral_item():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM viral_media_items WHERE is_posted = 0 ORDER BY id ASC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def mark_viral_item_posted(item_id, pin_id, target_board_id=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE viral_media_items 
        SET is_posted = 1, pinterest_pin_id = ?, target_board_id = ?, posted_at = CURRENT_TIMESTAMP, post_error = NULL
        WHERE id = ?
        """, (pin_id, target_board_id, item_id))
        conn.commit()
    finally:
        conn.close()

def mark_viral_item_error(item_id, error_msg):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE viral_media_items 
        SET is_posted = -1, post_error = ? 
        WHERE id = ?
        """, (error_msg, item_id))
        conn.commit()
    finally:
        conn.close()

def increment_viral_views(item_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE viral_media_items SET views_count = views_count + 1 WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()

def increment_viral_unlocks(item_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE viral_media_items SET unlocks_count = unlocks_count + 1 WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()

def get_viral_stats():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM viral_media_items")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM viral_media_items WHERE is_posted = 1")
        posted = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(views_count), SUM(unlocks_count) FROM viral_media_items")
        views, unlocks = cursor.fetchone()
        return {
            "total_viral_items": total,
            "posted_viral_pins": posted,
            "pending_viral_pins": total - posted,
            "total_views": views or 0,
            "total_unlocks": unlocks or 0
        }
    finally:
        conn.close()

# ================= RESILIENT ZERO-404 RESOLVERS =================
AESTHETIC_WALLPAPERS = [
    "https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1563089145-599997674d42?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1534447677768-be436bb09401?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=1200&auto=format&fit=crop"
]

def get_safe_pin_item(item_id: int):
    """
    Guarantees that NO pin URL (/p/{id}) ever returns a 404 error!
    1. Checks local SQLite DB.
    2. If missing on Render container, checks permanent Firebase posted_pins cache.
    3. If completely new, dynamically synthesizes a high-res 4K aesthetic item.
    """
    # 1. Check local DB
    item = get_item_by_id(item_id)
    if item:
        return item

    # 2. Check Firebase posted pins
    import firebase_db
    fb_pin = firebase_db.get_posted_pin_by_url_id(item_id)
    title = fb_pin.get("title") if fb_pin else "✨ 4K Ultra HD Aesthetic Wallpaper & PFP (Free Download)"

    img_url = AESTHETIC_WALLPAPERS[abs(int(item_id)) % len(AESTHETIC_WALLPAPERS)]

    return {
        "id": item_id,
        "seo_title": title,
        "seo_description": "Free Ultra HD 4K Aesthetic Wallpaper & PFP. Download original uncompressed graphics, high dynamic range, and crisp colors. Click the link to download now!",
        "media_type": "photo",
        "file_path": "",
        "cdn_url": img_url,
        "original_filename": f"aesthetic_wallpaper_{item_id}.jpg"
    }

def get_safe_viral_item(item_id: int):
    """
    Guarantees that NO viral video pin (/v/{id}) ever returns a 404 error!
    """
    item = get_viral_item_by_id(item_id)
    if item:
        return item

    item = get_item_by_id(item_id)
    if item:
        return item

    # Check any available viral item in SQLite
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM viral_media_items ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["id"] = item_id
            return d
    except Exception:
        pass
    finally:
        conn.close()

    thumb_url = AESTHETIC_WALLPAPERS[abs(int(item_id)) % len(AESTHETIC_WALLPAPERS)]
    return {
        "id": item_id,
        "seo_title": "Tap Visit Site to Watch Full Video 🔞👀",
        "seo_description": "Exclusive private 1080p stream unlocked on our portal. Click Visit Site to complete quick access and watch the full video on Telegram! 🔞✨",
        "media_type": "video",
        "file_path": "",
        "cdn_url": thumb_url
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)

