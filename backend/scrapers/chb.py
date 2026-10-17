"""
彰化銀行爬蟲
來源：官網匯率頁（https://www.bankchb.com/frontend/G0100_query.jsp）
載入的 JSON API：POST https://www.bankchb.com/frontend/jsp/getG0100_query.jsp

回應：{"update_time": "...", "datas": [{"curname": "日圓 (JPY)", "buy": "...", "sell": "..."}, ...]}
curname 帶「-C」（如「日圓現鈔 (JPY-C)」）為現鈔，其餘為即期。
"""

from .base import BaseRateScraper, currency_code, is_cash_label

PAGE_URL = "https://www.bankchb.com/frontend/G0100_query.jsp"
API_URL  = "https://www.bankchb.com/frontend/jsp/getG0100_query.jsp"


class CHBScraper(BaseRateScraper):
    bank_code = "CHB"
    bank_name = "彰化銀行"

    def fetch(self) -> dict:
        r = self.post(API_URL, headers={"Accept": "application/json", "Referer": PAGE_URL,
                                        "X-Requested-With": "XMLHttpRequest"})
        book = self.new_book()
        for row in r.json().get("datas") or []:
            name = row.get("curname", "")
            kind = "cash" if is_cash_label(name) else "spot"
            book.add(currency_code(name), kind, row.get("buy"), row.get("sell"))
        return book.result()
