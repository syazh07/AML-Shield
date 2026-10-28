/* Shell: stage rail, the advance button, the SSE log, and panel swapping.

   The whole interaction is one button. Click it, a stage really executes for
   both datasets at once, its stdout streams into the log, and both columns fill
   with what that stage produced.
*/

import { attachTips, el } from './charts.js';
import { renderPanel } from './panels.js';

const SOURCES = ['real', 'synthetic'];

const state = {
  runId: null,
  manifest: null,
  stages: [],        // manifest entries
  status: {},        // stage id -> { status, sources }
  current: '00',     // stage the columns are showing
  artifacts: {},     // stage id -> parsed payload
  view: 'both',      // which columns are shown: both | real | synthetic
  busy: false,
  events: null,      // EventSource
  tickHandle: null,
  tickStart: 0,
};

const dom = {
  rail: document.getElementById('rail'),
  title: document.getElementById('stage-title'),
  sub: document.getElementById('stage-sub'),
  script: document.getElementById('stage-script'),
  advance: document.getElementById('advance'),
  runall: document.getElementById('runall'),
  reset: document.getElementById('reset'),
  theme: document.getElementById('theme'),
  elapsed: document.getElementById('elapsed'),
  logToggle: document.getElementById('logtoggle'),
  log: document.getElementById('runlog'),
  logInner: document.getElementById('runlog-inner'),
  cols: document.getElementById('cols'),
  view: document.getElementById('view'),
  preflight: document.getElementById('preflight'),
  preflightText: document.getElementById('preflight-text'),
};

const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    return res.json();
  },
  async post(path) {
    const res = await fetch(path, { method: 'POST' });
    if (!res.ok) throw new Error(`${res.status} ${(await res.json()).detail || ''}`);
    return res.json();
  },
};

function stageById(id) {
  return state.stages.find((s) => s.id === id);
}

/* ---- preflight ------------------------------------------------------------ */
async function loadPreflight() {
  try {
    const pf = await api.get('/api/preflight');
    const bad = pf.checks.filter((c) => !c.ok);
    dom.preflight.querySelector('.dot').className = `dot ${pf.ok ? 'dot-ok' : 'dot-bad'}`;
    dom.preflightText.textContent = pf.ok
      ? 'environment ready'
      : `${bad.length} check${bad.length === 1 ? '' : 's'} failing`;
    dom.preflight.title = pf.checks
      .map((c) => `${c.ok ? '✓' : '✗'} ${c.name}: ${c.detail}`).join('\n');
  } catch (err) {
    dom.preflight.querySelector('.dot').className = 'dot dot-bad';
    dom.preflightText.textContent = 'preflight unreachable';
  }
}

/* ---- rail ----------------------------------------------------------------- */
function renderRail() {
  dom.rail.textContent = '';
  state.stages.forEach((s) => {
    const st = (state.status[s.id] || {}).status || 'pending';
    const chip = el('button', {
      class: `chip ${s.id === state.current ? 'is-current' : ''}`,
      'data-state': st,
      title: `${s.script} — ${s.subtitle}`,
    }, [
      el('div', { class: 'chip-top' }, [
        el('span', { class: 'chip-state' }),
        el('span', { class: 'chip-id', text: s.id }),
      ]),
      el('span', { class: 'chip-label', text: s.label }),
    ]);
    chip.addEventListener('click', () => show(s.id));
    dom.rail.appendChild(chip);
  });
}

/* ---- which columns are visible -------------------------------------------- */
function isShown(source) {
  return state.view === 'both' || state.view === source;
}

/* Display only. Both datasets still run on every step — this just decides what
   is on screen, so you can put one side up without re-running anything. */
function applyView(view) {
  state.view = view;
  localStorage.setItem('mlviz-view', view);
  dom.cols.dataset.view = view;
  [...dom.view.children].forEach((b) => {
    b.classList.toggle('is-on', b.dataset.view === view);
  });
  renderColumns();
}

