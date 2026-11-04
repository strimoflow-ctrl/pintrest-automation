import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Force UTF-8 for console output on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent

def run_web_server():
    print("\n🚀 Starting NOX PFP Web App & Monetag Landing Page on http://localhost:8000...")
    subprocess.run(["uvicorn", "web_app.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])

def run_scraper(limit: int = 50):
    print(f"\n📥 Running Telegram Scraper for 'Nox_oo1' (Limit: {limit})...")
    import telegram_scraper
    asyncio.run(telegram_scraper.scrape_channel(limit=limit))

def run_poster():
    print("\n📌 Starting Pinterest Auto-Poster Worker...")
    import pinterest_poster
    pinterest_poster.start_posting_worker()

def show_stats():
    import database
    database.init_db()
    stats = database.get_stats()
    print("\n================ SYSTEM STATISTICS ================")
    print(f"📦 Total Scraped Media:     {stats['total_media']}")
    print(f"📌 Posted to Pinterest:     {stats['posted_pins']}")
    print(f"⏳ Pending Pins to Post:    {stats['pending_pins']}")
    print(f"👁️ Total Landing Page Views: {stats['total_views']}")
    print(f"⬇️ Total Downloads Triggered:{stats['total_downloads']}")
    print("===================================================\n")

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "server":
            run_web_server()
        elif cmd == "scrape":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            run_scraper(limit)
        elif cmd == "post":
            run_poster()
        elif cmd == "stats":
            show_stats()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python main.py [server|scrape|post|stats]")
        return

    while True:
        print("\n=================================================")
        print("    ⚡ NOX PFP PINTEREST & MONETAG AUTOMATION   ")
        print("=================================================")
        print("1. 🚀 Start Web Server (Landing Page + Monetag Ads)")
        print("2. 📥 Scrape Telegram Channel (Photos, Videos, Docs)")
        print("3. 📌 Start Pinterest Auto-Poster")
        print("4. 📊 View Database & Traffic Stats")
        print("5. 🚪 Exit")
        choice = input("\nEnter choice [1-5]: ").strip()

        if choice == "1":
            run_web_server()
        elif choice == "2":
            lim = input("Enter how many posts to scrape [default: 50]: ").strip()
            limit = int(lim) if lim.isdigit() else 50
            run_scraper(limit)
        elif choice == "3":
            run_poster()
        elif choice == "4":
            show_stats()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, please select 1-5.")

if __name__ == "__main__":
    main()
