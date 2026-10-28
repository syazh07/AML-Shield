/* Inline-SVG chart primitives. No dependencies, no CDN — the demo machine may
   be offline. Every chart is drawn in a 0..W viewBox and scales with its column,
   so the two sides stay dimensionally identical.

   Conventions (kept consistent across every chart here):
     - marks are thin; data-ends are rounded 4px and anchored to the baseline
     - grid and axes are recessive; values wear text tokens, never the series hue
     - one series per chart, coloured by which dataset column it lives in
     - hover tooltips come from [data-tip]; line charts add a crosshair
*/

const NS = 'http://www.w3.org/2000/svg';
export const W = 520;

export function svgEl(tag, attrs = {}, children = []) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, String(v));
  }
  for (const c of [].concat(children)) {
    if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'html') node.innerHTML = v;
    else node.setAttribute(k, String(v));
  }
  for (const c of [].concat(children)) {
    if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
}

function frame(height, klass = 'chart') {
  const svg = svgEl('svg', {
    viewBox: `0 0 ${W} ${height}`,
    width: '100%',
    class: klass,
    role: 'img',
    preserveAspectRatio: 'xMidYMid meet',
  });
  return svg;
}

/* Rounded on the data end only — the baseline end stays square so bars sit flat. */
function barPathH(x, y, w, h, r = 4) {
  const rr = Math.max(0, Math.min(r, w));
  return `M${x},${y} H${x + w - rr} a${rr},${rr} 0 0 1 ${rr},${rr}` +
    ` V${y + h - rr} a${rr},${rr} 0 0 1 ${-rr},${rr} H${x} Z`;
}

function barPathV(x, y, w, h, r = 4) {
  const rr = Math.max(0, Math.min(r, h, w / 2));
  return `M${x},${y + h} V${y + rr} a${rr},${rr} 0 0 1 ${rr},${-rr}` +
    ` H${x + w - rr} a${rr},${rr} 0 0 1 ${rr},${rr} V${y + h} Z`;
}

export function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const n = Number(v);
  if (Number.isInteger(n)) return n.toLocaleString();
  if (Math.abs(n) >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return n.toFixed(digits).replace(/\.?0+$/, '');
}

/* ---- horizontal bars: SHAP importance, rule firing, feature ranges -------- */
export function barChartH({ items, color, labelWidth = 168, valueFmt = fmtNum,
                            unit = '', max = null, note = null }) {
  const rowH = 28;
  const barH = 14;
  const top = 8;
  const bottom = note ? 30 : 10;
  const height = top + items.length * rowH + bottom;
  const x0 = labelWidth;
  const plotW = W - x0 - 62;
  const peak = max !== null ? max : Math.max(...items.map((d) => Math.abs(d.value)), 1e-9);
  const svg = frame(height);

  // recessive gridlines at quarter steps
  for (let i = 1; i <= 4; i += 1) {
    const gx = x0 + (plotW * i) / 4;
    svg.appendChild(svgEl('line', {
      x1: gx, x2: gx, y1: top - 2, y2: top + items.length * rowH,
      class: 'grid-line',
    }));
  }
  svg.appendChild(svgEl('line', {
    x1: x0, x2: x0, y1: top - 2, y2: top + items.length * rowH, class: 'axis-line',
  }));

  items.forEach((d, i) => {
    const y = top + i * rowH;
    const w = Math.max(1.5, (Math.abs(d.value) / peak) * plotW);
    svg.appendChild(svgEl('text', {
      x: x0 - 10, y: y + barH + 1, class: 'lbl lbl-row', 'text-anchor': 'end',
    }, d.label));
    const bar = svgEl('path', {
      d: barPathH(x0 + 1, y + 3, w, barH),
      fill: color,
      opacity: d.muted ? 0.45 : 1,
      'data-tip': d.tip || `${d.label}: ${valueFmt(d.value)}${unit}`,
    });
    svg.appendChild(bar);
    svg.appendChild(svgEl('text', {
      x: x0 + w + 10, y: y + barH + 1, class: 'lbl lbl-val',
    }, `${valueFmt(d.value)}${unit}`));
  });

  if (note) {
    svg.appendChild(svgEl('text', {
      x: x0, y: height - 8, class: 'lbl lbl-note',
    }, note));
  }
  return svg;
}

