"""
台新銀行爬蟲
來源：官網即時匯率頁（https://www.taishinbank.com.tw/TSB/personal/deposit/lookup/realtime/）
載入的 https://www.taishinbank.com.tw/eServiceA/transactionrate/transactionrateExport.jsp?no=5

該 JS 以 document.writeln('...') 逐行輸出 HTML（內容為 JS 跳脫字串）。
還原後有兩張表：
  表頭「幣別 | 銀行買入 | 銀行賣出」→ 即期
  表頭「幣別 | 現鈔買入 | 現鈔賣出」→ 現鈔
數值可能帶註記，如「0.2030 近30日最高」，to_float 只取數字。
"""

import json
import re
from bs4 import BeautifulSoup
from .base import BaseRateScraper, currency_code

EXPORT_URL = "https://www.taishinbank.com.tw/eServiceA/transactionrate/transactionrateExport.jsp?no=5"


def _decode_writeln(js: str) -> str:
    lines = re.findall(r"document\.writeln\('(.*?)'\);", js)
    return "\n".join(json.loads('"' + s.replace("\\'", "'") + '"') for s in lines)


class TAISHINScraper(BaseRateScraper):
    bank_code = "TAISHIN"
    bank_name = "台新銀行"

    def fetch(self) -> dict:
        html = _decode_writeln(self.get(EXPORT_URL).text)
        soup = BeautifulSoup(html, "lxml")
        book = self.new_book()

        for table in soup.select("table"):
            rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
            if not rows:
                continue
            header = rows[0].get_text(" ", strip=True)
            if "現鈔買入" in header and "即期" not in header:
                kind = "cash"
            elif "銀行買入" in header:
                kind = "spot"
            else:
                continue
            for tr in rows[1:]:
                tds = tr.find_all("td", recursive=False)
                if len(tds) >= 3:
                    book.add(currency_code(tds[0].get_text(strip=True)), kind,
                             tds[1].get_text(" ", strip=True), tds[2].get_text(" ", strip=True))
        return book.result()
