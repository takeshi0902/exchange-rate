import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL    = os.getenv("DISCORD_WEBHOOK_URL", "")
DATABASE_PATH          = os.getenv("DATABASE_PATH", "rates.db")
SCRAPE_INTERVAL_HOURS  = int(os.getenv("SCRAPE_INTERVAL_HOURS", "1"))
CORS_ORIGINS           = [s.strip() for s in os.getenv("CORS_ORIGINS", "*").split(",")]

# 爬蟲共用 HTTP headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_TIMEOUT = 15   # seconds
