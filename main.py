import sys
import argparse
import uvicorn
from pathlib import Path

# Force UTF-8 for console output on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import database
import nail_engine

def run_server():
    """Runs the FastAPI server with automated background poster."""
    print("==================================================")
    print("💅 GLAMNAILS PINTEREST & MONETAG AUTOMATION")
    print(f"🌐 Site URL: {config.SITE_BASE_URL}")
    print(f"⏱  Post Interval: Every {config.POST_INTERVAL_MINUTES} mins")
    print("==================================================")
    
    # Initialize DB
    database.populate_catalogs_if_empty()
    stats = database.get_stats()
    print(f"[✓] Available Inventory: {stats['total_tutorials']} Tutorials ({stats['posted_pins']} Posted)")
    
    uvicorn.run("web_app.app:app", host="0.0.0.0", port=8000, reload=False)

def post_single():
    """Test function to post 1 single pin immediately."""
    print("[*] Testing immediate pin posting...")
    database.populate_catalogs_if_empty()
    success = nail_engine.post_next_nail_pin()
    if success:
        print("[✓] Pin posted successfully!")
    else:
        print("[-] Pin posting failed or queue is empty.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GlamNails Pinterest Automation")
    parser.add_argument("--post-one", action="store_true", help="Post a single pin right now and exit")
    parser.add_argument("--stats", action="store_true", help="Print current database stats and exit")
    args = parser.parse_args()

    if args.post_one:
        post_single()
    elif args.stats:
        database.populate_catalogs_if_empty()
        print(database.get_stats())
    else:
        run_server()
