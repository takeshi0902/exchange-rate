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