/* Axis ticks that land on round numbers. Counts are integers, so a 19-account
   histogram must not label its gridlines 1.25 / 2.5 / 3.75. */
function niceScale(peak, maxTicks = 4) {
  if (peak <= maxTicks) {
    return { max: Math.max(1, peak), ticks: Array.from({ length: Math.max(2, peak + 1) }, (_, i) => i) };
  }
  const raw = peak / maxTicks;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || 10 * mag;
  const max = Math.ceil(peak / step) * step;
  const ticks = [];
  for (let v = 0; v <= max + 1e-9; v += step) ticks.push(v);
  return { max, ticks };
}

/* ---- histogram of the 0-100 composite, with the alert cutoff -------------- */
export function histogram({ bins, color, threshold = null, xLabel = '' }) {
  const height = 190;
  const top = 12;
  const left = 40;
  const bottom = 42;
  const plotW = W - left - 16;
  const plotH = height - top - bottom;
  const { max: peak, ticks } = niceScale(Math.max(...bins.map((b) => b.count), 1));
  const svg = frame(height);
  const xOf = (v) => left + (v / 100) * plotW;

  ticks.forEach((t) => {
    const y = top + plotH - (t / peak) * plotH;
    svg.appendChild(svgEl('line', { x1: left, x2: left + plotW, y1: y, y2: y, class: 'grid-line' }));
    svg.appendChild(svgEl('text', {
      x: left - 8, y: y + 4, class: 'lbl lbl-tick', 'text-anchor': 'end',
    }, String(t)));
  });

  const slot = plotW / bins.length;
  bins.forEach((b) => {
    if (!b.count) return;
    const h = Math.max(2, (b.count / peak) * plotH);
    // beyond the cutoff = full weight; below it = recessive. Opacity rather
    // than a second hue, so nothing competes with the column's identity colour.
    const beyond = threshold !== null && b.x1 > threshold;
    svg.appendChild(svgEl('path', {
      d: barPathV(xOf(b.x0) + 1, top + plotH - h, Math.max(1, slot - 2), h),
      fill: color,
      opacity: beyond ? 1 : 0.45,
      'data-tip': `risk ${b.x0}–${b.x1}: ${b.count} account${b.count === 1 ? '' : 's'}`,
    }));
  });

  svg.appendChild(svgEl('line', {
    x1: left, x2: left + plotW, y1: top + plotH, y2: top + plotH, class: 'axis-line',
  }));
  [0, 25, 50, 75, 100].forEach((v) => {
    svg.appendChild(svgEl('text', {
      x: xOf(v), y: top + plotH + 18, class: 'lbl lbl-tick', 'text-anchor': 'middle',
    }, String(v)));
  });

  if (threshold !== null) {
    const tx = xOf(threshold);
    svg.appendChild(svgEl('line', {
      x1: tx, x2: tx, y1: top - 4, y2: top + plotH, class: 'rule-line',
    }));
    svg.appendChild(svgEl('text', {
      x: tx + 6, y: top + 8, class: 'lbl lbl-rule',
    }, `cutoff ${threshold} →`));
  }
  if (xLabel) {
    svg.appendChild(svgEl('text', {
      x: left + plotW / 2, y: height - 6, class: 'lbl lbl-axis', 'text-anchor': 'middle',
    }, xLabel));
  }
  return svg;
}

