"""
SQLite 資料庫操作模組
─────────────────────────────────────────────────────
rates      — 每次爬蟲的匯率快照（保留歷史）
scrape_log — 每次爬蟲的成功 / 失敗記錄
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from config import DATABASE_PATH

log = logging.getLogger(__name__)

TZ8 = timezone(timedelta(hours=8))


# ── Schema ──────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS rates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_code   TEXT    NOT NULL,
    bank_name   TEXT    NOT NULL,
    currency    TEXT    NOT NULL,
    spot_buy    REAL,
    spot_sell   REAL,
    cash_buy    REAL,
    cash_sell   REAL,
    scraped_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rates_lookup
    ON rates(bank_code, currency, scraped_at DESC);

CREATE TABLE IF NOT EXISTS scrape_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_code   TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    message     TEXT,
    scraped_at  TEXT    NOT NULL
);
"""


# ── Connection ───────────────────────────────────────────────────────────────

@contextmanager
def _conn():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATABASE_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript(_DDL)
    log.info(f"資料庫初始化完成：{DATABASE_PATH}")


# ── Write ────────────────────────────────────────────────────────────────────

def save_rates(bank_data: dict):
    """
    bank_data 格式（scrapers/base.py 的 fetch() 回傳）：
    {
      "bank_code": "MEGA", "bank_name": "兆豐銀行",
      "rates": {"JPY": {"spot_buy": 0.2031, "spot_sell": 0.2072, "cash_buy": ..., "cash_sell": ...}, ...}
    }
    """
    now = datetime.now(TZ8).isoformat()
    rows = [
        (
            bank_data["bank_code"], bank_data["bank_name"], currency,
            r.get("spot_buy"), r.get("spot_sell"),
            r.get("cash_buy"), r.get("cash_sell"),
            now,
        )
        for currency, r in sorted(bank_data["rates"].items())
    ]
    with _conn() as con:
        con.executemany(
            "INSERT INTO rates (bank_code,bank_name,currency,spot_buy,spot_sell,cash_buy,cash_sell,scraped_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
    log.info(f"已儲存 {bank_data['bank_code']} {len(rows)} 個幣別")


def log_scrape(bank_code: str, status: str, message: str = ""):
    now = datetime.now(TZ8).isoformat()
    with _conn() as con:
        con.execute(
            "INSERT INTO scrape_log (bank_code,status,message,scraped_at) VALUES (?,?,?,?)",
            (bank_code, status, message, now),
        )


# ── Read ─────────────────────────────────────────────────────────────────────

def get_latest_rates() -> list[dict]:
    """
    每家銀行 + 每個幣別，各取最新一筆。
    回傳格式符合前端 /api/rates 期望的 rates 陣列。
    """
    sql = """
        SELECT r.*
        FROM rates r
        INNER JOIN (
            SELECT bank_code, currency, MAX(scraped_at) AS latest
            FROM rates
            GROUP BY bank_code, currency
        ) sub ON r.bank_code = sub.bank_code
              AND r.currency  = sub.currency
              AND r.scraped_at = sub.latest
        ORDER BY r.bank_code, r.currency
    """
    with _conn() as con:
        rows = con.execute(sql).fetchall()

    # Group by bank
    banks: dict[str, dict] = {}
    for row in rows:
        code = row["bank_code"]
        if code not in banks:
            # 前端以 b.bank 顯示銀行名稱
            banks[code] = {"bank_code": code, "bank_name": row["bank_name"], "bank": row["bank_name"]}
        banks[code][row["currency"]] = {
            "spot_buy":  row["spot_buy"],
            "spot_sell": row["spot_sell"],
            "cash_buy":  row["cash_buy"],
            "cash_sell": row["cash_sell"],
            "updated_at": row["scraped_at"],
        }
    return list(banks.values())


def get_history(currency: str, days: int = 365) -> list[dict]:
    """
    各銀行即期匯率的每日平均（台灣銀行暫停後改用全體平均，單一銀行失效也不影響走勢）。
    每個交易日一筆。
    """
    sql = """
        SELECT DATE(scraped_at, '+8 hours') AS date,   -- scraped_at 帶 +08:00，SQLite 會先轉 UTC，再加回台灣時間
               ROUND(AVG(spot_buy),  4) AS spot_buy,
               ROUND(AVG(spot_sell), 4) AS spot_sell,
               COUNT(DISTINCT bank_code) AS banks
        FROM rates
        WHERE currency = ?
          AND spot_buy IS NOT NULL AND spot_sell IS NOT NULL
          AND scraped_at >= datetime('now', ? || ' days')
        GROUP BY DATE(scraped_at, '+8 hours')
        ORDER BY date ASC
    """
    with _conn() as con:
        rows = con.execute(sql, (currency, f"-{days}")).fetchall()
    return [dict(r) for r in rows]


def get_usd_jpy() -> float | None:
    """
    以各銀行最新的 USD、JPY 即期賣出平均值推算 USD/JPY 參考值（用於三角換匯前端顯示）。
    """
    latest = {}
    for bank in get_latest_rates():
        for ccy in ("USD", "JPY"):
            v = (bank.get(ccy) or {}).get("spot_sell")
            if v:
                latest.setdefault(ccy, []).append(v)
    usd, jpy = latest.get("USD"), latest.get("JPY")
    if usd and jpy:
        return round((sum(usd) / len(usd)) / (sum(jpy) / len(jpy)), 2)
    return None
