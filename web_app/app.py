import os
import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add parent directory to sys.path so we can import config & database
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import config
import database

app = FastAPI(title="NOX PFP Landing & Monetag Hub")

# Mount static and media directories
STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/media", StaticFiles(directory=str(config.MEDIA_DIR)), name="media")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

async def background_automation_loop():
    """
    Background worker that runs inside Botkeep:
    - Auto-posts pins to Pinterest at safe intervals (every 35 mins)
    - Automatically scrapes new wallpapers from Nox_oo1 when queue gets low
    - Sends Telegram notification on each post
    """
    import asyncio
    from pinterest_poster import post_single_item
    from telegram_scraper import scrape_telegram_web
    
    # Wait 15 seconds after server boot
    await asyncio.sleep(15)
    print("[*] Botkeep Automation Background Worker Active!")
    
    while True:
        try:
            item = database.get_next_unposted_item()
            if item:
                print(f"[*] Auto-posting queued item #{item['id']} to Pinterest...")
                post_single_item(item)
            else:
                print("[*] Queue empty. Auto-scraping new batch from Telegram...")
                scrape_telegram_web(max_items=25)
        except Exception as e:
            print(f"[-] Background worker error: {e}")
            
        sleep_secs = max(config.POST_INTERVAL_MINUTES * 60, 600)
        print(f"[*] Sleeping {config.POST_INTERVAL_MINUTES} minutes until next scheduled pin...")
        await asyncio.sleep(sleep_secs)

@app.on_event("startup")
def startup_event():
    import asyncio
    database.init_db()
    asyncio.create_task(background_automation_loop())

# ================= UPTIME PING & HEALTH CHECK =================
@app.head("/")
async def head_root():
    """Handles HEAD requests for Uptime monitors (UptimeRobot, BetterUptime, etc.)"""
    return HTMLResponse(content="", status_code=200)

@app.get("/sw.js")
async def service_worker():
    """Serves Monetag Push Notification Service Worker at root /sw.js"""
    sw_file = BASE_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(
            path=str(sw_file),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"}
        )
    raise HTTPException(status_code=404, detail="sw.js not found")

@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint to keep Render server awake 24/7"""
    stats = database.get_stats()
    return {
        "status": "healthy",
        "service": "NOX PFP Pinterest Automation",
        "stats": stats
    }

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    items = database.get_recent_items(limit=36)
    stats = database.get_stats()
    return templates.TemplateResponse(request, "index.html", {
        "items": items,
        "stats": stats,
        "monetag_script_tag": config.MONETAG_SCRIPT_TAG
    })

@app.get("/p/{item_id}", response_class=HTMLResponse)
async def view_pin_page(request: Request, item_id: int):
    item = database.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Wallpapers/PFP not found")
        
    # Increment views counter
    database.increment_views(item_id)
    
    return templates.TemplateResponse(request, "pin_view.html", {
        "item": item,
        "site_url": config.SITE_BASE_URL,
        "timer_seconds": config.TIMER_SECONDS,
        "monetag_direct_link": config.MONETAG_DIRECT_LINK,
        "monetag_script_tag": config.MONETAG_SCRIPT_TAG,
        "now_year": datetime.now().year
    })

@app.get("/download/{item_id}")
async def download_media(item_id: int):
    item = database.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Increment downloads counter
    database.increment_downloads(item_id)

    file_path = config.MEDIA_DIR / item["file_path"]
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            filename=item["original_filename"] or file_path.name,
            media_type="application/octet-stream"
        )
    elif item.get("cdn_url"):
        # Zero-storage fallback: redirect directly to Telegram high-speed CDN
        return RedirectResponse(url=item["cdn_url"])
    else:
        raise HTTPException(status_code=404, detail="File missing on server")

@app.get("/api/stats")
async def api_stats():
    return database.get_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
