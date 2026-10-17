# 開發紀錄

| 日期 | 階段 | 內容 |
|---|---|---|
| 2026-10-17 | 0 | 導入 product-playbook 流程；git init；完成選題評分（30 分，未過關，使用者決定有條件繼續） |
| 2026-10-17 | 1（實驗） | 日本退稅新制文章 `site/articles/japan-tax-refund-2026.html`（來源：日本觀光廳）；前端移至 `site/`；修正 articles/ 子資料夾導覽連結；模擬資料警示橫幅；安全標頭 `_headers`；ADR 0001 部署於 Cloudflare Pages |
| 2026-10-17 | 1（實驗） | 首次上線 https://exchange-rate.exchange-rate.workers.dev （Cloudflare Workers 靜態資產）；驗證：頁面 200、`/backend/` 等 404、安全標頭生效；修正主機省略 .html 時導覽列 active 判斷 |
| 2026-10-18 | — | 安裝 `frontend-design` skill（anthropics/skills，專案層級）作為前端設計指引；試裝的 `design-taste-frontend` 已移除（不適用工具頁） |
| 2026-10-18 | 4（提前） | 視覺改版「登機證」：重寫 `site/css/style.css` 為 token 化設計系統（docs/04-design.md、ADR 0002）；首頁主視覺改登機證；移除標題 emoji；走勢圖改讀 CSS 變數；修正 `.page-body` 吃掉 `.container` 左右留白、導覽列「換匯知識」誤標；已部署並以 375px / 1280px 截圖檢查 |
| 2026-10-18 | 5（提前） | 爬蟲改版（ADR 0003）：新增台新、富邦、永豐、華南、彰化、土銀；抓各行所有幣別；全面改用 HTTP／JSON API 並移除 Playwright；台銀、中信因防機器人機制暫停；修正國泰代碼、合庫現鈔、台新黃金誤判成 USD、走勢日期時區、前端 `bank` 欄位與 `usd_jpy` 缺漏；前端 mock 改為實抓快照並標示暫停銀行；11 家實測全數成功 |
| 2026-10-18 | — | 信用卡資料與試算修正：聯邦「賤卡」→「賴點卡」、富邦 J Card →「台北富邦J卡」、台新 @GoGo → Richart 卡（2025-09-01 更名）、中信 LINE Pay 海外回饋 1% → 2.8%；移除查無依據的「海外手續費 0%」；回饋查無現行條件者標「待確認」以 0% 計；修正手續費重複計算（1% ＋ 1.5% → 1.5%）、現金改用現鈔賣出價；卡片資料附來源連結；臨櫃手續費表標示「資料待查證」 |
