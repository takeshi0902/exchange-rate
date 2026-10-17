"""
部署前檢查（wrangler.jsonc 的 build.command 會先執行本檔）：
site/data/rates.json 必須存在且在 3 小時內產生，否則中止部署，
避免從本機手動部署時把沒有匯率、或匯率過舊的網站推上線。

正常部署由 GitHub Actions 負責；要手動更新請到 GitHub → Actions → 「更新匯率並部署」→ Run workflow。
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RATES = Path(__file__).resolve().parents[1] / "site" / "data" / "rates.json"
MAX_AGE = timedelta(hours=3)

try:
    updated = datetime.fromisoformat(json.loads(RATES.read_text(encoding="utf-8"))["updated_at"])
except (FileNotFoundError, KeyError, ValueError) as e:
    sys.exit(f"[中止部署] 找不到有效的 {RATES.name}（{e}）。請改用 GitHub Actions 部署。")

age = datetime.now(timezone.utc) - updated
if age > MAX_AGE:
    sys.exit(f"[中止部署] {RATES.name} 已是 {age} 前的資料。請改用 GitHub Actions 部署。")
print(f"資料檢查通過（{RATES.name} 產生於 {updated.isoformat()}）")
