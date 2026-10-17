"""
國泰世華銀行爬蟲
URL: https://accessibility.cathaybk.com.tw/exchange-rate-search.aspx（無障礙版）

靜態 HTML，表格結構：幣別 | 買進匯率 | 賣出匯率
幣別格式：美元(USD)、美元現鈔(USD Cash)、日圓(JPY)
另有「數位通路優惠匯率(XXX Online Exchange Rate)」列，屬網銀限定價，目前略過。
"""

from bs4 import BeautifulSoup
from .base import BaseRateScraper, currency_code, is_cash_label

HTML_URL = "https://accessibility.cathaybk.com.tw/exchange-rate-search.aspx"


class CATHAYScraper(BaseRateScraper):
    bank_code = "CATHAY"
    bank_name = "國泰世華"

    def fetch(self) -> dict:
        r     = self.get(HTML_URL)
        soup  = BeautifulSoup(r.text, "lxml")
        table = soup.select_one("table.table_style_1")
        if not table:
            raise RuntimeError("找不到 table.table_style_1，頁面結構可能已變更")

        book = self.new_book()
        for tr in table.select("tr"):
            tds = tr.select("td")
            if len(tds) < 3:
                continue
            label = tds[0].get_text(" ", strip=True)
            if "數位通路" in label or "Online" in label:
                continue
            kind = "cash" if is_cash_label(label) else "spot"
            book.add(currency_code(label), kind, tds[1].get_text(strip=True), tds[2].get_text(strip=True))
        return book.result()
