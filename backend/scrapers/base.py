"""
爬蟲基底類別 + 共用工具函式
每個銀行爬蟲繼承 BaseRateScraper，實作 fetch() 方法。

fetch() 回傳格式：
{
  "bank_code": "MEGA",
  "bank_name": "兆豐銀行",
  "rates": {
    "JPY": {"spot_buy": 0.2031, "spot_sell": 0.2072, "cash_buy": 0.1959, "cash_sell": 0.2086},
    "USD": {...},
    ...銀行公布的所有幣別
  },
}
任何欄位若無法取得就不放（不填 None）；沒有任何幣別時應 raise。
"""

import logging
import re
import time
import requests
from abc import ABC, abstractmethod
from config import HEADERS, REQUEST_TIMEOUT

log = logging.getLogger(__name__)


class BaseRateScraper(ABC):
    bank_code: str = ""
    bank_name: str = ""
    # 暫停的銀行：排程略過，API 以 unavailable 回報原因
    enabled: bool = True
    disabled_reason: str = ""

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """帶 retry 的 HTTP 請求。"""
        headers = {**HEADERS, **kwargs.pop("headers", {})}
        session = kwargs.pop("session", None) or requests
        for attempt in range(3):
            try:
                r = session.request(method, url, headers=headers, timeout=REQUEST_TIMEOUT, **kwargs)
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                log.warning(f"{self.bank_code} 第 {attempt+1} 次失敗，重試中：{e}")
                time.sleep(2 ** attempt)  # 1s, 2s backoff

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def new_book(self) -> "RateBook":
        return RateBook(self.bank_code, self.bank_name)

    @abstractmethod
    def fetch(self) -> dict:
        """抓取並回傳上方註解的格式。"""


class RateBook:
    """收集單一銀行各幣別匯率，輸出 fetch() 的回傳格式。"""

    def __init__(self, bank_code: str, bank_name: str):
        self.bank_code = bank_code
        self.bank_name = bank_name
        self.rates: dict[str, dict[str, float]] = {}

    def add(self, currency: str | None, kind: str, buy, sell) -> None:
        """kind 為 'spot' 或 'cash'；buy / sell 可為字串或數字，無效值自動略過。"""
        if not currency or kind not in ("spot", "cash"):
            return
        buy, sell = to_float(buy), to_float(sell)
        entry = self.rates.setdefault(currency, {})
        if buy:  entry[f"{kind}_buy"]  = buy
        if sell: entry[f"{kind}_sell"] = sell
        if not entry:
            del self.rates[currency]

    def result(self) -> dict:
        if not self.rates:
            raise RuntimeError(f"{self.bank_name} 未取得任何匯率，頁面或 API 結構可能已變更")
        return {"bank_code": self.bank_code, "bank_name": self.bank_name, "rates": self.rates}


# ── 共用工具 ──────────────────────────────────────────────────────────────────

def to_float(text) -> float | None:
    """'0.2182' / '31,475' / ' 0.2030 近30日最高' → float，無法解析或 ≤0 回 None。"""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text) if text > 0 else None
    m = re.search(r"\d[\d,]*\.?\d*", str(text))
    if not m:
        return None
    try:
        v = float(m.group(0).replace(",", ""))
        return v if v > 0 else None
    except ValueError:
        return None


# 中文幣別名稱 → ISO 4217；較長的名稱放前面，避免「美金」吃掉「大額美金」之類的比對
_ZH_CURRENCY = [
    ("澳大利亞幣", "AUD"), ("紐西蘭幣", "NZD"), ("新加坡幣", "SGD"), ("加拿大幣", "CAD"),
    ("瑞士法郎", "CHF"), ("土耳其里拉", "TRY"), ("墨西哥披索", "MXN"), ("菲國比索", "PHP"),
    ("菲律賓比索", "PHP"), ("馬來西亞幣", "MYR"), ("越南盾", "VND"), ("印尼盾", "IDR"),
    ("人民幣", "CNY"), ("南非幣", "ZAR"), ("瑞典幣", "SEK"), ("丹麥幣", "DKK"),
    ("泰國銖", "THB"), ("泰國幣", "THB"), ("澳門幣", "MOP"), ("馬來幣", "MYR"),
    ("美金", "USD"), ("美元", "USD"), ("日圓", "JPY"), ("日元", "JPY"), ("日幣", "JPY"),
    ("港幣", "HKD"), ("英鎊", "GBP"), ("澳幣", "AUD"), ("加幣", "CAD"), ("紐幣", "NZD"),
    ("歐元", "EUR"), ("泰銖", "THB"), ("泰幣", "THB"), ("韓元", "KRW"), ("韓幣", "KRW"),
]
# 不是一般換匯幣別（黃金、新台幣本身），一律略過
_EXCLUDE = {"XAU", "XAG", "TWD"}


def currency_code(text: str) -> str | None:
    """'日圓 (JPY)' / '美金現鈔 (USD-C)' / '美元USD' / '日元' → ISO 代碼；認不出回 None。

    只看第一個三字母代碼：「黃金XAU(USD)」會先遇到 XAU 而略過，不會誤判成 USD。
    （中文字在 regex 中算 \\w，不能用 \\b 判斷邊界，改用前後不是大寫字母。）
    """
    if not text or "黃金" in text:
        return None
    m = re.search(r"(?<![A-Z])([A-Z]{3})(?![A-Z])", text)
    if m:
        code = m.group(1)
        return None if code in _EXCLUDE else code
    for zh, code in _ZH_CURRENCY:
        if zh in text:
            return code
    return None


def is_cash_label(text: str) -> bool:
    """幣別欄或類別欄是否表示現鈔。"""
    return bool(re.search(r"現鈔|現金|Cash|-C\b", text or ""))
