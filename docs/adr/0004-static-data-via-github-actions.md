# ADR 0004：以 GitHub Actions 定時產生靜態匯率資料，取代 API 伺服器

- 日期：2026-10-18
- 狀態：已採用（取代原本 Render ＋ FastAPI ＋ SQLite 的設計）

## 背景

原設計是部署 FastAPI 伺服器到 Render，以 APScheduler 每小時爬取並存入 SQLite。檢查後發現：

- `render.yaml` 使用免費方案＋永久磁碟，但 Render 免費方案不提供永久磁碟 → 每次重啟資料清空，歷史走勢存不住
- 免費方案閒置 15 分鐘休眠 → 休眠期間排程不執行
- 公開的 API 伺服器是額外的攻擊面；使用者要求「不要被攻擊就下線」

匯率每小時更新一次即可，不需要常駐伺服器。

## 決定

- **GitHub Actions 每小時**（`.github/workflows/update-rates.yml`）執行 `backend/build_data.py`：
  爬蟲 → 合理性檢查 → 更新歷史 → 輸出 `site/data/rates.json`、`history/*.json`、`status.json` → `wrangler deploy`
- **歷史資料存在 git 的 `data` 分支**（`latest.json`、`history/`、`state.json`），與程式碼的 `main` 分支分開
- 網站維持**全靜態**；前端直接讀 `data/*.json`
- 推送到 `main` 也會觸發部署；**不從本機手動部署**（`wrangler.jsonc` 的 build 會執行 `check_site_data.py`，資料缺漏或超過 3 小時即中止）
- 資料品質：同銀行「賣出 < 買入」移除；跨銀行與中位數差距 > 20% 移除（曾發生黃金價誤判為美元）
- 單一銀行失敗時沿用其上次成功資料（前端依 `updated_at` 標示過舊）；連續失敗 3 次發 Discord 通知（選用）

## 考慮過的選項

| 選項 | 不採用原因 |
|---|---|
| Render 付費（約 US$7／月起＋磁碟） | 要付費；仍有公開伺服器 |
| Render 免費＋外部喚醒 | 資料仍會隨重啟消失；違反服務使用精神 |
| Cloudflare Worker cron ＋ D1 | 需以 JavaScript 重寫所有爬蟲 |

## 後果

- 移除 `backend/main.py`、`scheduler.py`、`database.py`、`render.yaml`、`Procfile`、`site/data/mock-rates.json`（保留在 git 歷史）
- 依賴只剩 requests、beautifulsoup4、lxml、python-dotenv
- GitHub 排程可能延遲數分鐘至數十分鐘；公開 repo 若 60 天無活動排程會被停用（data 分支每小時的 commit 會維持活動）
- 走勢資料從 2026-10-18 開始累積
