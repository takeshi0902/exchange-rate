"""
FastAPI 主程式
─────────────────────────────────────────────────────
Endpoints:
  GET /api/rates           → 所有銀行最新匯率
  GET /api/rates/history   → 歷史走勢，各銀行平均（?currency=JPY&days=30）
  GET /api/usd-jpy         → USD/JPY 參考匯率
  GET /api/status          → 爬蟲健康狀態
  GET /healthz             → Render health-check
"""

import hashlib
import json as _json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import database as DB
import scheduler as SC
from scrapers import unavailable_banks
from config import CORS_ORIGINS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)
TZ8 = timezone(timedelta(hours=8))

# ── Lifespan ─────────────────────────────────────────────────────────────────

_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    DB.init_db()
    _scheduler = SC.start(run_now=True)
    yield
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("排程器已關閉")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="台灣銀行匯率比較 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/healthz")
def healthz():
    return {"status": "ok", "ts": datetime.now(TZ8).isoformat()}


@app.get("/api/rates")
def get_rates():
    """
    回傳所有銀行最新匯率。
    回應包含 checksum 欄位（SHA256 of rates array），前端可用於完整性驗證。
    Cache-Control: max-age=3600，CDN / 瀏覽器快取一小時。
    """
    rates = DB.get_latest_rates()
    if not rates:
        raise HTTPException(status_code=503, detail="尚無匯率資料，請稍後再試")
    now = datetime.now(TZ8).isoformat()

    # Compute checksum: SHA256 of rates array (sort_keys for determinism)
    rates_str = _json.dumps(rates, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    checksum  = "sha256:" + hashlib.sha256(rates_str.encode("utf-8")).hexdigest()

    return JSONResponse(
        # unavailable：暫停中的銀行與原因，前端可標示「暫時無法取得」
        # usd_jpy：三角換匯頁直接讀取，省一次請求
        content={"checksum": checksum, "updated_at": now, "rates": rates,
                 "usd_jpy": DB.get_usd_jpy(), "unavailable": unavailable_banks()},
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/rates/history")
def get_history(
    currency: str = Query("JPY", pattern="^[A-Z]{3}$"),
    days: int = Query(30, ge=1, le=365),
):
    """
    回傳各銀行即期匯率的每日平均，每日一筆。
    格式：{"currency": "JPY", "days": 30, "data": [{"date": "...", "spot_buy": ..., "spot_sell": ..., "banks": 11}, ...]}
    """
    data = DB.get_history(currency.upper(), days)
    return {"currency": currency.upper(), "days": days, "data": data}


@app.get("/api/usd-jpy")
def get_usd_jpy():
    """回傳 USD/JPY 參考匯率（由各銀行即期賣出平均推算）。"""
    rate = DB.get_usd_jpy()
    if rate is None:
        raise HTTPException(status_code=503, detail="USD/JPY 資料不足")
    return {"usd_jpy": rate, "note": "由各銀行 USD、JPY 即期賣出平均推算，僅供參考"}


@app.get("/api/status")
def get_status():
    """
    回傳各銀行爬蟲最後一次的狀態。
    格式：{"banks": [{"bank_code": ..., "status": ..., "message": ..., "scraped_at": ...}, ...]}
    """
    sql = """
        SELECT bank_code, status, message, scraped_at
        FROM scrape_log
        WHERE id IN (
            SELECT MAX(id) FROM scrape_log GROUP BY bank_code
        )
        ORDER BY bank_code
    """
    import sqlite3
    from pathlib import Path
    from config import DATABASE_PATH

    if not Path(DATABASE_PATH).exists():
        return {"banks": [], "unavailable": unavailable_banks()}

    con = sqlite3.connect(DATABASE_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(sql).fetchall()
    con.close()
    return {"banks": [dict(r) for r in rows], "unavailable": unavailable_banks()}