/* ---- columns -------------------------------------------------------------- */
function renderColumns() {
  const stage = stageById(state.current);
  dom.title.textContent = `${stage.id} · ${stage.label}`;
  dom.sub.textContent = stage.subtitle;
  dom.script.textContent = stage.script;

  const parsed = state.artifacts[state.current];
  SOURCES.forEach((source) => {
    const body = document.getElementById(`body-${source}`);
    body.textContent = '';
    // skip the hidden column entirely — no point building charts nobody sees
    if (!isShown(source)) return;
    const payload = parsed ? parsed.sources[source] : null;
    body.appendChild(renderPanel(state.current, payload, source, { runId: state.runId }));

    const timing = document.getElementById(`t-${source}`);
    const srcState = (state.status[state.current] || {}).sources;
    const info = srcState ? srcState[source] : null;
    timing.textContent = info && info.duration_s ? `${info.duration_s.toFixed(2)}s` : '';
  });
}

async function show(stageId) {
  state.current = stageId;
  const st = state.status[stageId];
  // Fetch for anything that has been attempted, not just successes — the
  // endpoint carries the per-source status and error text, which is exactly
  // what a failed stage needs to show instead of silently reading "not run".
  if (st && st.status !== 'pending' && !state.artifacts[stageId]) {
    try {
      state.artifacts[stageId] = await api.get(`/api/run/${state.runId}/stage/${stageId}`);
    } catch (err) { /* leave the panel in its waiting state */ }
  }
  renderRail();
  renderColumns();
  renderControls();
}

/* ---- controls ------------------------------------------------------------- */
function nextStageId() {
  const s = state.stages.find((x) => (state.status[x.id] || {}).status !== 'done');
  return s ? s.id : null;
}

function renderControls() {
  const next = nextStageId();
  if (state.busy) {
    const running = state.stages.find((x) => (state.status[x.id] || {}).status === 'running');
    dom.advance.textContent = running
      ? `Running ${running.id} · ${running.label}…` : 'Running…';
  } else if (next) {
    const s = stageById(next);
    dom.advance.textContent = `Run stage ${s.id} · ${s.label}`;
  } else {
    dom.advance.textContent = 'Pipeline complete';
  }
  dom.advance.disabled = state.busy || !next;
  dom.runall.disabled = state.busy || !next;
}

function startTicker() {
  state.tickStart = performance.now();
  stopTicker();
  state.tickHandle = setInterval(() => {
    const s = (performance.now() - state.tickStart) / 1000;
    dom.elapsed.textContent = `${s.toFixed(1)}s`;
  }, 100);
}

function stopTicker() {
  if (state.tickHandle) clearInterval(state.tickHandle);
  state.tickHandle = null;
}

async function step(stageId = null) {
  if (state.busy) return;
  state.busy = true;
  renderControls();
  startTicker();
  const target = stageId || nextStageId();
  if (target) show(target);
  try {
    await api.post(`/api/run/${state.runId}/step${stageId ? `?stage=${stageId}` : ''}`);
  } catch (err) {
    appendLog({ source: 'real', channel: 'stderr', line: String(err.message || err) });
  } finally {
    stopTicker();
    state.busy = false;
    // the SSE stage_done already refreshed status; pull the artifacts
    delete state.artifacts[target];
    await show(target);
  }
}

async function runAll() {
  while (nextStageId() && !state.busy) {
    /* eslint-disable no-await-in-loop */
    await step();
    const failed = Object.values(state.status).some(
      (s) => s.status === 'failed' || s.status === 'timeout',
    );
    if (failed) break;
  }
}

/* ---- log ------------------------------------------------------------------ */
function appendLog(ev) {
  const atBottom = dom.logInner.scrollTop + dom.logInner.clientHeight
    >= dom.logInner.scrollHeight - 24;
  dom.logInner.appendChild(el('div', {
    class: 'logline', 'data-source': ev.source, 'data-channel': ev.channel || 'stdout',
  }, [
    el('span', { class: 'src', text: ev.source === 'real' ? 'real' : 'synth' }),
    el('span', { class: 'txt', text: ev.line }),
  ]));
  while (dom.logInner.childElementCount > 1200) {
    dom.logInner.removeChild(dom.logInner.firstChild);
  }
  if (atBottom) dom.logInner.scrollTop = dom.logInner.scrollHeight;
}

