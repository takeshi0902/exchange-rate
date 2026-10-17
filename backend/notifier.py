"""
Discord Webhook 通知模組
爬蟲失敗 → 發送警報到指定頻道
"""

import logging
import requests
from datetime import datetime, timezone, timedelta
from config import DISCORD_WEBHOOK_URL

log = logging.getLogger(__name__)
TZ8 = timezone(timedelta(hours=8))


def send_error(bank_name: str, error_msg: str) -> None:
    """爬蟲失敗時呼叫，發送紅色 embed 到 Discord。"""
    if not DISCORD_WEBHOOK_URL:
        log.warning("DISCORD_WEBHOOK_URL 未設定，跳過通知")
        return

    now = datetime.now(TZ8).strftime("%Y-%m-%d %H:%M")
    payload = {
        "embeds": [{
            "title": f"⚠️ 爬蟲失敗：{bank_name}",
            "description": (
                f"**時間：** {now}\n"
                f"**錯誤：** {error_msg[:500]}\n\n"
                "請檢查銀行網站是否改版，或確認伺服器連線是否正常。"
            ),
            "color": 0xE53935,  # 紅色
        }]
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        log.info(f"Discord 通知已發送：{bank_name}")
    except Exception as e:
        log.error(f"Discord 通知發送失敗：{e}")


def send_recovery(bank_name: str) -> None:
    """爬蟲從失敗狀態恢復正常時通知。"""
    if not DISCORD_WEBHOOK_URL:
        return
    now = datetime.now(TZ8).strftime("%Y-%m-%d %H:%M")
    payload = {
        "embeds": [{
            "title": f"✅ 爬蟲恢復：{bank_name}",
            "description": f"**時間：** {now}\n已成功取得最新匯率資料。",
            "color": 0x43A047,  # 綠色
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        log.error(f"Discord recovery 通知失敗：{e}")


def send_rate_limit(bank_name: str, count: int) -> None:
    """單一銀行今日請求超過上限時通知。"""
    if not DISCORD_WEBHOOK_URL:
        return
    now = datetime.now(TZ8).strftime("%Y-%m-%d %H:%M")
    payload = {
        "embeds": [{
            "title": f"🚦 請求限速：{bank_name}",
            "description": (
                f"**時間：** {now}\n"
                f"今日對 **{bank_name}** 的請求次數已達 **{count} 次**，"
                f"已暫停今日後續爬取。\n\n"
                "系統將於明日零時自動重置計數器並恢復爬取。"
            ),
            "color": 0xFB8C00,  # 橘色
        }]
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        log.info(f"Discord 限速通知已發送：{bank_name}")
    except Exception as e:
        log.error(f"Discord 限速通知失敗：{e}")


def send_daily_summary(stats: list[dict]) -> None:
    """每日摘要（可選用，在 scheduler 定時呼叫）。"""
    if not DISCORD_WEBHOOK_URL:
        return
    ok    = [s for s in stats if s["status"] == "ok"]
    fails = [s for s in stats if s["status"] == "error"]
    now   = datetime.now(TZ8).strftime("%Y-%m-%d %H:%M")
    color = 0x43A047 if not fails else 0xFB8C00
    lines = [f"✅ {s['bank']}" for s in ok] + [f"❌ {s['bank']}：{s['msg']}" for s in fails]
    payload = {
        "embeds": [{
            "title": f"🏦 換匯比較 爬蟲摘要 {now}",
            "description": "\n".join(lines) or "無資料",
            "color": color,
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        log.error(f"Discord 摘要通知失敗：{e}")
