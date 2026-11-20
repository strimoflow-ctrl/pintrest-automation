import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import config

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite tables for collections and individual image pin queue."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Collections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nail_tutorials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tutorial_id TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            category TEXT,
            source_site TEXT,
            source_url TEXT,
            featured_image TEXT NOT NULL,
            all_images_json TEXT,
            image_count INTEGER DEFAULT 0,
            views_count INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # Per-image pin queue table (every single image is a pin)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nail_pins_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin_key TEXT UNIQUE NOT NULL,
            collection_slug TEXT NOT NULL,
            collection_title TEXT NOT NULL,
            image_url TEXT NOT NULL,
            image_index INTEGER NOT NULL,
            pin_title TEXT NOT NULL,
            pin_description TEXT NOT NULL,
            is_posted INTEGER DEFAULT 0,
            pinterest_pin_id TEXT,
            posted_at TEXT
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pins_posted ON nail_pins_queue (is_posted)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pins_slug ON nail_pins_queue (collection_slug)")
    conn.commit()
    conn.close()

def populate_catalogs_if_empty():
    """Loads all genuine nail lookbooks and queues every image as an individual pin."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM nail_pins_queue")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return count
    
    clean_json_file = config.NAIL_CATALOGS_DIR / "genuine_nail_collections.json"
    if not clean_json_file.exists():
        conn.close()
        return 0
    
    inserted_collections = 0
    inserted_pins = 0
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(clean_json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        collections = data.get("collections", [])
        
        for c in collections:
            tutorial_id = c.get("id") or c.get("slug")
            slug = c.get("slug")
            title = c.get("title")
            featured_img = c.get("featured_image")
            images = c.get("images", [])
            image_count = c.get("image_count", len(images))
            
            if not slug or not featured_img or not title or len(images) == 0:
                continue
                
            cursor.execute("""
                INSERT OR IGNORE INTO nail_tutorials (
                    tutorial_id, slug, title, category, source_site, source_url,
                    featured_image, all_images_json, image_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tutorial_id,
                slug,
                title,
                "Aesthetic Nail Art",
                c.get("source_site", "GlamNails Studio"),
                c.get("source_url", ""),
                featured_img,
                json.dumps(images),
                image_count,
                now
            ))
            inserted_collections += 1
            
            # Queue EVERY SINGLE IMAGE as an individual pin pointing to this collection!
            for idx, img_url in enumerate(images):
                if not img_url or not img_url.startswith("http"):
                    continue
                pin_key = f"{slug}_{idx+1}"
                pin_title = f"{title} • Look #{idx+1} | Aesthetic Nails ✨"
                pin_desc = (
                    f"Looking for aesthetic nail inspiration? Check out this stunning {title} (Design #{idx+1}). "
                    f"Tap visit to view the complete lookbook and all design angles! 💅 #nailart #nails #diynails #nailinspo"
                )
                cursor.execute("""
                    INSERT OR IGNORE INTO nail_pins_queue (
                        pin_key, collection_slug, collection_title, image_url,
                        image_index, pin_title, pin_description, is_posted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    pin_key,
                    slug,
                    title,
                    img_url,
                    idx + 1,
                    pin_title,
                    pin_desc
                ))
                inserted_pins += 1
                
    except Exception as e:
        print(f"[-] Error loading collections: {e}")
        
    conn.commit()
    conn.close()
    return inserted_pins

def get_next_unposted_pin() -> Optional[Dict[str, Any]]:
    """Fetches the next unposted image pin from the queue."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM nail_pins_queue 
        WHERE is_posted = 0 
        ORDER BY id ASC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def mark_pin_posted(pin_key: str, pinterest_pin_id: Optional[str] = None):
    """Marks an image pin as posted to Pinterest."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE nail_pins_queue 
        SET is_posted = 1, pinterest_pin_id = ?, posted_at = ? 
        WHERE pin_key = ?
    """, (pinterest_pin_id, now, pin_key))
    conn.commit()
    conn.close()

def get_tutorial_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Fetches collection details by slug."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nail_tutorials WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["images"] = json.loads(d.get("all_images_json") or "[]")
        return d
    return None

def increment_views(slug: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE nail_tutorials SET views_count = views_count + 1 WHERE slug = ?", (slug,))
    conn.commit()
    conn.close()

def get_stats() -> Dict[str, Any]:
    """Returns database status and stats."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM nail_tutorials")
    total_collections = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM nail_pins_queue")
    total_pins = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM nail_pins_queue WHERE is_posted = 1")
    posted_pins = cursor.fetchone()[0]
    conn.close()
    return {
        "total_collections": total_collections,
        "total_tutorials": total_collections,
        "total_pins": total_pins,
        "posted_pins": posted_pins,
        "unposted_pins": total_pins - posted_pins
    }
