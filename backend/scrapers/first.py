"""
第一銀行爬蟲
URL: https://ebank.firstbank.com.tw/BATcpibWeb/html/FQ1010.html

頁面使用 Big5 編碼，匯率值以 <script>dispHyphen('X');</script> 嵌入。
欄位：幣別名稱 | 類別（即期/現鈔）| 買入匯率 | 賣出匯率
「大額美金」為大額交易報價，不屬一般換匯，略過。
"""

import re
from bs4 import BeautifulSoup
from .base import BaseRateScraper, currency_code, is_cash_label

HTML_URL = "https://ebank.firstbank.com.tw/BATcpibWeb/html/FQ1010.html"


def _cell_value(td) -> str | None:
    """匯率可能直接是文字，或包在 dispHyphen('X') 裡。"""
    script = td.find("script")
    if not script:
        return td.get_text(strip=True)
    m = re.search(r"dispHyphen\(['\"]([\d.]+)['\"]", script.string or "")
    return m.group(1) if m else None


class FIRSTScraper(BaseRateScraper):
    bank_code = "FIRST"
    bank_name = "第一銀行"

    def fetch(self) -> dict:
        r = self.get(HTML_URL)
        r.encoding = "big5"   # 強制 Big5 解碼
        soup = BeautifulSoup(r.text, "lxml")

        book = self.new_book()
        for tr in soup.select("tr"):
            tds = tr.select("td")
            if len(tds) < 4:
                continue
            name = tds[0].get_text(" ", strip=True)
            kind_text = tds[1].get_text(strip=True)
            if "大額" in name or not re.search(r"即期|現鈔|現金", kind_text):
                continue
            kind = "cash" if is_cash_label(kind_text) else "spot"
            book.add(currency_code(name), kind, _cell_value(tds[2]), _cell_value(tds[3]))
        return book.result()
