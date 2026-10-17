"""
中國信託商業銀行（暫停）
官網匯率頁：https://www.ctbcbank.com/twrbo/zh_tw/dep_index/dep_ratequery/dep_foreign_rates.html

2026-10-18 檢查：頁面回傳 HTTP 202 空殼，等待 15 秒仍無匯率資料或 API 請求，
推斷有防機器人機制。不嘗試繞過；待有官方資料管道再實作。
"""

from .base import BaseRateScraper


class CTBCScraper(BaseRateScraper):
    bank_code = "CTBC"
    bank_name = "中國信託"
    enabled = False
    disabled_reason = "官網有防機器人機制，暫時無法取得"

    def fetch(self) -> dict:
        raise RuntimeError(self.disabled_reason)
