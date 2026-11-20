import sys
import asyncio
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import config
import database
import nail_engine

app = FastAPI(title="GlamNails DIY & Monetag Hub")

# Mount static and media directories
STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/media", StaticFiles(directory=str(config.MEDIA_DIR)), name="media")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

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
            print(f"[*] Posting nail tutorial to Pinterest...")
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
    # Initialize DB and populate 641 tutorials from JSON catalogs if first run
    print("[*] Initializing Nail Tutorials Database...")
    inserted = database.populate_catalogs_if_empty()
    stats = database.get_stats()
    print(f"[✓] Database ready: {stats['total_tutorials']} tutorials loaded ({stats['posted_pins']} posted)")
    
    # Start auto-posting loop as non-blocking background task
    asyncio.create_task(background_pin_poster())

@app.get("/sw.js")
async def get_service_worker():
    """Serves the Monetag push notifications service worker."""
    sw_file = BASE_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(str(sw_file), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Service worker not found")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage gallery of trending nail tutorials."""
    tutorials = database.get_recent_tutorials(limit=36)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tutorials": tutorials,
        "monetag_script_tag": config.MONETAG_SCRIPT_TAG,
        "monetag_direct_link": config.MONETAG_DIRECT_LINK
    })

@app.get("/nail/{slug}", response_class=HTMLResponse)
async def view_nail_tutorial(request: Request, slug: str):
    """Destination landing page for Pinterest pins."""
    tutorial = database.get_tutorial_by_slug(slug)
    if not tutorial:
        raise HTTPException(status_code=404, detail="Nail tutorial not found")
        
    database.increment_views(slug)
    
    return templates.TemplateResponse("article.html", {
        "request": request,
        "tutorial": tutorial,
        "monetag_script_tag": config.MONETAG_SCRIPT_TAG,
        "monetag_direct_link": config.MONETAG_DIRECT_LINK
    })

@app.get("/api/stats")
async def get_stats():
    """Returns database status and stats."""
    return JSONResponse(database.get_stats())
