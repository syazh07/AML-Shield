/* One renderer per pipeline stage. Each receives the parsed artifacts for ONE
   source and returns a DOM fragment for that column.

   Where the two sides genuinely differ — different SHAP target at 03, different
   chart at 06, no labels to validate against at 04 — the panel says so out loud.
   That asymmetry is the Tier A / Tier B argument, so it is never smoothed over.
*/

import {
  barChartH, confusionMatrix, el, fmtNum, histogram, lineChart, prettify, table,
} from './charts.js';

const ACCENT = { real: 'var(--real)', synthetic: 'var(--synthetic)' };

function section(title, ...children) {
  return el('div', { class: 'section' }, [
    title ? el('h2', { class: 'section-title', text: title }) : null,
    ...children.flat().filter(Boolean),
  ]);
}

function stats(items) {
  return el('div', { class: 'stats' }, items.filter(Boolean).map((s) => el('div', {
    class: `stat ${s.tone ? `stat-${s.tone}` : ''}`,
  }, [
    el('div', { class: 'stat-v', text: s.value }),
    el('div', { class: 'stat-k', text: s.key }),
  ])));
}

function raw(label, text) {
  if (!text) return null;
  return el('details', { class: 'raw' }, [
    el('summary', { text: label }),
    el('pre', { text }),
  ]);
}

/* ---- 00 · quality gate ---------------------------------------------------- */
function panel00(d, source) {
  const out = [];
  out.push(section(null, stats([
    { value: fmtNum(d.counts.transactions), key: 'transactions' },
    { value: fmtNum(d.counts.accounts), key: 'accounts' },
    d.labels
      ? { value: `${d.labels.mules}/${d.labels.normals}`, key: 'mules / normals' }
      : { value: '—', key: 'labels' },
  ])));

  out.push(section('What this file makes possible',
    el('div', { class: 'caps' }, d.capabilities.map((c) => el('div', {
      class: `cap ${c.ok ? 'cap-yes' : 'cap-no'}`,
    }, [
      el('div', { class: 'cap-mark', text: c.ok ? '✓' : '✗' }),
      el('div', {}, [
        el('div', { class: 'cap-name', text: c.name }),
        el('div', { class: 'cap-detail', text: c.detail }),
        el('div', { class: 'cap-unlocks', text: c.unlocks }),
      ]),
    ])))));

  if (d.concentration) {
    out.push(section(null, el('div', { class: 'callout callout-warn' }, [
      el('span', { html: `One account holds <b>${fmtNum(d.concentration.txns)}</b> of `
        + `${fmtNum(d.counts.transactions)} transactions (`
        + `<b>${Math.round(d.concentration.share * 100)}%</b>). The sample is one `
        + `busy aggregator plus 18 bystanders — a model cannot learn a population `
        + `from that.` }),
    ])));
  }

  if (d.typologies) {
    const items = Object.entries(d.typologies)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v]) => ({ label: k, value: v, muted: k === 'normal' }));
    out.push(section('Planted typologies (accounts)',
      barChartH({ items, color: ACCENT[source], labelWidth: 150, unit: '' }),
      el('p', { class: 'prose', text: 'The 30 "ambiguous" accounts are deliberate '
        + 'coin-flips — they keep the problem from being trivially separable.' })));
  }

  const channels = Object.entries(d.channels || {});
  if (channels.length) {
    out.push(section('Channel mix', barChartH({
      items: channels.map(([k, v]) => ({ label: k, value: v })),
      color: ACCENT[source],
      labelWidth: 110,
    })));
  }

  if (d.dead_columns && d.dead_columns.length) {
    out.push(section('Zero-information columns (dropped)',
      el('div', { class: 'pills' }, d.dead_columns.map((c) => el('span', {
        class: 'pill', text: c.column, 'data-tip': `constant: ${c.value}`,
      })))));
  }

  out.push(section('Amount profile', stats([
    { value: `₹${fmtNum(d.amount.median)}`, key: 'median' },
    { value: `₹${fmtNum(d.amount.mean)}`, key: 'mean' },
    { value: `₹${fmtNum(d.amount.max)}`, key: 'max' },
  ])));

  out.push(raw('Full data_quality_report.md', d.report_md));
  return out;
}