/* ---- ROC / PR curves ------------------------------------------------------ */
export function lineChart({ points, color, xLabel, yLabel, diagonal = false,
                            baseline = null, area = true }) {
  const height = 250;
  const top = 14;
  const left = 44;
  const bottom = 44;
  const plotW = W - left - 18;
  const plotH = height - top - bottom;
  const svg = frame(height);
  const xOf = (v) => left + v * plotW;
  const yOf = (v) => top + plotH - v * plotH;

  for (let i = 0; i <= 4; i += 1) {
    const gy = top + (plotH * i) / 4;
    const gx = left + (plotW * i) / 4;
    svg.appendChild(svgEl('line', { x1: left, x2: left + plotW, y1: gy, y2: gy, class: 'grid-line' }));
    svg.appendChild(svgEl('line', { x1: gx, x2: gx, y1: top, y2: top + plotH, class: 'grid-line' }));
    svg.appendChild(svgEl('text', {
      x: left - 8, y: yOf(i / 4) + 4, class: 'lbl lbl-tick', 'text-anchor': 'end',
    }, (i / 4).toFixed(2)));
    svg.appendChild(svgEl('text', {
      x: gx, y: top + plotH + 18, class: 'lbl lbl-tick', 'text-anchor': 'middle',
    }, (i / 4).toFixed(2)));
  }

  if (diagonal) {
    svg.appendChild(svgEl('line', {
      x1: xOf(0), y1: yOf(0), x2: xOf(1), y2: yOf(1), class: 'ref-line',
    }));
    svg.appendChild(svgEl('text', {
      x: xOf(0.72), y: yOf(0.66), class: 'lbl lbl-note',
    }, 'chance'));
  }
  if (baseline !== null) {
    svg.appendChild(svgEl('line', {
      x1: xOf(0), y1: yOf(baseline), x2: xOf(1), y2: yOf(baseline), class: 'ref-line',
    }));
    svg.appendChild(svgEl('text', {
      x: xOf(0.02), y: yOf(baseline) - 6, class: 'lbl lbl-note',
    }, `chance (${(baseline * 100).toFixed(0)}% positive)`));
  }

  const d = points.map((p, i) => `${i ? 'L' : 'M'}${xOf(p.x).toFixed(2)},${yOf(p.y).toFixed(2)}`).join(' ');
  if (area) {
    svg.appendChild(svgEl('path', {
      d: `${d} L${xOf(points[points.length - 1].x)},${yOf(0)} L${xOf(points[0].x)},${yOf(0)} Z`,
      fill: color, opacity: 0.12,
    }));
  }
  svg.appendChild(svgEl('path', { d, fill: 'none', stroke: color, 'stroke-width': 2,
    'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));

  svg.appendChild(svgEl('line', {
    x1: left, x2: left + plotW, y1: top + plotH, y2: top + plotH, class: 'axis-line',
  }));
  svg.appendChild(svgEl('text', {
    x: left + plotW / 2, y: height - 6, class: 'lbl lbl-axis', 'text-anchor': 'middle',
  }, xLabel));
  svg.appendChild(svgEl('text', {
    x: 12, y: top + plotH / 2, class: 'lbl lbl-axis', 'text-anchor': 'middle',
    transform: `rotate(-90 12 ${top + plotH / 2})`,
  }, yLabel));

  // crosshair: snap to the nearest point on x
  const marker = svgEl('circle', { r: 5, fill: color, class: 'crosshair-dot', stroke: 'var(--surface-1)', 'stroke-width': 2 });
  const vline = svgEl('line', { y1: top, y2: top + plotH, class: 'crosshair-line' });
  svg.appendChild(vline);
  svg.appendChild(marker);
  const hit = svgEl('rect', {
    x: left, y: top, width: plotW, height: plotH, fill: 'transparent', class: 'hit',
  });
  hit.addEventListener('mousemove', (ev) => {
    const box = svg.getBoundingClientRect();
    const vx = ((ev.clientX - box.left) / box.width) * W;
    const target = (vx - left) / plotW;
    let best = points[0];
    for (const p of points) {
      if (Math.abs(p.x - target) < Math.abs(best.x - target)) best = p;
    }
    marker.setAttribute('cx', xOf(best.x));
    marker.setAttribute('cy', yOf(best.y));
    vline.setAttribute('x1', xOf(best.x));
    vline.setAttribute('x2', xOf(best.x));
    svg.classList.add('crosshair-on');
    showTip(ev, `${xLabel} ${best.x.toFixed(3)} · ${yLabel} ${best.y.toFixed(3)}`);
  });
  hit.addEventListener('mouseleave', () => { svg.classList.remove('crosshair-on'); hideTip(); });
  svg.appendChild(hit);
  return svg;
}

/* ---- 2x2 confusion matrix (HTML, not SVG — it is a labelled table) -------- */
export function confusionMatrix({ tn, fp, fn, tp }) {
  const cells = [
    { k: 'tn', v: tn, role: 'true negative', tone: 'ok', row: 'actual normal', col: 'pred normal' },
    { k: 'fp', v: fp, role: 'false positive', tone: 'bad', row: 'actual normal', col: 'pred mule' },
    { k: 'fn', v: fn, role: 'false negative', tone: 'bad', row: 'actual mule', col: 'pred normal' },
    { k: 'tp', v: tp, role: 'true positive', tone: 'ok', row: 'actual mule', col: 'pred mule' },
  ];
  const grid = el('div', { class: 'cm' });
  grid.appendChild(el('div', { class: 'cm-corner' }));
  grid.appendChild(el('div', { class: 'cm-head', text: 'predicted normal' }));
  grid.appendChild(el('div', { class: 'cm-head', text: 'predicted mule' }));
  ['actual normal', 'actual mule'].forEach((rowName) => {
    grid.appendChild(el('div', { class: 'cm-side', text: rowName }));
    cells.filter((c) => c.row === rowName).forEach((c) => {
      grid.appendChild(el('div', { class: `cm-cell cm-${c.tone}` }, [
        el('span', { class: 'cm-val', text: String(c.v) }),
        el('span', { class: 'cm-role', text: c.role }),
      ]));
    });
  });
  return grid;
}

/* ---- table ---------------------------------------------------------------- */

/* How a boolean cell should be coloured depends on what it means. "Flagged" is
   an alert (a cost, even when right); "Correct" is a verdict. Colouring both red
   for `true` would say a correct call was a bad outcome. */
const BOOL_TONE = {
  Is_Flagged: 'alarm', flagged: 'alarm', Correct: 'verdict',
};

function boolChip(value, column) {
  const on = isTruthy(value);
  const tone = BOOL_TONE[column] || 'neutral';
  let cls = 'chip-off';
  if (tone === 'alarm') cls = on ? 'chip-alarm' : 'chip-off';
  else if (tone === 'verdict') cls = on ? 'chip-good' : 'chip-alarm';
  else cls = on ? 'chip-neutral' : 'chip-off';
  return el('span', { class: `chip ${cls}`, text: on ? 'yes' : 'no' });
}

export function table({ columns, rows, headers = null, flagKey = null, className = '' }) {
  const t = el('table', { class: `tbl ${className}` });
  const thead = el('thead');
  const tr = el('tr');
  columns.forEach((c, i) => tr.appendChild(el('th', { text: (headers && headers[i]) || prettify(c) })));
  thead.appendChild(tr);
  t.appendChild(thead);
  const tbody = el('tbody');
  rows.forEach((r) => {
    const row = el('tr');
    if (flagKey && isTruthy(r[flagKey])) row.classList.add('is-flagged');
    columns.forEach((c) => {
      const raw = r[c];
      const td = el('td');
      if (typeof raw === 'boolean' || /^(true|false)$/i.test(String(raw))) {
        td.appendChild(boolChip(raw, c));
      } else if (typeof raw === 'number') {
        td.className = 'num';
        td.textContent = fmtNum(raw);
      } else {
        td.textContent = raw === null || raw === undefined ? '—' : String(raw);
      }
      row.appendChild(td);
    });
    tbody.appendChild(row);
  });
  t.appendChild(tbody);
  const wrap = el('div', { class: 'tbl-wrap' }, [t]);
  return wrap;
}

function isTruthy(v) {
  return v === true || v === 1 || /^(true|yes|1)$/i.test(String(v));
}

export function prettify(key) {
  return String(key).replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

/* ---- shared tooltip ------------------------------------------------------- */
let tipNode = null;

function ensureTip() {
  if (!tipNode) {
    tipNode = el('div', { class: 'tip', role: 'tooltip' });
    document.body.appendChild(tipNode);
  }
  return tipNode;
}

export function showTip(ev, text) {
  const tip = ensureTip();
  tip.textContent = text;
  tip.classList.add('on');
  const pad = 14;
  const x = Math.min(ev.clientX + pad, window.innerWidth - tip.offsetWidth - 8);
  const y = Math.max(8, ev.clientY - tip.offsetHeight - pad);
  tip.style.transform = `translate(${x}px, ${y}px)`;
}

export function hideTip() {
  if (tipNode) tipNode.classList.remove('on');
}

/* Delegated hover for anything carrying data-tip. Called once at boot. */
export function attachTips(root) {
  root.addEventListener('mousemove', (ev) => {
    const target = ev.target.closest ? ev.target.closest('[data-tip]') : null;
    if (target) showTip(ev, target.getAttribute('data-tip'));
    else if (!ev.target.classList || !ev.target.classList.contains('hit')) hideTip();
  });
  root.addEventListener('mouseleave', hideTip);
}
