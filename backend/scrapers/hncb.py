"""
華南銀行爬蟲
來源：官網匯率頁（https://www.hncb.com.tw/wps/portal/HNCB/exchange-rate/）
載入的 JSON API：https://www.hncb.com.tw/hncb/rest/exRate/all

回應為陣列，TYPE="forward" 為遠期匯率（略過），TYPE 空白為即期；
DESC_ENG 為幣別代碼，BUY_AMT_BOARD / SELL_AMT_BOARD 為銀行買入 / 賣出。
官網未提供現鈔匯率 API，故只有即期。
"""

from .base import BaseRateScraper, currency_code

API_URL = "https://www.hncb.com.tw/hncb/rest/exRate/all"


class HNCBScraper(BaseRateScraper):
    bank_code = "HNCB"
    bank_name = "華南銀行"

    def fetch(self) -> dict:
        r = self.get(API_URL, headers={"Accept": "application/json"})
        book = self.new_book()
        for row in r.json():
            if (row.get("TYPE") or "").strip():
                continue
            book.add(currency_code(row.get("DESC_ENG", "")), "spot",
                     row.get("BUY_AMT_BOARD"), row.get("SELL_AMT_BOARD"))
        return book.result()
