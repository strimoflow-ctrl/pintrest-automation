import sys
import asyncio
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import config
import database
import nail_engine

app = FastAPI(title="GlamNails Modern Lookbook Hub")

DIST_DIR = BASE_DIR / "glamnails_site" / "dist"
ASSETS_DIR = DIST_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

app.mount("/media", StaticFiles(directory=str(config.MEDIA_DIR)), name="media")

async def background_pin_poster():
    """
    Automated Background Worker:
    - Waits 5 seconds after server boot/restart
    - Immediately posts 1 fresh nail pin to Pinterest for instant verification
    - Then continues posting on schedule every POST_INTERVAL_MINUTES (default 35 mins)
    """
    await asyncio.sleep(5)
    print("\n[🚀] Server boot/restart detected! Immediately posting first pin for instant test...")
    
    interval_seconds = max(config.POST_INTERVAL_MINUTES * 60, 600)
    
    while True:
        try:
            print(f"[*] Posting nail collection pin to Pinterest...")
            success = nail_engine.post_next_nail_pin()
            if success:
                print(f"[✓] Pin successfully posted! Next scheduled post in {config.POST_INTERVAL_MINUTES} minutes.")
            else:
                print(f"[!] No pin was posted. Will check again in {config.POST_INTERVAL_MINUTES} minutes.")
        except Exception as e:
            print(f"[-] Background worker error: {e}")
            
        await asyncio.sleep(interval_seconds)

@app.on_event("startup")
async def on_startup():
    print("[*] Initializing GlamNails Modern Engine...")
    database.populate_catalogs_if_empty()
    stats = database.get_stats()
    print(f"[✓] Database ready: {stats['total_tutorials']} lookbooks loaded ({stats['posted_pins']} posted)")
    asyncio.create_task(background_pin_poster())

@app.get("/sw.js")
async def get_service_worker():
    """Serves the Monetag push notifications service worker."""
    sw_file = BASE_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(str(sw_file), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Service worker not found")

@app.get("/")
@app.get("/nail/{slug}")
@app.get("/lookbook/{slug}")
async def serve_react_app(slug: str = None):
    """Serves the modern React SPA lookbook."""
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(status_code=404, detail="Frontend build not found")

@app.get("/api/stats")
async def get_stats():
    """Returns database status and stats."""
    return JSONResponse(database.get_stats())
