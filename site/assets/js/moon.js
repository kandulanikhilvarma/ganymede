/* Ganymede, drawn rather than photographed.

   The real moon is the largest in the solar system and the only one with its
   own magnetic field. Its surface is the distinctive part: dark ancient
   cratered ground cut across by long parallel grooves, formed where the crust
   pulled apart. That is what this draws.

   Everything is deterministic from a seed, so the same page renders the same
   moon every time, and everything is a token colour, so it follows the theme.
   No photograph on this site would have belonged to it; this does. */

const NS = 'http://www.w3.org/2000/svg';

function el(name, attrs = {}, kids = []) {
  const n = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const c of [].concat(kids)) n.appendChild(c);
  return n;
}

/* mulberry32: small, fast, and repeatable, which is the only property that matters here */
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * @param {Element} node   where to render
 * @param {object}  opts   { seed, grooves, craters, phase, label }
 *   phase 0 = fully lit, 1 = fully dark. The terminator bends: it is the
 *   same wobble the mark uses.
 */
export function ganymede(node, opts = {}) {
  // Artwork must never take a page down with it. A missing container is a
  // layout mistake, not a reason to stop the module that renders the content.
  if (!node) return null;
  const {
    seed = 7, grooves = 26, craters = 16, phase = 0.42,
    label = 'Ganymede, drawn from its grooved terrain',
  } = opts;

  const R = 92, C = 100;
  const r = rng(seed);
  const uid = `gm${seed}`;

  const s = el('svg', {
    viewBox: '0 0 200 200', role: 'img', 'aria-label': label,
    class: 'ganymede',
  });
  s.style.width = '100%';
  s.style.height = 'auto';
  s.style.display = 'block';

  const defs = el('defs');
  defs.appendChild(el('clipPath', { id: `${uid}-disc` }, [
    el('circle', { cx: C, cy: C, r: R }),
  ]));

  const body = el('radialGradient', { id: `${uid}-body`, cx: '36%', cy: '30%', r: '82%' });
  body.appendChild(el('stop', { offset: '0%', 'stop-color': 'var(--line-strong)' }));
  body.appendChild(el('stop', { offset: '52%', 'stop-color': 'var(--surface-3)' }));
  body.appendChild(el('stop', { offset: '100%', 'stop-color': 'var(--surface-2)' }));
  defs.appendChild(body);

  // A soft limb: the edge of a sphere is darker than its middle.
  const limb = el('radialGradient', { id: `${uid}-limb`, cx: '50%', cy: '50%', r: '50%' });
  limb.appendChild(el('stop', { offset: '72%', 'stop-color': 'var(--ground)', 'stop-opacity': '0' }));
  limb.appendChild(el('stop', { offset: '100%', 'stop-color': 'var(--ground)', 'stop-opacity': '.72' }));
  defs.appendChild(limb);
  s.appendChild(defs);

  s.appendChild(el('circle', { cx: C, cy: C, r: R, fill: `url(#${uid}-body)` }));

  const clip = `url(#${uid}-disc)`;

  // ---- grooves: long parallel furrows, the surface's signature ----------
  // Real Ganymede is divided into terrain provinces whose groove sets run at
  // different angles and cut across each other. Evenly spaced horizontals read
  // as scanlines, which is the one thing this must not look like.
  const g = el('g', { 'clip-path': clip, fill: 'none', 'stroke-linecap': 'round' });
  const provinces = [
    { tilt: -3, share: 0.5 },
    { tilt: 8, share: 0.32 },
    { tilt: -13, share: 0.18 },
  ];
  let drawn = 0;
  provinces.forEach((prov, pi) => {
    const n = Math.max(2, Math.round(grooves * prov.share));
    const spread = 170 + r() * 70;
    const offset = -30 + r() * 190;
    for (let i = 0; i < n; i++) {
      const t = i / n;
      const y = offset + t * spread + (r() - 0.5) * 9;
      const bend = (r() - 0.5) * 52;
      const rise = Math.tan((prov.tilt * Math.PI) / 180) * 210;
      const drift = (r() - 0.5) * 16;
      g.appendChild(el('path', {
        d: `M-8 ${(y - rise / 2).toFixed(1)} Q ${100 + bend} ${(y + drift).toFixed(1)} `
           + `208 ${(y + rise / 2).toFixed(1)}`,
        stroke: r() > 0.86 ? 'var(--signal)' : 'var(--muted)',
        'stroke-width': (0.4 + r() * 1.05).toFixed(2),
        opacity: ((pi === 0 ? 0.24 : 0.13) + r() * 0.26).toFixed(2),
      }));
      drawn++;
    }
  });
  s.appendChild(g);

  // ---- craters ----------------------------------------------------------
  const cg = el('g', { 'clip-path': clip });
  for (let i = 0; i < craters; i++) {
    // rejection-sample inside the disc so craters do not cluster at the corners
    let x, y, d;
    do {
      x = r() * 200; y = r() * 200;
      d = Math.hypot(x - C, y - C);
    } while (d > R - 6);
    const rad = 2.5 + r() * (d > R * 0.66 ? 6 : 11);
    cg.appendChild(el('circle', {
      cx: x.toFixed(1), cy: y.toFixed(1), r: rad.toFixed(1),
      fill: 'var(--ground)', opacity: (0.16 + r() * 0.2).toFixed(2),
    }));
    cg.appendChild(el('circle', {
      cx: (x - rad * 0.16).toFixed(1), cy: (y - rad * 0.16).toFixed(1), r: rad.toFixed(1),
      fill: 'none', stroke: 'var(--surface-3)',
      'stroke-width': 0.7, opacity: (0.28 + r() * 0.34).toFixed(2),
    }));
  }
  s.appendChild(cg);

  // ---- the terminator, bent the way the mark bends it -------------------
  if (phase > 0) {
    // phase 0 leaves the disc fully lit, phase 1 covers it. The shadow grows
    // from the left, so its width is the phase itself, not the complement.
    const x = 200 * phase;
    s.appendChild(el('path', {
      d: `M${x} -10 C ${x - 62} 60, ${x + 62} 140, ${x} 210 L -10 210 L -10 -10 Z`,
      'clip-path': clip, fill: 'var(--ground)', opacity: '.74',
    }));
    s.appendChild(el('path', {
      d: `M${x} -10 C ${x - 62} 60, ${x + 62} 140, ${x} 210`,
      'clip-path': clip, fill: 'none', stroke: 'var(--signal)',
      'stroke-width': 1.1, opacity: '.34',
    }));
  }

  s.appendChild(el('circle', { cx: C, cy: C, r: R, fill: `url(#${uid}-limb)` }));
  s.appendChild(el('circle', {
    cx: C, cy: C, r: R, fill: 'none',
    stroke: 'var(--line-strong)', 'stroke-width': 0.8, opacity: '.55',
  }));

  node.replaceChildren(s);
  return s;
}

/**
 * The phases, read left to right. Used where the page wants a rule that means
 * something: an account moving from quiet through the bend and back again.
 */
export function phaseStrip(node, { count = 7, size = 34, seed = 3 } = {}) {
  if (!node) return null;
  const wrap = document.createElement('div');
  wrap.className = 'phasestrip';
  for (let i = 0; i < count; i++) {
    const cell = document.createElement('span');
    cell.style.width = `${size}px`;
    ganymede(cell, {
      seed: seed + i, grooves: 9, craters: 5,
      phase: Math.abs((i / (count - 1)) * 2 - 1) * 0.86,
      label: '',
    });
    cell.firstChild.setAttribute('aria-hidden', 'true');
    cell.firstChild.removeAttribute('role');
    wrap.appendChild(cell);
  }
  node.replaceChildren(wrap);
  return wrap;
}