/* ---- 01 · features -------------------------------------------------------- */
function panel01(d, source) {
  const out = [];
  out.push(section(null, stats([
    { value: fmtNum(d.rows), key: 'account rows' },
    { value: fmtNum(d.n_columns), key: 'feature columns' },
    d.n_tier_b_only
      ? { value: `+${d.n_tier_b_only}`, key: 'unlocked by time + graph', tone: 'good' }
      : { value: '0', key: 'temporal / graph features' },
  ])));

  out.push(section('Feature columns',
    el('div', { class: 'pills' }, d.columns.map((c) => el('span', {
      class: `pill ${c.tier_b_only ? 'pill-new' : ''}`,
      text: c.name,
      'data-tip': c.mean === undefined ? c.name
        : `${c.name} — min ${fmtNum(c.min)} · mean ${fmtNum(c.mean)} · max ${fmtNum(c.max)}`,
    }))),
    el('p', {
      class: 'prose',
      text: d.n_tier_b_only
        ? 'Highlighted columns exist only because this dataset has real timestamps '
          + 'and counterparty edges. They are the four temporal and five graph features.'
        : 'Count and ratio features only. With one frozen timestamp and no '
          + 'beneficiary column, there is nothing temporal or relational to compute.',
    }),
    d.label_columns && d.label_columns.length
      ? el('p', {
        class: 'prose',
        html: `Carried alongside but never fed to the model: `
          + `${d.label_columns.map((c) => `<code>${c}</code>`).join(', ')}.`,
      })
      : null));

  out.push(section('First rows', table({
    columns: d.preview_columns,
    rows: d.preview,
  })));
  return out;
}

/* ---- 02 · score ----------------------------------------------------------- */
function panel02(d, source) {
  const out = [];
  out.push(section(null, el('div', { class: 'formula' }, [
    el('span', { text: d.fusion.formula }),
    el('small', {
      text: `Rules combine by noisy-OR, so one strong typology already scores high `
        + `and extra typologies compound. Weights ${d.fusion.w_rule} / ${d.fusion.w_anom} `
        + `read live from common.py.`,
    }),
  ])));

  out.push(section(null, stats([
    { value: fmtNum(d.rows), key: 'accounts scored' },
    { value: fmtNum(d.flagged), key: `flagged ≥ ${d.threshold}`, tone: 'bad' },
    { value: `${Math.round((d.flagged / d.rows) * 100)}%`, key: 'of the book' },
  ])));

  out.push(section('Composite risk distribution', histogram({
    bins: d.histogram.bins,
    color: ACCENT[source],
    threshold: d.threshold,
    xLabel: 'composite risk (0–100)',
  })));

  if (d.label_split) {
    out.push(section(null, stats([
      { value: fmtNum(d.label_split.flagged_mules), key: 'flagged & mule', tone: 'good' },
      { value: fmtNum(d.label_split.flagged_normals), key: 'flagged & normal', tone: 'bad' },
      { value: fmtNum(d.label_split.missed_mules), key: 'missed mules', tone: 'bad' },
    ])));
  } else {
    out.push(section(null, el('div', { class: 'callout callout-note' }, [
      el('span', {
        html: `<b>${d.flagged} of ${d.rows}</b> accounts clear the cutoff — and with `
          + `no labels, nobody can say how many are real. That ratio is the `
          + `reviewer-backpressure problem in one number.`,
      }),
    ])));
  }

  const firing = Object.entries(d.rule_firing || {})
    .map(([k, v]) => ({
      label: prettify(k),
      value: v.accounts_firing,
      muted: v.accounts_firing === 0,
      tip: `${prettify(k)} — fires on ${v.accounts_firing} accounts · `
        + `mean ${fmtNum(v.mean_when_firing)} when firing · standalone cap ${v.cap}`,
    }))
    .sort((a, b) => b.value - a.value);
  if (firing.length) {
    out.push(section('Typology rules — accounts firing',
      barChartH({ items: firing, color: ACCENT[source], labelWidth: 160 })));
  }

  out.push(section(`Top ${Math.min(25, d.rows)} by composite risk`, table({
    columns: d.top_columns,
    rows: d.top,
    flagKey: null,
  })));
  return out;
}

/* ---- 03 · explain --------------------------------------------------------- */
function panel03(d, source) {
  const out = [];
  out.push(section(null, el('div', { class: 'callout callout-note' }, [
    el('span', { html: `<b>${d.model}</b><br>${d.schema_note}` }),
  ])));

  out.push(section('Global feature importance (mean |SHAP|)', barChartH({
    items: d.importance.map((r) => ({ label: r.feature, value: r.mean_abs_shap })),
    color: ACCENT[source],
    labelWidth: 174,
    valueFmt: (v) => fmtNum(v, 3),
  })));

  if (d.rows.length) {
    out.push(section(`Per-account driver — ${d.explains}`, table({
      columns: d.row_columns.filter((c) => d.rows[0][c] !== undefined),
      rows: d.rows,
    })));
  }
  return out;
}

