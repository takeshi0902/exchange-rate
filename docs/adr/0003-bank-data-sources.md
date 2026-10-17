# ADR 0003：銀行匯率資料來源與擴充方式

- 日期：2026-10-18
- 狀態：已採用

## 背景

使用者要求擴充涵蓋銀行（新增中信、台新、富邦、永豐、華南、彰化、土銀）並抓取各行公布的所有幣別，同時修正既有爬蟲。

## 決定

1. **優先使用官網頁面本身載入的 JSON API**，其次解析靜態 HTML；全部以一般 HTTP 請求取得，**移除 Playwright**（部署更輕、速度更快、較不易壞）。
2. **不繞過任何防機器人機制**。遇到驗證頁或封鎖的銀行設為 `enabled = False`，並在 API 的 `unavailable` 欄位回報原因，前端顯示「暫時沒有列入比較」。
3. 新增銀行 = 在 `backend/scrapers/` 新增一個檔案並加入 `ALL_SCRAPERS`；幣別名稱辨識、數值解析集中在 `scrapers/base.py`（`currency_code`、`RateBook`）。
4. 走勢圖與 USD/JPY 參考值改用**各銀行平均**，不依賴單一銀行。

## 各銀行來源（2026-10-18 實測）

| 代碼 | 銀行 | 來源 | 幣別數 | 現鈔 |
|---|---|---|---|---|
| MEGA | 兆豐 | JSON API `GetRateData` | 20 | 18 |
| ESUN | 玉山 | 頁面 JSON-LD | 15 | 8 |
| CATHAY | 國泰世華 | 無障礙版 HTML 表格 | 16 | 5 |
| TCB | 合作金庫 | JSON API `GetSpotForeignExchange`（需頁面 token） | 14 | 6 |
| FIRST | 第一 | HTML（Big5） | 15 | 8 |
| TAISHIN | 台新 | `transactionrateExport.jsp`（document.writeln） | 14 | 9 |
| FUBON | 台北富邦 | HTML 表格 | 14 | 7 |
| SINOPAC | 永豐 | JSON API `ws_exchange.ashx`（REMIT / CASH） | 16 | 5 |
| HNCB | 華南 | JSON API `exRate/all` | 14 | 0（官網無現鈔 API） |
| CHB | 彰化 | JSON API `getG0100_query.jsp` | 14 | 5 |
| LANDBANK | 土地 | HTML 表格 | 14 | 7 |
| BOT | 台灣銀行 | **暫停**：加入 Challenge Validation；官方開放資料 API 各年度皆無資料 | — | — |
| CTBC | 中國信託 | **暫停**：頁面回 202 空殼，無資料 | — | — |

robots.txt：上述使用的路徑皆未被禁止 `[已驗證]`。各行網站使用條款是否限制程式讀取：**尚未逐一審閱** `[假設]`，列入待驗證。

## 考慮過的選項

| 選項 | 不採用原因 |
|---|---|
| 以 Playwright 模擬瀏覽器通過台銀 / 中信驗證 | 屬繞過存取控制，有法律與封鎖風險 |
| 使用第三方匯率彙整網站資料 | 授權不明、多一層延遲與錯誤 |
| 保留 Playwright 抓兆豐、合庫 | 兩行皆有可直接呼叫的 JSON API |

## 後果

- 爬蟲輸出格式改為 `{"bank_code", "bank_name", "rates": {幣別: {...}}}`
- 銀行代碼變更：國泰世華 `CTBC → CATHAY`（CTBC 改指中國信託）、合作金庫 `TCFB → TCB`。後端尚未上線，無既有資料需遷移
- 國泰世華另有「數位通路優惠匯率」，目前未收錄（需擴充資料表）
