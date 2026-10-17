"""
定時建置匯率資料（由 GitHub Actions 每小時執行，見 .github/workflows/update-rates.yml）
─────────────────────────────────────────────────────
流程：執行所有啟用中的爬蟲 → 合理性檢查 → 更新資料庫（data 分支）→ 輸出前端用的靜態 JSON

用法：
    python backend/build_data.py --store data-store --out site/data

--store：持久資料（git 的 data 分支），保存跨次執行的狀態
    latest.json        各銀行最後一次成功的匯率
    history/{幣別}.json 每日各銀行即期平均（每次執行覆寫當天那一筆）
    state.json         各銀行連續失敗次數、最後狀態（用於通知）
--out：前端讀取的靜態檔
    rates.json         格式同舊版 /api/rates
    history/{幣別}.json {"currency", "data": [{date, spot_buy, spot_sell, banks}]}
    status.json        各銀行爬蟲狀態

某家銀行失敗時沿用它上一次成功的資料（updated_at 不變，前端會標示資料過舊）。
全部銀行都失敗時以 exit code 1 結束，讓 workflow 顯示失敗，但仍輸出舊資料。
"""

import argparse
import json
import logging
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scrapers import ACTIVE_SCRAPERS, unavailable_banks  # noqa: E402
import notifier as NT                                      # noqa: E402

log = logging.getLogger("build_data")
TZ8 = timezone(timedelta(hours=8))
FIELDS = ("spot_buy", "spot_sell", "cash_buy", "cash_sell")
OUTLIER_RATIO = 0.20     # 與各銀行中位數相差超過 20% 視為異常值
NOTIFY_AFTER_FAILS = 3   # 連續失敗幾次才發通知


# ── 讀寫 ─────────────────────────────────────────────────────────────────────

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# ── 合理性檢查 ───────────────────────────────────────────────────────────────

def drop_inverted(bank: dict) -> list[str]:
    """賣出低於買入的報價視為錯誤，移除該組（即期或現鈔）。回傳問題描述。"""
    problems = []
    for ccy, r in list(bank["rates"].items()):
        for kind in ("spot", "cash"):
            b, s = r.get(f"{kind}_buy"), r.get(f"{kind}_sell")
            if b and s and s < b:
                problems.append(f"{ccy} {kind} 賣出 {s} < 買入 {b}")
                r.pop(f"{kind}_buy"); r.pop(f"{kind}_sell")
        if not r:
            del bank["rates"][ccy]
    return problems


def drop_outliers(banks: list[dict]) -> list[str]:
    """跨銀行比對：同幣別同欄位與中位數相差超過 OUTLIER_RATIO 的值移除（例：黃金價誤判為美元）。"""
    problems = []
    for field in FIELDS:
        values: dict[str, list[tuple[dict, float]]] = {}
        for bank in banks:
            for ccy, r in bank["rates"].items():
                if r.get(field):
                    values.setdefault(ccy, []).append((bank, r[field]))
        for ccy, pairs in values.items():
            if len(pairs) < 3:      # 太少家無法判斷
                continue
            median = statistics.median(v for _, v in pairs)
            for bank, v in pairs:
                if abs(v - median) / median > OUTLIER_RATIO:
                    problems.append(f"{bank['bank_name']} {ccy} {field}={v}（中位數 {median}）")
                    bank["rates"][ccy].pop(field)
    for bank in banks:
        bank["rates"] = {c: r for c, r in bank["rates"].items() if r}
    return problems


# ── 主流程 ───────────────────────────────────────────────────────────────────

