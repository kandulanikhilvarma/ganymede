/* Resolve <b data-fig="allocator:headline.lift_pct"> against site/data/*.json.

   Pages do not hard-code numbers. They name one, and this fills in the value
   together with the provenance badge the pipeline attached to it. A figure the
   build script stopped producing renders as a visible dash rather than a stale
   number nobody noticed, and a figure with no provenance cannot be rendered at
   all -- which is the property the whole data layer exists to guarantee. */

const cache = new Map();

async function file(name) {
  if (!cache.has(name)) {
    cache.set(name, fetch(`data/${name}.json`).then(r => {
      if (!r.ok) throw new Error(`${name}.json: ${r.status}`);
      return r.json();
    }));
  }
  return cache.get(name);
}

const dig = (obj, path) => path.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);

const FORMAT = {
  raw: v => String(v),
  n: v => Number(v).toLocaleString('en-GB'),
  pct: v => `${v}%`,
  pct01: v => `${Math.round(v * 100)}%`,
  ms: v => `${v} ms`,
  money: v => '€' + Math.round(v).toLocaleString('en-GB'),
  compact: v => Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 1 }).format(v),
  signed: v => (v > 0 ? '+' : '') + v + '%',
  fixed2: v => Number(v).toFixed(2),
};

export function badgeFor(record) {
  const b = document.createElement('span');
  b.className = `badge badge-${record.provenance}`;
  b.textContent = record.provenance;
  const why = record.note ? `${record.source} — ${record.note}` : record.source;
  if (why) b.title = why;
  return b;
}

export async function resolveFigures(scope = document) {
  const nodes = [...scope.querySelectorAll('[data-fig]')];
  await Promise.all(nodes.map(async node => {
    const [name, path] = node.dataset.fig.split(':');
    let record;
    try {
      record = dig(await file(name), path);
    } catch {
      node.textContent = '—';
      node.title = `${node.dataset.fig} could not be loaded`;
      return;
    }
    if (!record || typeof record !== 'object' || !('provenance' in record)) {
      node.textContent = '—';
      node.title = `${node.dataset.fig} is missing or carries no provenance`;
      return;
    }
    const fn = FORMAT[node.dataset.figFormat || 'raw'] || FORMAT.raw;
    node.textContent = record.value === null || record.value === undefined
      ? (node.dataset.figEmpty || 'not yet earned')
      : fn(record.value);
    if (record.value === null) node.classList.add('fig-pending');

    // The badge lands in the nearest [data-badge-slot] going up the tree, so a
    // card's badge stays in that card rather than in whichever one rendered first.
    if (node.dataset.figBadge === 'off') return;
    let slot = null;
    for (let a = node.parentElement; a && !slot; a = a.parentElement) {
      slot = a.querySelector(':scope [data-badge-slot]');
      if (a === scope.body || a === scope.documentElement) break;
    }
    slot = slot || node.parentElement;
    if (slot && !slot.querySelector(`.badge-${record.provenance}`)) {
      slot.appendChild(badgeFor(record));
    }
  }));
}

/* Unwrap a data field that may or may not carry provenance.

   Wrapping a plain number in a provenance record silently turns every raw
   reader of it into "[object Object]" on the page. That happened once, to the
   minimum turn gap on the desk. Read through this and it cannot happen again. */
export function val(field) {
  return field && typeof field === 'object' && 'value' in field ? field.value : field;
}

export { file as loadFile, dig };