function setLogOpen(open) {
  dom.log.classList.toggle('on', open);
  dom.logToggle.textContent = open ? 'Hide log' : 'Show log';
}

/* ---- SSE ------------------------------------------------------------------ */
function connectEvents() {
  if (state.events) state.events.close();
  const src = new EventSource(`/api/run/${state.runId}/events`);
  state.events = src;
  src.onmessage = (msg) => {
    const ev = JSON.parse(msg.data);
    if (ev.type === 'snapshot') {
      state.status = ev.run.stages;
      (ev.log || []).forEach(appendLog);
      renderRail();
      renderControls();
    } else if (ev.type === 'log') {
      appendLog(ev);
    } else if (ev.type === 'status') {
      const st = state.status[ev.stage];
      if (st) {
        st.sources[ev.source] = ev;
        const all = SOURCES.map((s) => st.sources[s].status);
        st.status = all.includes('failed') || all.includes('timeout') ? 'failed'
          : all.includes('running') ? 'running'
            : all.every((x) => x === 'done') ? 'done' : 'pending';
      }
      renderRail();
      if (ev.stage === state.current) renderColumns();
    } else if (ev.type === 'stage_done') {
      renderRail();
      renderControls();
    }
  };
}

/* ---- run lifecycle -------------------------------------------------------- */
async function newRun() {
  if (state.events) state.events.close();
  dom.logInner.textContent = '';
  const run = await api.post('/api/run');
  state.runId = run.run_id;
  state.status = run.stages;
  state.artifacts = {};
  state.current = state.stages[0].id;
  connectEvents();
  renderRail();
  renderColumns();
  renderControls();
  dom.elapsed.textContent = '';
}

/* ---- theme ---------------------------------------------------------------- */
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  dom.theme.textContent = theme === 'dark' ? 'Light' : 'Dark';
  localStorage.setItem('mlviz-theme', theme);
}

/* ---- boot ----------------------------------------------------------------- */
async function boot() {
  applyTheme(localStorage.getItem('mlviz-theme') || 'dark');
  state.view = localStorage.getItem('mlviz-view') || 'both';
  dom.cols.dataset.view = state.view;
  [...dom.view.children].forEach((b) => {
    b.classList.toggle('is-on', b.dataset.view === state.view);
  });
  attachTips(document.body);

  state.manifest = await api.get('/api/stages');
  state.stages = state.manifest.stages;
  SOURCES.forEach((s) => {
    document.getElementById(`ds-${s}`).textContent = state.manifest.sources[s].dataset;
    document.getElementById(`ds-${s}`).title = state.manifest.sources[s].blurb;
  });

  await loadPreflight();
  await newRun();

  dom.advance.addEventListener('click', () => step());
  dom.runall.addEventListener('click', runAll);
  dom.reset.addEventListener('click', newRun);
  dom.theme.addEventListener('click', () => applyTheme(
    document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark',
  ));
  dom.logToggle.addEventListener('click', () => setLogOpen(!dom.log.classList.contains('on')));
  dom.view.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-view]');
    if (btn) applyView(btn.dataset.view);
  });

  // space / right-arrow advances — hands-free from a clicker on stage
  window.addEventListener('keydown', (ev) => {
    if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA') return;
    if (ev.key === ' ' || ev.key === 'ArrowRight') {
      ev.preventDefault();
      if (!dom.advance.disabled) step();
    } else if (ev.key === 'ArrowLeft') {
      const i = state.stages.findIndex((s) => s.id === state.current);
      if (i > 0) show(state.stages[i - 1].id);
    }
  });
}

boot().catch((err) => {
  document.body.appendChild(el('div', {
    class: 'empty empty-fail',
  }, [
    el('div', { class: 'empty-title', text: 'Could not start' }),
    el('div', { class: 'err-detail', text: String(err.message || err) }),
  ]));
});
