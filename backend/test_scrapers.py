"""
爬蟲測試腳本 — 實際連線各銀行，印出結果並做基本合理性檢查。
用法：
    cd backend
    python test_scrapers.py           # 測試所有啟用中的銀行
    python test_scrapers.py MEGA      # 只測試兆豐
    python test_scrapers.py MEGA HNCB # 測試指定銀行
    python test_scrapers.py BOT       # 指名暫停中的銀行也會執行（用來確認是否恢復）
"""

import sys
import logging
from scrapers import ALL_SCRAPERS, ACTIVE_SCRAPERS

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s  %(message)s")

filter_codes = {a.upper() for a in sys.argv[1:]}
FIELDS = ("spot_buy", "spot_sell", "cash_buy", "cash_sell")


def _fmt(val):
    return f"{val:.4f}" if val is not None else "—"


def check(data: dict) -> list[str]:
    """合理性檢查：賣出不得低於買入；現鈔價差應不小於即期。"""
    problems = []
    for ccy, r in data["rates"].items():
        for kind in ("spot", "cash"):
            b, s = r.get(f"{kind}_buy"), r.get(f"{kind}_sell")
            if b and s and s < b:
                problems.append(f"{ccy} {kind} 賣出 {s} < 買入 {b}")
        if all(r.get(f) for f in FIELDS) and (r["cash_sell"] - r["cash_buy"]) < (r["spot_sell"] - r["spot_buy"]):
            problems.append(f"{ccy} 現鈔價差小於即期價差")
    return problems


def run():
    scrapers = [s for s in ALL_SCRAPERS if s.bank_code in filter_codes] if filter_codes else ACTIVE_SCRAPERS
    for s in ALL_SCRAPERS:
        if not s.enabled and not filter_codes:
            print(f"（暫停）{s.bank_name} ({s.bank_code})：{s.disabled_reason}")

    results = []
    for ScraperCls in scrapers:
        scraper = ScraperCls()
        print(f"\n{'─'*60}\n  {scraper.bank_name} ({scraper.bank_code})\n{'─'*60}")
        try:
            data = scraper.fetch()
            rates = data["rates"]
            for currency in ("JPY", "USD"):
                r = rates.get(currency)
                print(f"  {currency}  " + ("無資料" if not r else
                      "  ".join(f"{f}={_fmt(r.get(f))}" for f in FIELDS)))
            with_cash = sorted(c for c, r in rates.items() if "cash_sell" in r)
            print(f"  共 {len(rates)} 幣別：{' '.join(sorted(rates))}")
            print(f"  有現鈔 {len(with_cash)}：{' '.join(with_cash) or '無'}")
            problems = check(data)
            for p in problems:
                print(f"  [警告] {p}")
            results.append((scraper.bank_name, "ok" if not problems else "warn", "；".join(problems)))
        except Exception as e:
            results.append((scraper.bank_name, "error", str(e)))
            print(f"  [失敗] {e}")

    ok   = sum(1 for _, st, _ in results if st == "ok")
    warn = sum(1 for _, st, _ in results if st == "warn")
    fail = sum(1 for _, st, _ in results if st == "error")
    print(f"\n{'='*60}\n  結果：成功 {ok} / 警告 {warn} / 失敗 {fail} / 共 {len(results)}\n{'='*60}")
    for name, st, msg in results:
        if st != "ok":
            print(f"[{st.upper()}] {name}: {msg}")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    run()
