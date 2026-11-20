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
    """Initializes the SQLite database with the nail_tutorials schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
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
            tutorial_steps_json TEXT,
            pinterest_title TEXT,
            pinterest_description TEXT,
            pinterest_tags_json TEXT,
            is_posted INTEGER DEFAULT 0,
            pinterest_pin_id TEXT,
            posted_at TEXT,
            views_count INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_posted ON nail_tutorials (is_posted)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_slug ON nail_tutorials (slug)")
    conn.commit()
    conn.close()

def populate_catalogs_if_empty():
    """Loads all parsed nail tutorials from JSON catalogs into the database."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM nail_tutorials")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return count
    
    catalogs_dir = config.NAIL_CATALOGS_DIR
    if not catalogs_dir.exists():
        conn.close()
        return 0
    
    inserted = 0
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    for json_file in catalogs_dir.glob("*_catalog.json"):
        if "all_nail_catalogs_summary" in json_file.name:
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            posts = data.get("posts", [])
            for p in posts:
                tutorial_id = p.get("id") or p.get("slug")
                slug = p.get("slug")
                if not slug or not p.get("featured_image"):
                    continue
                
                seo = p.get("pinterest_seo", {})
                title = p.get("title", "Aesthetic Nail Art Tutorial")
                # Clean up title if it contains outfit or non-nail word
                if "nail" not in title.lower():
                    title = f"{title} Nail Art Design"
                
                pin_title = seo.get("title") or f"{title} | Easy Step-by-Step DIY Tutorial ✨"
                pin_desc = seo.get("description") or f"Easy step-by-step DIY tutorial for {title}. Tap visit for the full guide and color shades! 💅"
                
                cursor.execute("""
                    INSERT OR IGNORE INTO nail_tutorials (
                        tutorial_id, slug, title, category, source_site, source_url,
                        featured_image, all_images_json, image_count, tutorial_steps_json,
                        pinterest_title, pinterest_description, pinterest_tags_json,
                        is_posted, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (
                    tutorial_id,
                    slug,
                    title,
                    p.get("category", "Nail Art DIY"),
                    p.get("source_site", "Beauty Hub"),
                    p.get("source_url", ""),
                    p.get("featured_image"),
                    json.dumps(p.get("all_images", [])),
                    p.get("image_count", 0),
                    json.dumps(p.get("tutorial_steps", [])),
                    pin_title,
                    pin_desc,
                    json.dumps(seo.get("tags", ["#nailart", "#diynails", "#acrylicnails"])),
                    now
                ))
                inserted += 1
        except Exception as e:
            print(f"[-] Error loading {json_file.name}: {e}")
            
    conn.commit()
    conn.close()
    return inserted

def get_next_unposted_tutorial() -> Optional[Dict[str, Any]]:
    """Fetches the next unposted nail tutorial from the queue."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM nail_tutorials 
        WHERE is_posted = 0 
        ORDER BY id ASC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["all_images"] = json.loads(d.get("all_images_json") or "[]")
        d["tutorial_steps"] = json.loads(d.get("tutorial_steps_json") or "[]")
        d["pinterest_tags"] = json.loads(d.get("pinterest_tags_json") or "[]")
        return d
    return None

def mark_tutorial_posted(tutorial_id: str, pin_id: Optional[str] = None):
    """Marks a tutorial as posted to Pinterest."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE nail_tutorials 
        SET is_posted = 1, pinterest_pin_id = ?, posted_at = ? 
        WHERE tutorial_id = ?
    """, (pin_id, now, tutorial_id))
    conn.commit()
    conn.close()

def get_tutorial_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Fetches tutorial details by slug for the web app landing page."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nail_tutorials WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["all_images"] = json.loads(d.get("all_images_json") or "[]")
        d["tutorial_steps"] = json.loads(d.get("tutorial_steps_json") or "[]")
        d["pinterest_tags"] = json.loads(d.get("pinterest_tags_json") or "[]")
        return d
    return None

def get_recent_tutorials(limit: int = 24, offset: int = 0) -> List[Dict[str, Any]]:
    """Gets list of tutorials for the homepage gallery."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, slug, title, category, featured_image, image_count, views_count, is_posted 
        FROM nail_tutorials 
        ORDER BY id ASC 
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def increment_views(slug: str):
    """Increments the view count for a tutorial."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE nail_tutorials SET views_count = views_count + 1 WHERE slug = ?", (slug,))
    conn.commit()
    conn.close()

def get_stats() -> Dict[str, Any]:
    """Returns total tutorials, posted count, and unposted count."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM nail_tutorials")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM nail_tutorials WHERE is_posted = 1")
    posted = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(views_count), 0) FROM nail_tutorials")
    views = cursor.fetchone()[0]
    conn.close()
    return {
        "total_tutorials": total,
        "posted_pins": posted,
        "unposted_pins": total - posted,
        "total_views": views
    }
