/* Small SVG chart primitives.
   No library: every chart here is a handful of paths, and a charting dependency
   would be larger than the charts. Everything draws with design tokens, so the
   charts follow the theme without a second palette to keep in sync. */

const NS = 'http://www.w3.org/2000/svg';

export function el(name, attrs = {}, children = []) {
  const n = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return n;
}

export function svg(w, h, extra = {}) {
  const n = el('svg', {
    viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: 'xMidYMid meet', role: 'img', ...extra,
  });
  // width/height belong in CSS: "auto" is not a valid SVG length attribute.
  n.style.width = '100%';
  n.style.height = 'auto';
  n.style.display = 'block';
  return n;
}

export const scale = (d0, d1, r0, r1) => v =>
  d1 === d0 ? r0 : r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);

export const fmt = {
  pct: v => `${Math.round(v * 100)}%`,
  n: v => v.toLocaleString('en-GB'),
  money: v => '€' + Math.round(v).toLocaleString('en-GB'),
  compact: v => Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 1 }).format(v),
};

/* ---- axes -------------------------------------------------------------- */
function axes(g, { x, y, w, h, pad, xTicks, yTicks, xLabel, yLabel }) {
  const line = (a, b, c, d) => el('line', {
    x1: a, y1: b, x2: c, y2: d, stroke: 'var(--line)', 'stroke-width': 1,
  });
  g.appendChild(line(pad.l, h - pad.b, w - pad.r, h - pad.b));
  g.appendChild(line(pad.l, pad.t, pad.l, h - pad.b));

  for (const t of yTicks || []) {
    const yy = y(t.v);
    g.appendChild(el('line', {
      x1: pad.l, y1: yy, x2: w - pad.r, y2: yy,
      stroke: 'var(--line)', 'stroke-width': 1, opacity: .5,
      'stroke-dasharray': t.dashed ? '3 3' : null,
    }));
    g.appendChild(el('text', {
      x: pad.l - 7, y: yy + 3.5, 'text-anchor': 'end',
      fill: 'var(--faint)', 'font-size': 11, 'font-family': 'var(--font-mono)',
    }, t.label));
  }
  for (const t of xTicks || []) {
    g.appendChild(el('text', {
      x: x(t.v), y: h - pad.b + 14, 'text-anchor': 'middle',
      fill: 'var(--faint)', 'font-size': 11, 'font-family': 'var(--font-mono)',
    }, t.label));
  }
  if (xLabel) g.appendChild(el('text', {
    x: (pad.l + w - pad.r) / 2, y: h - 2, 'text-anchor': 'middle',
    fill: 'var(--faint)', 'font-size': 11.5,
  }, xLabel));
  if (yLabel) g.appendChild(el('text', {
    x: 13, y: (pad.t + h - pad.b) / 2, 'text-anchor': 'middle',
    fill: 'var(--faint)', 'font-size': 11.5,
    transform: `rotate(-90 13 ${(pad.t + h - pad.b) / 2})`,
  }, yLabel));
}

const path = pts => pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join('');

/* ---- line chart --------------------------------------------------------
   series: [{ points:[[x,y]...], stroke, dashed, label, fill }] */
export function lineChart(node, {
  series, w = 640, h = 300, pad = { t: 14, r: 16, b: 30, l: 44 },
  xDomain, yDomain, xTicks, yTicks, xLabel, yLabel, diagonal = false, title,
}) {
  const all = series.flatMap(s => s.points);
  const xd = xDomain || [Math.min(...all.map(p => p[0])), Math.max(...all.map(p => p[0]))];
  const yd = yDomain || [Math.min(...all.map(p => p[1])), Math.max(...all.map(p => p[1]))];
  const x = scale(xd[0], xd[1], pad.l, w - pad.r);
  const y = scale(yd[0], yd[1], h - pad.b, pad.t);

  const s = svg(w, h, { 'aria-label': title || 'chart' });
  axes(s, { x, y, w, h, pad, xTicks, yTicks, xLabel, yLabel });

  if (diagonal) {
    s.appendChild(el('line', {
      x1: x(xd[0]), y1: y(yd[0]), x2: x(xd[1]), y2: y(yd[1]),
      stroke: 'var(--faint)', 'stroke-width': 1, 'stroke-dasharray': '4 4', opacity: .8,
    }));
  }
  for (const ser of series) {
    const pts = ser.points.map(p => [x(p[0]), y(p[1])]);
    if (ser.fill) {
      s.appendChild(el('path', {
        d: path(pts) + `L${x(xd[1])} ${y(yd[0])}L${x(xd[0])} ${y(yd[0])}Z`,
        fill: ser.fill, opacity: .12, stroke: 'none',
      }));
    }
    s.appendChild(el('path', {
      d: path(pts), fill: 'none', stroke: ser.stroke || 'var(--signal)',
      'stroke-width': ser.width || 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
      'stroke-dasharray': ser.dashed ? '5 4' : null,
    }));
    if (ser.dots) {
      for (const p of pts) {
        s.appendChild(el('circle', { cx: p[0], cy: p[1], r: 2.6, fill: ser.stroke || 'var(--signal)' }));
      }
    }
  }
  node.replaceChildren(s);
  return { svg: s, x, y, pad, w, h };
}

