"""
台灣銀行（暫停）
URL: https://rate.bot.com.tw/xrt?Lang=zh-TW

2026-10-18 檢查：網站加入「Challenge Validation」防機器人驗證，程式請求只拿到驗證頁。
官方開放資料 API（govdata.bot.com.tw /105011/1/ByYearAndCcy）各年度皆回「找不到資料」。
不嘗試繞過驗證；待有官方資料管道再恢復。下方解析程式保留，恢復時可直接使用。

表格欄位順序：幣別 | 現金買入 | 現金賣出 | 即期買入 | 即期賣出 | ...
"""

from bs4 import BeautifulSoup
from .base import BaseRateScraper, currency_code

URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"


class BOTScraper(BaseRateScraper):
    bank_code = "BOT"
    bank_name = "台灣銀行"
    enabled = False
    disabled_reason = "官網加入防機器人驗證，暫時無法取得"

    def fetch(self) -> dict:
        soup  = BeautifulSoup(self.get(URL).text, "lxml")
        table = soup.select_one("table.table tbody") or soup.select_one("table tbody")
        if not table:
            raise RuntimeError("找不到匯率表格")

        book = self.new_book()
        for tr in table.select("tr"):
            tds = tr.select("td")
            if len(tds) < 5:
                continue
            currency = currency_code(tds[0].get_text(" ", strip=True))
            book.add(currency, "cash", tds[1].get_text(strip=True), tds[2].get_text(strip=True))
            book.add(currency, "spot", tds[3].get_text(strip=True), tds[4].get_text(strip=True))
        return book.result()
