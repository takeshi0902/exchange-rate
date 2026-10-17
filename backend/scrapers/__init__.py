"""
銀行爬蟲註冊表。新增銀行：在 scrapers/ 新增一個檔案，再加到 ALL_SCRAPERS。
enabled = False 的銀行不會執行，API 會以 unavailable 列出原因。
"""

from .bot      import BOTScraper
from .mega     import MEGAScraper
from .esun     import ESUNScraper
from .cathay   import CATHAYScraper
from .tcb      import TCBScraper
from .first    import FIRSTScraper
from .ctbc     import CTBCScraper
from .taishin  import TAISHINScraper
from .fubon    import FUBONScraper
from .sinopac  import SINOPACScraper
from .hncb     import HNCBScraper
from .chb      import CHBScraper
from .landbank import LANDBANKScraper

ALL_SCRAPERS = [
    BOTScraper, MEGAScraper, ESUNScraper, CATHAYScraper, TCBScraper, FIRSTScraper,
    CTBCScraper, TAISHINScraper, FUBONScraper, SINOPACScraper, HNCBScraper, CHBScraper,
    LANDBANKScraper,
]

ACTIVE_SCRAPERS = [s for s in ALL_SCRAPERS if s.enabled]


def unavailable_banks() -> list[dict]:
    """暫停中的銀行與原因，供 API 回報前端。"""
    return [
        {"bank_code": s.bank_code, "bank_name": s.bank_name, "reason": s.disabled_reason}
        for s in ALL_SCRAPERS if not s.enabled
    ]