/* ---- 04 · validate -------------------------------------------------------- */
function panel04(d, source) {
  const out = [];
  out.push(section(null, el('div', { class: 'callout callout-note' }, [
    el('span', { text: d.method }),
  ])));

  if (d.metrics.length) {
    out.push(section(null, stats(d.metrics.map((m) => ({
      value: m.value, key: m.label,
    })))));
  }

  if (d.separation) {
    out.push(section('Separation test — planted accounts', table({
      columns: ['account', 'type', 'rank', 'composite', 'flagged'],
      rows: d.separation,
      flagKey: 'flagged',
    })));
    if (d.verdict) {
      out.push(section(null, el('div', { class: 'callout callout-note' }, [
        el('span', {
          html: `<b>${d.verdict}</b> — every planted mule outranks every planted `
            + `normal, and the fixed cutoff lands between the two groups.`,
        }),
      ])));
    }
  }

  if (d.confusion) {
    out.push(section('Confusion matrix @ 0.5', confusionMatrix(d.confusion)));
  }
  if (d.roc) {
    out.push(section('ROC — out-of-fold', lineChart({
      points: d.roc, color: ACCENT[source],
      xLabel: 'false positive rate', yLabel: 'true positive rate', diagonal: true,
    })));
  }
  if (d.pr) {
    out.push(section('Precision–Recall — out-of-fold', lineChart({
      points: d.pr, color: ACCENT[source],
      xLabel: 'recall', yLabel: 'precision', baseline: d.positive_rate,
    })));
  }
  if (d.caveat) {
    out.push(section(null, el('div', { class: 'callout callout-warn' }, [
      el('span', { html: `<b>Read this before believing the numbers.</b> ${d.caveat}` }),
    ])));
  }

  out.push(raw('Full validation_report.md', d.report_md));
  return out;
}

/* ---- 05 · report ---------------------------------------------------------- */
function panel05(d, source) {
  const out = [];
  out.push(section(null, stats([
    { value: fmtNum(d.flagged), key: `alerts ≥ ${d.threshold}`, tone: 'bad' },
    { value: fmtNum(d.total), key: 'accounts reviewed' },
    { value: `${Math.round((d.flagged / d.total) * 100)}%`, key: 'alert rate' },
  ])));

  if (d.outcome) {
    out.push(section('Against ground truth', stats([
      { value: fmtNum(d.outcome.true_positive), key: 'caught', tone: 'good' },
      { value: fmtNum(d.outcome.false_positive), key: 'wasted reviews', tone: 'bad' },
      { value: fmtNum(d.outcome.false_negative), key: 'missed', tone: 'bad' },
    ])));
  } else if (d.outcome_note) {
    out.push(section(null, el('div', { class: 'callout callout-warn' }, [
      el('span', { text: d.outcome_note }),
    ])));
  }

  out.push(section('Alert queue', table({
    columns: d.columns,
    rows: d.rows,
    flagKey: 'Is_Flagged',
  })));
  return out;
}

/* ---- 06 · chart ----------------------------------------------------------- */
function panel06(d, source, ctx) {
  const out = [];
  if (!d.images.length) {
    return [el('div', { class: 'empty' }, [
      el('div', { class: 'empty-title', text: 'No image produced' }),
    ])];
  }
  d.images.forEach((img) => {
    out.push(section(img.caption, el('img', {
      class: 'img-artifact',
      src: `/api/run/${ctx.runId}/image/${img.filename}`,
      alt: img.caption,
    }), el('p', { class: 'prose', text: img.filename })));
  });
  out.push(section(null, el('div', { class: 'callout callout-note' }, [
    el('span', { text: d.note }),
  ])));
  return out;
}

const PANELS = {
  '00': panel00, '01': panel01, '02': panel02, '03': panel03,
  '04': panel04, '05': panel05, '06': panel06,
};

const WAITING_COPY = {
  pending: ['Not run yet', 'Click the button below to execute this stage for real.'],
  running: ['Running…', 'The stage is executing right now. Watch the log.'],
  failed: ['Stage failed', 'No cached result is substituted — what you see is what happened.'],
  timeout: ['Stage timed out', 'The subprocess was killed after exceeding its limit.'],
  parse_error: ['Could not read the artifacts', 'The stage finished but its output did not parse.'],
};

export function renderPanel(stageId, payload, source, ctx) {
  const host = document.createDocumentFragment();
  if (!payload || !payload.available) {
    const stateKey = (payload && payload.status) || 'pending';
    const [title, sub] = WAITING_COPY[stateKey] || WAITING_COPY.pending;
    const bad = stateKey === 'failed' || stateKey === 'timeout' || stateKey === 'parse_error';
    host.appendChild(el('div', { class: `empty ${bad ? 'empty-fail' : ''}` }, [
      el('div', { class: 'empty-title', text: title }),
      el('div', { class: 'empty-sub', text: sub }),
      payload && payload.error ? el('div', { class: 'err-detail', text: payload.error }) : null,
    ]));
    return host;
  }
  const nodes = PANELS[stageId](payload, source, ctx) || [];
  nodes.filter(Boolean).forEach((n) => host.appendChild(n));
  return host;
}
