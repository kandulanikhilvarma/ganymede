/* Ganymede site chrome: theme, reading depth, glossary tooltips, nav state.
   The pre-paint half of the theme logic lives inline in each page's <head>;
   this file only wires the controls. */

const root = document.documentElement;

/* ---- theme ------------------------------------------------------------- */
// Dark is the site's default, not the operating system's preference. An
// explicit choice is remembered; absent one, dark is what you get.
function currentTheme() {
  return root.getAttribute('data-theme') || 'dark';
}
function setTheme(t) {
  root.setAttribute('data-theme', t);
  try { localStorage.setItem('gm-theme', t); } catch {}
  document.querySelectorAll('[data-theme-btn]').forEach(b => {
    b.setAttribute('aria-label', t === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
  });
}
document.querySelectorAll('[data-theme-btn]').forEach(b => {
  b.addEventListener('click', () => setTheme(currentTheme() === 'dark' ? 'light' : 'dark'));
});
setTheme(currentTheme());

/* ---- reading depth -----------------------------------------------------
   1 = the 2-minute read, 2 = the 12-minute read, 3 = everything.
   Tiers are additive: a [data-tier="3"] block appears only at depth 3. */
function setDepth(d) {
  root.setAttribute('data-depth', String(d));
  try { localStorage.setItem('gm-depth', String(d)); } catch {}
  document.querySelectorAll('[data-depth-btn]').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.depthBtn === String(d)));
  });
}
document.querySelectorAll('[data-depth-btn]').forEach(b => {
  b.addEventListener('click', () => setDepth(b.dataset.depthBtn));
});
setDepth(root.getAttribute('data-depth') || '2');

/* ---- glossary ----------------------------------------------------------
   Any element with data-term="self-cure" gets a definition on hover/focus.
   The definitions live in one JSON file so the glossary page and the inline
   tooltips can never disagree. */
let TERMS = null;
let tipEl = null;

async function loadTerms() {
  if (TERMS) return TERMS;
  try {
    const res = await fetch(new URL('../../data/glossary.json', import.meta.url));
    TERMS = await res.json();
  } catch { TERMS = {}; }
  return TERMS;
}

// WCAG 1.4.13: the tip must stay while the pointer moves onto it, so leaving
// the term only schedules the hide, and entering the tip cancels it.
let tipOwner = null, hideTimer = 0;

function hideTip() {
  clearTimeout(hideTimer);
  if (tipOwner) tipOwner.removeAttribute('aria-describedby');
  if (tipEl) { tipEl.remove(); tipEl = null; }
  tipOwner = null;
}
function hideTipSoon() { clearTimeout(hideTimer); hideTimer = setTimeout(hideTip, 200); }

async function showTip(el) {
  clearTimeout(hideTimer);
  const terms = await loadTerms();
  const entry = terms[el.dataset.term];
  if (!entry) return;
  hideTip();
  tipOwner = el;
  tipEl = document.createElement('div');
  tipEl.className = 'tip';
  tipEl.id = 'gm-tip';
  tipEl.setAttribute('role', 'tooltip');
  tipEl.addEventListener('mouseenter', () => clearTimeout(hideTimer));
  tipEl.addEventListener('mouseleave', hideTipSoon);
  el.setAttribute('aria-describedby', 'gm-tip');
  tipEl.innerHTML = '<span class="t"></span><span class="d"></span>';
  tipEl.querySelector('.t').textContent = entry.term;
  tipEl.querySelector('.d').textContent = entry.short;
  document.body.appendChild(tipEl);
  const r = el.getBoundingClientRect();
  const w = tipEl.offsetWidth;
  const left = Math.min(Math.max(8, r.left + scrollX), scrollX + innerWidth - w - 8);
  const above = r.top > tipEl.offsetHeight + 16;
  tipEl.style.left = left + 'px';
  tipEl.style.top = (above ? r.top + scrollY - tipEl.offsetHeight - 8 : r.bottom + scrollY + 8) + 'px';
}

function wireTerms(scope = document) {
  scope.querySelectorAll('[data-term]').forEach(el => {
    if (el.dataset.wired) return;
    el.dataset.wired = '1';
    el.classList.add('term');
    el.tabIndex = 0;
    el.addEventListener('mouseenter', () => showTip(el));
    el.addEventListener('focus', () => showTip(el));
    el.addEventListener('mouseleave', hideTipSoon);
    el.addEventListener('blur', hideTip);
  });
}
wireTerms();
addEventListener('scroll', hideTip, { passive: true });
addEventListener('keydown', e => { if (e.key === 'Escape') hideTip(); });

/* ---- nav --------------------------------------------------------------- */
// Production serves clean URLs (/system) while the links say system.html, and
// the local server serves the .html form. Compare page names, not strings.
const page = path => path.split('/').pop().replace(/\.html$/, '') || 'index';
const here = page(location.pathname);
document.querySelectorAll('.navlinks a').forEach(a => {
  if (page(new URL(a.href).pathname) === here) a.setAttribute('aria-current', 'page');
});

const toggle = document.querySelector('[data-nav-toggle]');
function setMenu(open) {
  toggle.closest('.topnav').classList.toggle('open', open);
  toggle.setAttribute('aria-expanded', String(open));
  toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
}
if (toggle) {
  const links = toggle.closest('.topnav').querySelector('.navlinks');
  if (links) {
    links.id ||= 'navlinks';
    toggle.setAttribute('aria-controls', links.id);
    links.addEventListener('click', e => { if (e.target.closest('a')) setMenu(false); });
  }
  toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  addEventListener('keydown', e => {
    if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setMenu(false);
      toggle.focus();
    }
  });
}

export { wireTerms, setTheme, setDepth };
