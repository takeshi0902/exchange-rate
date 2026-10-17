/* ══════════════════════════════════════════════════
   資料讀取
   匯率由 GitHub Actions 每小時爬取後，以靜態 JSON 部署在本站 data/ 底下
   （backend/build_data.py、.github/workflows/update-rates.yml）
   ══════════════════════════════════════════════════ */

const STALE_HOURS = 4;   // 超過幾小時沒更新視為資料過舊

const FETCH_TIMEOUT_MS  = 10000;  // 10 秒後中止請求
const FETCH_SLOW_MS     =  5000;  // 5 秒後顯示「載入中」提示

/* 所有頁面都在根目錄或 articles/ 底下 */
const DATA_BASE = location.pathname.includes('/articles/') ? '../data/' : 'data/';

/* ─────────────────────────────────────────────────────────────
   Timeout-aware fetch
   onSlow: 超過 5 秒時呼叫（可用來更新 loading UI）
   ───────────────────────────────────────────────────────────── */
async function _fetchWithTimeout(url, { onSlow } = {}) {
  const controller = new AbortController();
  let slowTimer;

  if (typeof onSlow === 'function') {
    slowTimer = setTimeout(onSlow, FETCH_SLOW_MS);
  }
  const abortTimer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  try {
    // no-cache：每次向伺服器確認是否有新版（未變更時只回 304，不會重新下載）
    const res = await fetch(url, { signal: controller.signal, cache: 'no-cache' });
    clearTimeout(abortTimer);
    clearTimeout(slowTimer);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res;
  } catch (err) {
    clearTimeout(abortTimer);
    clearTimeout(slowTimer);
    if (err.name === 'AbortError') {
      throw new Error('資料載入逾時（10 秒），請確認網路連線後重試');
    }
    throw err;
  }
}

/* ── Stale check ── */
function isStale(updatedAt) {
  if (!updatedAt) return true;
  return Date.now() - new Date(updatedAt).getTime() > STALE_HOURS * 3600 * 1000;
}

function isRecent(updatedAt) {
  if (!updatedAt) return false;
  return Date.now() - new Date(updatedAt).getTime() < 120 * 60 * 1000;
}

/* 各銀行最新匯率 */
async function fetchRates({ onSlow } = {}) {
  const res = await _fetchWithTimeout(DATA_BASE + 'rates.json', { onSlow });
  return res.json();
}

/* 歷史走勢（各銀行即期平均，每日一筆）；尚無資料的幣別回傳空陣列 */
async function fetchHistory(currency = 'JPY', days = 365, { onSlow } = {}) {
  let data = [];
  try {
    const res = await _fetchWithTimeout(`${DATA_BASE}history/${currency}.json`, { onSlow });
    data = (await res.json()).data || [];
  } catch (err) {
    if (!String(err.message).includes('404')) throw err;
  }
  const cutoff = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
  return { currency, data: data.filter(d => d.date >= cutoff) };
}

/* ── Static JSON files ── */
async function fetchCreditCards() {
  try {
    const res = await _fetchWithTimeout(DATA_BASE + 'credit-cards.json');
    return res.json();
  } catch (err) {
    console.error('fetchCreditCards:', err);
    throw new Error('功能暫時無法使用');
  }
}

async function fetchBankFees() {
  try {
    const res = await _fetchWithTimeout(DATA_BASE + 'bank-fees.json');
    return res.json();
  } catch (err) {
    console.error('fetchBankFees:', err);
    throw new Error('功能暫時無法使用');
  }
}

/* ─────────────────────────────────────────────────────────────
   Helpers
   ───────────────────────────────────────────────────────────── */
function getBestRate(rates, currency, field) {
  let best = null, bestBank = null;
  rates.forEach(b => {
    const r   = b[currency];
    if (!r || r[field] == null) return;
    const val = r[field];
    if (field === 'spot_buy' || field === 'cash_buy') {
      if (best === null || val > best) { best = val; bestBank = b.bank_code; }
    } else {
      if (best === null || val < best) { best = val; bestBank = b.bank_code; }
    }
  });
  return { best, bestBank };
}

function formatRate(val, currency) {
  if (val == null) return '—';
  return currency === 'JPY' ? val.toFixed(4) : val.toFixed(3);
}

function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('zh-TW') + ' ' +
    d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
}

function formatTimeAgo(iso) {
  if (!iso) return '—';
  const mins = Math.round((Date.now() - new Date(iso)) / 60000);
  if (mins < 1)  return '剛剛更新';
  if (mins < 60) return `${mins} 分鐘前`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs} 小時前`;
  return `${Math.floor(hrs / 24)} 天前`;
}

/* 暫停中的銀行（API 的 unavailable 欄位），回傳一行說明文字；沒有則回傳空字串 */
function unavailableText(data) {
  const list = data?.unavailable || [];
  if (!list.length) return '';
  return `${list.map(b => b.bank_name).join('、')}官網目前限制程式讀取，暫時沒有列入比較。`;
}

/* 統一錯誤訊息：用戶看到友善提示，細節寫 console.error */
function showError(containerEl, err, fallbackMsg = '功能暫時無法使用，請稍後再試') {
  console.error(err);
  if (containerEl) {
    containerEl.innerHTML =
      `<div class="alert alert-error" style="margin:0">${fallbackMsg}</div>`;
  }
}
