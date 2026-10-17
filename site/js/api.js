/* ══════════════════════════════════════════════════
   API Client  |  Mock mode → real backend ready
   後端上線後：把 API_BASE 換成 Render URL，USE_MOCK 改 false
   ══════════════════════════════════════════════════ */

const API_BASE = 'https://your-app.onrender.com';  // 後端上線後填入
const USE_MOCK = true;                               // 後端上線後改 false
const STALE_HOURS = 4;

/* 模擬資料模式：頁面頂端顯示警示，避免使用者誤以為是真實匯率 */
if (USE_MOCK) {
  document.addEventListener('DOMContentLoaded', () => {
    const banner = document.createElement('div');
    banner.className = 'alert alert-warning';
    banner.style.margin = '0';
    banner.style.borderRadius = '0';
    banner.textContent = '⚠️ 測試版：本頁匯率為某一時間點的資料快照，不是即時報價，換匯前請以銀行公告為準。';
    document.body.prepend(banner);
  });
}

const FETCH_TIMEOUT_MS  = 10000;  // 10 秒後中止請求
const FETCH_SLOW_MS     =  5000;  // 5 秒後顯示「載入中」提示

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
    const res = await fetch(url, { signal: controller.signal });
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

/* ─────────────────────────────────────────────────────────────
   Checksum verification (Web Crypto API)
   Python side: sha256(json.dumps(rates, sort_keys=True, separators=(',',':')))
   JS side: sha256(sortedJsonStringify(rates))
   ───────────────────────────────────────────────────────────── */
function _sortedJsonStringify(val) {
  if (Array.isArray(val)) {
    return '[' + val.map(_sortedJsonStringify).join(',') + ']';
  }
  if (val !== null && typeof val === 'object') {
    const keys = Object.keys(val).sort();
    return '{' + keys.map(k => JSON.stringify(k) + ':' + _sortedJsonStringify(val[k])).join(',') + '}';
  }
  return JSON.stringify(val);
}

async function _verifyChecksum(data) {
  if (!data.checksum || !data.checksum.startsWith('sha256:')) return true;
  if (!window.crypto?.subtle) return true;  // 舊瀏覽器跳過驗證

  const expected = data.checksum.slice(7);
  try {
    const ratesStr  = _sortedJsonStringify(data.rates);
    const msgBuf    = new TextEncoder().encode(ratesStr);
    const hashBuf   = await crypto.subtle.digest('SHA-256', msgBuf);
    const actual    = Array.from(new Uint8Array(hashBuf))
                           .map(b => b.toString(16).padStart(2, '0')).join('');
    return actual === expected;
  } catch {
    return true;  // 驗證失敗視為通過（降級）
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

/* ─────────────────────────────────────────────────────────────
   GET /api/rates
   ───────────────────────────────────────────────────────────── */
async function fetchRates({ onSlow } = {}) {
  if (USE_MOCK) {
    const res  = await _fetchWithTimeout('data/mock-rates.json', { onSlow });
    const data = await res.json();
    return data;
  }

  const res  = await _fetchWithTimeout(`${API_BASE}/api/rates`, { onSlow });
  const data = await res.json();

  const ok = await _verifyChecksum(data);
  if (!ok) {
    console.error('[Security] checksum mismatch — refusing to render');
    throw new Error('資料完整性驗證失敗，請重新整理頁面');
  }

  return data;
}

/* ─────────────────────────────────────────────────────────────
   GET /api/rates/history
   ───────────────────────────────────────────────────────────── */
async function fetchHistory(currency = 'JPY', days = 365, { onSlow } = {}) {
  if (USE_MOCK) {
    return { currency, data: generateMockHistory(currency, days) };
  }
  const res = await _fetchWithTimeout(
    `${API_BASE}/api/rates/history?currency=${currency}&days=${days}`,
    { onSlow }
  );
  return res.json();
}

/* ── Mock history generator ── */
function generateMockHistory(currency = 'JPY', days = 365) {
  const today = new Date();
  const data  = [];
  const config = {
    JPY: { base: 0.213, volatility: 0.004, trend: -0.008 },
    USD: { base: 31.5,  volatility: 0.3,   trend: 0.5    },
  };
  const cfg = config[currency] || config.JPY;
  let rate   = cfg.base;

  for (let i = days; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    if (d.getDay() === 0 || d.getDay() === 6) continue;
    const change = (Math.random() - 0.499) * cfg.volatility + (cfg.trend / days);
    rate = Math.max(cfg.base * 0.85, Math.min(cfg.base * 1.15, rate + change));
    data.push({
      date:      d.toISOString().split('T')[0],
      spot_buy:  +( rate * 0.994).toFixed(4),
      spot_sell: +(rate * 1.006).toFixed(4),
    });
  }
  return data;
}

/* ── Static JSON files ── */
async function fetchCreditCards() {
  try {
    const res = await _fetchWithTimeout('data/credit-cards.json');
    return res.json();
  } catch (err) {
    console.error('fetchCreditCards:', err);
    throw new Error('功能暫時無法使用');
  }
}

async function fetchBankFees() {
  try {
    const res = await _fetchWithTimeout('data/bank-fees.json');
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
