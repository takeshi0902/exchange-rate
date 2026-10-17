# 換匯比較網

本專案依 `product-playbook` skill 的一人產品團隊流程開發。

## 目前階段

**階段 1：市場研究**（階段 0 未過關，使用者決定有條件繼續，見 `docs/00-opportunity.md`）

進行中實驗：日本退稅新制文章上線測流量（2026-10-17 起），結果納入 `docs/01-market.md`。

流量分析：Cloudflare Web Analytics（2026-10-18 起）；Google Search Console 已驗證（`site/googleb9690c46a79fca48.html` 勿刪）。新增頁面要同步加入 `site/sitemap.xml`。

已知待辦：台銀、中信暫停；`data/bank-fees.json` 只有舊 6 家且含台銀；`articles/index.html` 另 3 篇文章、`contact.html` 尚不存在。

## 專案結構

- 前端：`site/`（全靜態 HTML ＋ `css/`、`js/`、`data/`），部署於 Cloudflare（Workers 靜態資產），見 ADR 0001
- 匯率資料：GitHub Actions 每小時執行 `backend/build_data.py` → 產生 `site/data/rates.json`、`history/` → 部署，見 ADR 0004
  - 歷史資料在 git 的 `data` 分支；`site/data/rates.json` 等為產生檔，不進 main
  - 爬蟲：`backend/scrapers/` 一行一檔，註冊於 `__init__.py`；資料來源見 ADR 0003
  - 離線測試：`backend/.venv/Scripts/python -m unittest discover -s backend/tests`
  - 實際連線測試：`cd backend && .venv/Scripts/python test_scrapers.py`
- **部署**：推送到 main 或在 GitHub Actions 手動執行「更新匯率並部署」。不要從本機 `wrangler deploy`（會被 `check_site_data.py` 擋下）
- 網址：https://exchange-rate.exchange-rate.workers.dev
- GitHub：https://github.com/takeshi0902/exchange-rate（公開；secrets：CLOUDFLARE_API_TOKEN、CLOUDFLARE_ACCOUNT_ID，選用 DISCORD_WEBHOOK_URL）
- 文件：`docs/`（各階段產出）、`docs/adr/`（技術決策）

## 規則

- 開始新階段前先讀前一階段文件，確認過關狀態
- 事實性資料需附來源與可信度標籤，不得自行生成
- 參數放 `config/`，機密放 `.env`，不寫死在程式碼
- 不自動 commit
