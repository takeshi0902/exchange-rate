"""
永豐銀行爬蟲
來源：官網匯率頁（https://bank.sinopac.com/MMA8/bank/html/rate/bank_ExchangeRate.html）
載入的 JSON API：
  https://mma.sinopac.com/ws/share/rate/ws_exchange.ashx?exchangeType=REMIT  → 即期（匯款）
  https://mma.sinopac.com/ws/share/rate/ws_exchange.ashx?exchangeType=CASH   → 現鈔

回應為陣列，[0].SubInfo 每列：DataValue2 = 銀行買進、DataValue3 = 銀行賣出、DataValue4 = 幣別代碼。
"""

import json
from .base import BaseRateScraper

API_URL = "https://mma.sinopac.com/ws/share/rate/ws_exchange.ashx?exchangeType={}"


class SINOPACScraper(BaseRateScraper):
    bank_code = "SINOPAC"
    bank_name = "永豐銀行"

    def fetch(self) -> dict:
        book = self.new_book()
        for exchange_type, kind in (("REMIT", "spot"), ("CASH", "cash")):
            text = self.get(API_URL.format(exchange_type)).text.strip()
            if not text.startswith("["):          # 防萬一回傳 JSONP 包裝
                text = text[text.index("(") + 1 : text.rindex(")")]
            data = json.loads(text)
            for row in (data[0].get("SubInfo") if data else None) or []:
                book.add(row.get("DataValue4"), kind, row.get("DataValue2"), row.get("DataValue3"))
        return book.result()
