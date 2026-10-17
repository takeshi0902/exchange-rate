"""
玉山銀行爬蟲
URL: https://www.esunbank.com.tw/bank/personal/deposit/rate/forex/foreign-exchange-rates/
     （重新導向至 esunbank.com/zh-tw/...）

頁面內嵌 JSON-LD（Schema.org ExchangeRateSpecification），直接解析即可。
name 欄位格式："日圓 即期匯率 銀行買入" / "日圓 現金匯率 銀行賣出"
"""

import json
from bs4 import BeautifulSoup
from .base import BaseRateScraper

HTML_URL = (
    "https://www.esunbank.com.tw/bank/personal/deposit/"
    "rate/forex/foreign-exchange-rates/"
)


class ESUNScraper(BaseRateScraper):
    bank_code = "ESUN"
    bank_name = "玉山銀行"

    def fetch(self) -> dict:
        r    = self.get(HTML_URL, allow_redirects=True)
        soup = BeautifulSoup(r.text, "lxml")
        book = self.new_book()

        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            main  = data.get("mainEntity") or data.get("about") or {}
            items = main.get("itemListElement") or []
            if not items and data.get("@type") == "ExchangeRateSpecification":
                items = [data]

            for item in items:
                if item.get("@type") != "ExchangeRateSpecification":
                    continue
                name  = item.get("name", "")
                price = (item.get("currentExchangeRate") or {}).get("price")
                kind  = "cash" if "現金" in name else "spot"
                if "買入" in name:
                    book.add(item.get("currency"), kind, price, None)
                else:
                    book.add(item.get("currency"), kind, None, price)

        return book.result()