def scrape(state: dict, now: str) -> tuple[list[dict], dict]:
    """執行爬蟲，回傳 (成功的銀行資料, 本次狀態)。"""
    ok, status = [], {}
    for Scraper in ACTIVE_SCRAPERS:
        s = Scraper()
        st = state.setdefault(s.bank_code, {"consecutive_fails": 0, "notified": False})
        try:
            data = s.fetch()
            problems = drop_inverted(data)
            data["updated_at"] = now
            ok.append(data)
            if st.get("notified"):
                NT.send_recovery(s.bank_name)
            st.update(consecutive_fails=0, notified=False, last_ok=now)
            status[s.bank_code] = {"bank_name": s.bank_name, "status": "warn" if problems else "ok",
                                   "message": "；".join(problems), "checked_at": now}
            log.info(f"[OK] {s.bank_name} {len(data['rates'])} 幣別" + (f"（{len(problems)} 項異常已移除）" if problems else ""))
        except Exception as e:  # 單一銀行失敗不影響其他銀行
            st["consecutive_fails"] = st.get("consecutive_fails", 0) + 1
            if st["consecutive_fails"] >= NOTIFY_AFTER_FAILS and not st.get("notified"):
                NT.send_error(s.bank_name, str(e))
                st["notified"] = True
            status[s.bank_code] = {"bank_name": s.bank_name, "status": "error", "message": str(e)[:300],
                                   "checked_at": now, "last_ok": st.get("last_ok")}
            log.error(f"[FAIL] {s.bank_name}（連續第 {st['consecutive_fails']} 次）：{e}")
    return ok, status


def build_rates_json(latest: dict, now: str) -> dict:
    """組成前端 rates.json（格式同舊版 /api/rates）。"""
    rates = []
    for code in sorted(latest):
        b = latest[code]
        entry = {"bank": b["bank_name"], "bank_name": b["bank_name"], "bank_code": code}
        for ccy, r in b["rates"].items():
            entry[ccy] = {f: r.get(f) for f in FIELDS} | {"updated_at": b["updated_at"]}
        rates.append(entry)
    return {"updated_at": now, "rates": rates, "usd_jpy": usd_jpy(latest), "unavailable": unavailable_banks()}


def averages(latest: dict, ccy: str, field: str) -> tuple[float | None, int]:
    vals = [b["rates"][ccy][field] for b in latest.values() if b["rates"].get(ccy, {}).get(field)]
    return (round(sum(vals) / len(vals), 4) if vals else None, len(vals))


def usd_jpy(latest: dict) -> float | None:
    usd, _ = averages(latest, "USD", "spot_sell")
    jpy, _ = averages(latest, "JPY", "spot_sell")
    return round(usd / jpy, 2) if usd and jpy else None


def update_history(store: Path, latest: dict, today: str) -> list[str]:
    """把今天的各銀行即期平均寫入 history/{幣別}.json，回傳有歷史資料的幣別。"""
    currencies = sorted({c for b in latest.values() for c in b["rates"]})
    written = []
    for ccy in currencies:
        buy, n_buy = averages(latest, ccy, "spot_buy")
        sell, n_sell = averages(latest, ccy, "spot_sell")
        if not (buy and sell):
            continue        # 只有現鈔的幣別（如兆豐韓元）不列入走勢
        path = store / "history" / f"{ccy}.json"
        hist = load_json(path, {})
        hist[today] = {"spot_buy": buy, "spot_sell": sell, "banks": min(n_buy, n_sell)}
        save_json(path, hist)
        written.append(ccy)
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    now_dt = datetime.now(TZ8)
    now, today = now_dt.isoformat(timespec="seconds"), now_dt.date().isoformat()

    state  = load_json(args.store / "state.json", {})
    latest = load_json(args.store / "latest.json", {})

    fresh, status = scrape(state, now)
    for problem in drop_outliers(fresh):
        log.warning(f"[異常值已移除] {problem}")
    for bank in fresh:
        latest[bank["bank_code"]] = bank
    # 已停用（移出 ACTIVE_SCRAPERS）的銀行不再顯示
    active = {s.bank_code for s in ACTIVE_SCRAPERS}
    latest = {c: b for c, b in latest.items() if c in active}

    save_json(args.store / "state.json", state)
    save_json(args.store / "latest.json", latest)
    history_ccys = update_history(args.store, latest, today) if fresh else []

    # 前端靜態檔
    save_json(args.out / "rates.json", build_rates_json(latest, now))
    save_json(args.out / "status.json", {"checked_at": now, "banks": status, "unavailable": unavailable_banks()})
    for path in sorted((args.store / "history").glob("*.json")):
        hist = load_json(path, {})
        save_json(args.out / "history" / path.name,
                  {"currency": path.stem, "data": [{"date": d, **v} for d, v in sorted(hist.items())]})

    log.info(f"完成：成功 {len(fresh)} / {len(ACTIVE_SCRAPERS)} 家，走勢 {len(history_ccys)} 幣別")
    return 0 if fresh else 1


if __name__ == "__main__":
    sys.exit(main())
