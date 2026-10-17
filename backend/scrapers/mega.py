"""
兆豐銀行爬蟲
來源：官網匯率頁背後的 JSON API（頁面 https://www.megabank.com.tw/personal/savings/foreign-service/forex）
https://www.megabank.com.tw/api/client/ExchangeRate/GetRateData

回應：{"updateTime": "...", "rates": [{"currKey": "USD|01",
        "spot": {"bid": "32.32", "ask": "32.42"}, "cash": {"bid": ..., "ask": ...}}, ...]}
bid = 銀行買入，ask = 銀行賣出。
"""

from .base import BaseRateScraper

PAGE_URL = "https://www.megabank.com.tw/personal/savings/foreign-service/forex"
API_URL  = (
    "https://www.megabank.com.tw/api/client/ExchangeRate/GetRateData"
    "?sc_lang=zh-TW&sc_site=bank-zh-tw&dic_lang=zh-TW"
)


class MEGAScraper(BaseRateScraper):
    bank_code = "MEGA"
    bank_name = "兆豐銀行"

    def fetch(self) -> dict:
        r = self.get(API_URL, headers={"Accept": "application/json", "Referer": PAGE_URL})
        book = self.new_book()
        for item in r.json().get("rates", []):
            currency = (item.get("currKey") or "").split("|")[0]
            for kind in ("spot", "cash"):
                q = item.get(kind) or {}
                book.add(currency, kind, q.get("bid"), q.get("ask"))
        return book.result()
