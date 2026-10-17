# 換匯比較網

本專案依 `product-playbook` skill 的一人產品團隊流程開發。

## 目前階段

**階段 1：市場研究**（階段 0 未過關，使用者決定有條件繼續，見 `docs/00-opportunity.md`）

進行中實驗：日本退稅新制文章上線測流量（2026-10-17 起），結果納入 `docs/01-market.md`。

已知待辦：後端未部署，前端仍用 2026-10-18 實抓快照（`USE_MOCK = true`）；台銀、中信暫停；`data/bank-fees.json` 只有舊 6 家且含台銀；`articles/index.html` 另 3 篇文章、`contact.html`、`sitemap.xml` 尚不存在；`robots.txt` 網域待填。

## 專案結構

- 前端：`site/`（靜態 HTML ＋ `css/`、`js/`、`data/`），部署於 Cloudflare Pages，見 `docs/adr/0001-*`
- 部署：`npx wrangler deploy`（設定在 `wrangler.jsonc`，只上傳 `site/`）
- 網址：https://exchange-rate.exchange-rate.workers.dev
- 後端：`backend/`（Python，銀行爬蟲、排程、通知，預計部署於 Render，尚未上線）
  - 爬蟲：`backend/scrapers/` 一行一檔，註冊於 `__init__.py`；資料來源見 `docs/adr/0003-*`
  - 實測：`cd backend && .venv/Scripts/python test_scrapers.py`
- 文件：`docs/`（各階段產出）、`docs/adr/`（技術決策）

## 規則

- 開始新階段前先讀前一階段文件，確認過關狀態
- 事實性資料需附來源與可信度標籤，不得自行生成
- 參數放 `config/`，機密放 `.env`，不寫死在程式碼
- 不自動 commit
