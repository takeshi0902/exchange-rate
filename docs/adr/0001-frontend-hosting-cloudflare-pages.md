# ADR 0001：前端部署於 Cloudflare Pages，前後端分資料夾

- 日期：2026-10-17
- 狀態：已採用

## 背景

日本退稅新制文章需在 2026-11-01 前上線，作為流量實驗。使用者要求網站不易因攻擊下線、易維護、好加新功能。

## 決定

1. 前端靜態檔集中在 `site/`，後端維持在 `backend/`。部署時只上傳 `site/`，避免後端程式碼與設定被公開。
2. 前端部署於 Cloudflare（免費方案）。實際部署時 wrangler 4.151 將專案建立為 Workers 靜態資產（新版 Pages），設定檔為根目錄 `wrangler.jsonc`（`assets.directory = "site"`），以 `npx wrangler deploy` 部署。
3. 安全標頭由 `site/_headers` 設定。

## 考慮過的選項

| 選項 | 優點 | 缺點 |
|---|---|---|
| Cloudflare Pages | 免費、CDN、內建 DDoS 防護、免費流量分析 | 需 Cloudflare 帳號 |
| GitHub Pages | 設定最簡單 | 無內建流量分析；整個 repo 公開時需另外處理後端資料夾 |
| Netlify | 操作簡單 | 免費額度有流量上限 |

## 後果

- 匯率工具頁目前使用模擬資料（`site/js/api.js` 中 `USE_MOCK = true`），頁面頂端顯示「模擬資料」警示，後端上線後移除。
- 之後若建立 GitHub repo，可改為 Cloudflare Pages 的 Git 整合，push 即自動部署，輸出目錄設為 `site`。
