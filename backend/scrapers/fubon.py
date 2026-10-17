"""
台北富邦銀行爬蟲
URL: https://www.fubon.com/Fubon_Portal/banking/Personal/deposit/exchange_rate/exchange_rate1.jsp

靜態 HTML，table.rate-table 每列：
  旗幟 | 幣別「美金(USD)」| 圖表連結 | 即期「買入<br>賣出」| 現鈔「買入<br>賣出」
買入、賣出放在同一格，以 <br> 分隔。
"""

from bs4 import BeautifulSoup
from .base import BaseRateScraper, currency_code

HTML_URL = "https://www.fubon.com/Fubon_Portal/banking/Personal/deposit/exchange_rate/exchange_rate1.jsp"


def _buy_sell(td) -> tuple[str | None, str | None]:
    parts = [s.strip() for s in td.stripped_strings]
    return (parts[0] if parts else None, parts[1] if len(parts) > 1 else None)


class FUBONScraper(BaseRateScraper):
    bank_code = "FUBON"
    bank_name = "台北富邦"

    def fetch(self) -> dict:
        soup  = BeautifulSoup(self.get(HTML_URL).text, "lxml")
        table = soup.select_one("table.rate-table")
        if not table:
            raise RuntimeError("找不到 table.rate-table，頁面結構可能已變更")

        book = self.new_book()
        for tr in table.select("tr"):
            tds = tr.select("td")
            if len(tds) < 5:
                continue
            currency = currency_code(tds[1].get_text(strip=True))
            book.add(currency, "spot", *_buy_sell(tds[3]))
            book.add(currency, "cash", *_buy_sell(tds[4]))
        return book.result()
