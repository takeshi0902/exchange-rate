"""
合作金庫商業銀行爬蟲
來源：官網匯率頁背後的 JSON API
  1. GET  https://www.tcb-bank.com.tw/personal-banking/deposit-exchange/exchange-rate/spot
     取得 __RequestVerificationToken（表單與 cookie）
  2. POST https://www.tcb-bank.com.tw/api/client/ForeignExchange/GetSpotForeignExchange
     body: __RequestVerificationToken, date=YYYY-MM-DD

回應 result 每個幣別兩列（Type=買入 / 賣出），PromptExchange = 即期，CashExchange = 現鈔。
"""

from datetime import datetime, timedelta, timezone
import re
import requests
from .base import BaseRateScraper

PAGE_URL = "https://www.tcb-bank.com.tw/personal-banking/deposit-exchange/exchange-rate/spot"
API_URL  = "https://www.tcb-bank.com.tw/api/client/ForeignExchange/GetSpotForeignExchange"
TZ8 = timezone(timedelta(hours=8))


class TCBScraper(BaseRateScraper):
    bank_code = "TCB"
    bank_name = "合作金庫"

    def fetch(self) -> dict:
        session = requests.Session()
        page  = self.get(PAGE_URL, session=session)
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', page.text)
        if not m:
            raise RuntimeError("合作金庫：找不到 __RequestVerificationToken，頁面結構可能已變更")

        r = self.post(
            API_URL,
            session=session,
            data={"__RequestVerificationToken": m.group(1), "date": datetime.now(TZ8).date().isoformat()},
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": PAGE_URL},
        )

        book = self.new_book()
        for row in r.json().get("result") or []:
            currency = (row.get("Currency") or "").strip()
            if row.get("Type") == "買入":
                book.add(currency, "spot", row.get("PromptExchange"), None)
                book.add(currency, "cash", row.get("CashExchange"), None)
            elif row.get("Type") == "賣出":
                book.add(currency, "spot", None, row.get("PromptExchange"))
                book.add(currency, "cash", None, row.get("CashExchange"))
        return book.result()
