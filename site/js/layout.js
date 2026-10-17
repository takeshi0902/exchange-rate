/* ── Shared Navigation & Footer injection ── */
(function () {
  const currentPage = location.pathname.split('/').pop() || 'index.html';
  // 子資料夾（如 articles/）內的頁面需加上 ../ 才能連回根目錄
  const base = location.pathname.includes('/articles/') ? '../' : '';
  // 資料來源銀行（與 backend/scrapers 啟用中的銀行一致）
  const SOURCE_BANKS = '兆豐銀行、玉山銀行、國泰世華、合作金庫、第一銀行、台新銀行、台北富邦、永豐銀行、華南銀行、彰化銀行、土地銀行';

  function navActive(href) {
    // 文章區以資料夾判斷，避免與首頁的 index.html 混淆
    if (href === 'articles/index.html') return base ? 'class="active"' : '';
    // 主機可能省略 .html（如 /compare），比對前統一去掉副檔名
    const strip = (s) => s.replace(/\.html$/, '');
    return strip(href) === strip(currentPage) ? 'class="active"' : '';
  }

  const NAV_HTML = `
<nav class="nav">
  <div class="nav-inner">
    <a class="nav-logo" href="${base}index.html">換匯<span>比較網</span></a>
    <ul class="nav-links">
      <li><a href="${base}compare.html" ${navActive('compare.html')}>匯率比較</a></li>
      <li><a href="${base}triangle.html" ${navActive('triangle.html')}>三角換匯</a></li>
      <li><a href="${base}credit-card.html" ${navActive('credit-card.html')}>信用卡試算</a></li>
      <li><a href="${base}history.html" ${navActive('history.html')}>歷史走勢</a></li>
      <li><a href="${base}articles/index.html" ${navActive('articles/index.html')}>換匯知識</a></li>
    </ul>
    <button class="nav-hamburger" id="hamburger" aria-label="選單">☰</button>
  </div>
</nav>
<div class="nav-mobile" id="mobileMenu">
  <div class="nav-mobile-panel">
    <a href="${base}index.html">🏠 首頁</a>
    <a href="${base}compare.html">📊 匯率比較表</a>
    <a href="${base}triangle.html">🔺 三角換匯試算</a>
    <a href="${base}credit-card.html">💳 信用卡試算</a>
    <a href="${base}history.html">📈 歷史走勢圖</a>
    <a href="${base}articles/index.html">📖 換匯知識</a>
    <a href="${base}about.html">關於我們</a>
    <a href="${base}contact.html">聯絡我們</a>
  </div>
</div>`;

  const FOOTER_HTML = `
<footer class="footer">
  <div class="footer-inner">
    <div>
      <div class="footer-brand">換匯比較網</div>
      <p class="footer-desc">整合台灣各大銀行即時匯率，提供三角換匯試算、信用卡成本比較，幫助您找到最划算的換匯方式。</p>
    </div>
    <div class="footer-col">
      <h4>核心工具</h4>
      <ul>
        <li><a href="${base}compare.html">匯率比較表</a></li>
        <li><a href="${base}triangle.html">三角換匯試算</a></li>
        <li><a href="${base}credit-card.html">信用卡試算</a></li>
        <li><a href="${base}history.html">歷史走勢圖</a></li>
      </ul>
    </div>
    <div class="footer-col">
      <h4>其他頁面</h4>
      <ul>
        <li><a href="${base}articles/index.html">換匯知識文章</a></li>
        <li><a href="${base}about.html">關於我們</a></li>
        <li><a href="${base}contact.html">聯絡我們</a></li>
        <li><a href="${base}privacy.html">隱私權政策</a></li>
        <li><a href="${base}disclaimer.html">免責聲明</a></li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <span>© 2026 換匯比較網。保留一切權利。</span>
    <span><a href="${base}disclaimer.html">免責聲明</a>｜<a href="${base}privacy.html">隱私權政策</a>｜<a href="${base}sitemap.xml">Sitemap</a></span>
  </div>
  <div class="container mt-16">
    <div class="disclaimer">
      <strong>資料來源：</strong>${SOURCE_BANKS}（各行官網公告牌告匯率）。台灣銀行、中國信託官網目前限制程式讀取，暫未列入。
      本站自動爬取各行公開資料，與各銀行無從屬或合作關係，著作權歸各銀行所有。<br>
      <strong>免責聲明：</strong>本站所顯示之匯率資料僅供參考，不構成換匯建議或財務諮詢。
      實際換匯匯率以各銀行現場公告為準，匯率隨時波動，本站不承擔任何因使用本資料而產生之損失責任。
    </div>
  </div>
</footer>`;

  // Inject nav
  const navEl = document.getElementById('nav-placeholder');
  if (navEl) navEl.outerHTML = NAV_HTML;

  // Inject footer
  const footerEl = document.getElementById('footer-placeholder');
  if (footerEl) footerEl.outerHTML = FOOTER_HTML;

  // Hamburger toggle
  document.addEventListener('click', (e) => {
    const ham  = document.getElementById('hamburger');
    const menu = document.getElementById('mobileMenu');
    if (!ham || !menu) return;
    if (ham.contains(e.target)) {
      menu.classList.toggle('open');
    } else if (menu.classList.contains('open') && !menu.querySelector('.nav-mobile-panel').contains(e.target)) {
      menu.classList.remove('open');
    }
  });
})();