/* ---- histogram --------------------------------------------------------- */
export function barChart(node, {
  bars, w = 640, h = 260, pad = { t: 14, r: 16, b: 34, l: 44 },
  xTicks, yTicks, xLabel, yLabel, colour = 'var(--signal)', markers = [], title,
}) {
  const maxY = Math.max(...bars.map(b => b.v), 1);
  const x = scale(0, bars.length, pad.l, w - pad.r);
  const y = scale(0, maxY, h - pad.b, pad.t);
  const bw = (w - pad.l - pad.r) / bars.length;

  const s = svg(w, h, { 'aria-label': title || 'histogram' });
  axes(s, { x, y, w, h, pad, xTicks: null, yTicks, xLabel, yLabel });

  bars.forEach((b, i) => {
    const height = (h - pad.b) - y(b.v);
    const rect = el('rect', {
      x: x(i) + 0.7, y: y(b.v), width: Math.max(1, bw - 1.4), height: Math.max(0, height),
      fill: b.colour || colour, rx: 1.5,
    });
    if (b.label) rect.appendChild(el('title', {}, b.label));
    s.appendChild(rect);
  });

  for (const t of xTicks || []) {
    s.appendChild(el('text', {
      x: x(t.i), y: h - pad.b + 14, 'text-anchor': 'middle',
      fill: 'var(--faint)', 'font-size': 11, 'font-family': 'var(--font-mono)',
    }, t.label));
  }
  for (const m of markers) {
    const mx = x(m.i);
    s.appendChild(el('line', {
      x1: mx, y1: pad.t - 4, x2: mx, y2: h - pad.b,
      stroke: m.colour || 'var(--predict)', 'stroke-width': 1.6, 'stroke-dasharray': '4 3',
    }));
    s.appendChild(el('text', {
      x: mx + 5, y: pad.t + 6, fill: m.colour || 'var(--predict)',
      'font-size': 11.5, 'font-family': 'var(--font-mono)',
    }, m.label));
  }
  node.replaceChildren(s);
  return { svg: s, x, y, pad, w, h };
}

/* ---- the trajectory field ----------------------------------------------
   The hero backdrop. Real delinquency paths, one per lane: the quiet ones rule
   the ground, the bending ones spike out of it. Keeping each path inside its
   own lane is what makes it read as a population rather than a wire mesh --
   and the spikes are the only thing that should catch the eye, because they
   are the only thing the Risk Lens is for. */
export function trajectoryField(node, { quiet, bending, w = 1400, h = 560, maxBucket = 6 }) {
  const s = svg(w, h, { 'aria-hidden': 'true', preserveAspectRatio: 'none' });
  s.style.height = '100%';   // the field stretches to its container, unlike a chart

  // One lane per path, and few enough lanes that a bend stays legible instead of
  // tangling with its neighbours. The JSON holds the full sample; the backdrop
  // draws a readable slice of it.
  const LANES = 46, BEND_SHARE = 12;
  const take = (arr, n) => {
    const step = Math.max(1, Math.floor(arr.length / n));
    return Array.from({ length: n }, (_, i) => arr[(i * step) % arr.length]).filter(Boolean);
  };
  const picked = [
    ...take(quiet, LANES - BEND_SHARE).map(d => ({ d, bend: false })),
    ...take(bending, BEND_SHARE).map(d => ({ d, bend: true })),
  ];
  // Scatter the bending paths through the field rather than stacking them at
  // the bottom, which is what the concatenation above would otherwise give.
  const rows = [];
  const every = Math.round(picked.length / BEND_SHARE);
  const quietQ = picked.filter(r => !r.bend), bendQ = picked.filter(r => r.bend);
  for (let i = 0; rows.length < picked.length; i++) {
    rows.push(i % every === 2 && bendQ.length ? bendQ.shift() : quietQ.shift() || bendQ.shift());
  }

  const laneH = h / rows.length;
  const gQuiet = el('g', { fill: 'none', stroke: 'var(--faint)', 'stroke-width': 1, opacity: 0.22 });
  const gBend = el('g', { fill: 'none', stroke: 'var(--predict)', 'stroke-width': 1.5, opacity: 0.6 });

  rows.forEach((row, i) => {
    const base = laneH * (i + 0.5);
    const n = row.d.length;
    const pts = row.d.map((v, j) => [
      (j / (n - 1)) * w,
      base - (Math.min(v, maxBucket) / maxBucket) * laneH * 2.1,
    ]);
    (row.bend ? gBend : gQuiet).appendChild(el('path', { d: path(pts) }));
  });

  s.appendChild(gQuiet);
  s.appendChild(gBend);
  node.replaceChildren(s);
  return s;
}

/* ---- sparkline ---------------------------------------------------------- */
export function sparkline(values, { w = 96, h = 24, stroke = 'var(--signal)' } = {}) {
  const lo = Math.min(...values), hi = Math.max(...values);
  const x = scale(0, values.length - 1, 1, w - 1);
  const y = scale(lo, hi, h - 2, 2);
  const s = svg(w, h, { 'aria-hidden': 'true' });
  s.appendChild(el('path', {
    d: path(values.map((v, i) => [x(i), y(v)])),
    fill: 'none', stroke, 'stroke-width': 1.5, 'stroke-linejoin': 'round',
  }));
  return s;
}

/* ---- provenance badge, from a data record ------------------------------- */
export function badge(record) {
  const span = document.createElement('span');
  span.className = `badge badge-${record.provenance}`;
  span.textContent = record.provenance;
  if (record.source) span.title = `${record.source}${record.note ? ' — ' + record.note : ''}`;
  return span;
}

export async function loadData(name) {
  const res = await fetch(`data/${name}.json`);
  if (!res.ok) throw new Error(`${name}.json: ${res.status}`);
  return res.json();
}
