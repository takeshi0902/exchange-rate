"""
臺灣土地銀行爬蟲
URL: https://rate.landbank.com.tw/zh-TW/Foreign?mid=35

靜態 HTML，table.table_rate 每列：
  幣別「日圓 (JPY)」| 即期買入 | 即期賣出 | 現金買入 | 現金賣出 | 歷史匯率連結
無報價的欄位顯示「--」。
"""

from bs4 import BeautifulSoup
from .base import BaseRateScraper, currency_code

HTML_URL = "https://rate.landbank.com.tw/zh-TW/Foreign?mid=35"


class LANDBANKScraper(BaseRateScraper):
    bank_code = "LANDBANK"
    bank_name = "土地銀行"

    def fetch(self) -> dict:
        soup  = BeautifulSoup(self.get(HTML_URL).text, "lxml")
        table = soup.select_one("table.table_rate")
        if not table:
            raise RuntimeError("找不到 table.table_rate，頁面結構可能已變更")

        book = self.new_book()
        for tr in table.select("tr"):
            cells = [td.get_text(strip=True) for td in tr.select("td")]
            if len(cells) < 5:
                continue
            currency = currency_code(cells[0])
            book.add(currency, "spot", cells[1], cells[2])
            book.add(currency, "cash", cells[3], cells[4])
        return book.result()
