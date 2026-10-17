"""
APScheduler 排程模組
─────────────────────────────────────────────────────
每小時執行一次全銀行爬蟲，結果存入 SQLite。

安全機制：
  - 每日請求計數器：單一銀行超過 50 次自動停止並通知 Discord
  - 連續失敗計數器：連續失敗 3 次才發通知，成功一次即重置
  - 恢復通知：從錯誤狀態恢復時發送綠色通知
"""

import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database as DB
import notifier  as NT
from scrapers import ACTIVE_SCRAPERS
from config import SCRAPE_INTERVAL_HOURS

log = logging.getLogger(__name__)
TZ8 = timezone(timedelta(hours=8))

DAILY_REQUEST_LIMIT = 50   # 單銀行每日最高請求次數

# ── 跨呼叫狀態（模組層級） ─────────────────────────────────────────────────────

_daily_counts:        dict[str, int]  = {}   # bank_code → 今日請求次數
_consecutive_fails:   dict[str, int]  = {}   # bank_code → 連續失敗次數
_notified_error:      set[str]        = set() # 已發出錯誤通知的 bank_code 集合
_last_reset_day:      object          = None  # datetime.date，上次重置日期


def _maybe_reset_daily_counters() -> None:
    """跨日時清空每日計數器。"""
    global _last_reset_day
    today = datetime.now(TZ8).date()
    if _last_reset_day != today:
        _daily_counts.clear()
        _last_reset_day = today
        log.info("每日請求計數器已重置")


# ── 核心爬蟲執行 ──────────────────────────────────────────────────────────────

def scrape_all() -> list[dict]:
    """執行所有爬蟲，回傳每家銀行的 {bank, status, msg} 清單。"""
    _maybe_reset_daily_counters()
    stats = []

    for ScraperCls in ACTIVE_SCRAPERS:   # 暫停中的銀行不執行
        scraper   = ScraperCls()
        bank_name = scraper.bank_name
        bank_code = scraper.bank_code

        # ── 每日請求上限檢查 ──────────────────────────────────────────────
        today_count = _daily_counts.get(bank_code, 0)
        if today_count >= DAILY_REQUEST_LIMIT:
            # 僅在剛達到門檻時通知一次（下一次 count 已超過不再通知）
            if today_count == DAILY_REQUEST_LIMIT:
                NT.send_rate_limit(bank_name, today_count)
                _daily_counts[bank_code] = DAILY_REQUEST_LIMIT + 1  # 避免重複通知
                log.warning(f"{bank_name} 今日請求已達 {DAILY_REQUEST_LIMIT} 次，發出限速通知")
            else:
                log.debug(f"{bank_name} 今日請求超限，略過")
            stats.append({"bank": bank_name, "status": "skipped", "msg": "rate_limit"})
            continue

        _daily_counts[bank_code] = today_count + 1

        # ── 執行爬蟲 ─────────────────────────────────────────────────────
        try:
            data = scraper.fetch()
            DB.save_rates(data)
            DB.log_scrape(bank_code, "ok")

            # 若先前已發過錯誤通知 → 發恢復通知，清除記錄
            if bank_code in _notified_error:
                NT.send_recovery(bank_name)
                _notified_error.discard(bank_code)

            _consecutive_fails[bank_code] = 0
            stats.append({"bank": bank_name, "status": "ok", "msg": ""})
            log.info(f"[OK] {bank_name}（今日第 {_daily_counts[bank_code]} 次）")

        except Exception as e:
            msg   = str(e)
            consec = _consecutive_fails.get(bank_code, 0) + 1
            _consecutive_fails[bank_code] = consec
            DB.log_scrape(bank_code, "error", msg)

            # 連續失敗滿 3 次才發通知（之後不重複）
            if consec == 3:
                NT.send_error(bank_name, msg)
                _notified_error.add(bank_code)

            stats.append({"bank": bank_name, "status": "error", "msg": msg})
            log.error(f"[FAIL] {bank_name}（連續第 {consec} 次）: {msg}")

    now      = datetime.now(TZ8).strftime("%H:%M")
    ok_count = sum(1 for s in stats if s["status"] == "ok")
    log.info(f"爬蟲完成 {now}：成功 {ok_count} / 共 {len(stats)}")
    return stats


# ── 排程器啟動 ────────────────────────────────────────────────────────────────

def start(run_now: bool = True) -> BackgroundScheduler:
    """
    建立並啟動排程器。
    run_now=True → 啟動後立即在背景執行一次，不阻塞 FastAPI 啟動。
    """
    scheduler = BackgroundScheduler(timezone="Asia/Taipei")
    scheduler.add_job(
        scrape_all,
        trigger=IntervalTrigger(hours=SCRAPE_INTERVAL_HOURS),
        id="scrape_all",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    log.info(f"排程啟動，每 {SCRAPE_INTERVAL_HOURS} 小時執行一次")

    if run_now:
        import threading
        threading.Thread(target=scrape_all, daemon=True, name="scrape-init").start()

    return scheduler
