// Client-side audit-trail export. Produces a real downloadable file for the
// selected format — no backend round-trip and no extra dependencies. The audit
// array is the same [{ ts, actor, action, hash }] shape rendered in the modal.

function triggerDownload(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const csvCell = (v) => {
  const s = String(v ?? '');
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const xmlText = (v) =>
  String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');

function fileStamp() {
  return new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
}

function buildCSV(caseObj, audit) {
  const rows = [
    ['seq', 'timestamp', 'actor', 'action', 'chain_hash'],
    ...audit.map((r, i) => [i + 1, r.ts, r.actor, r.action, r.hash]),
  ];
  return rows.map((cols) => cols.map(csvCell).join(',')).join('\r\n');
}

function buildJSON(caseObj, audit) {
  return JSON.stringify(
    {
      report: 'AML Shield — Immutable Audit Trail',
      caseId: caseObj.id,
      account: caseObj.account ?? null,
      riskScore: caseObj.score ?? null,
      exportedAt: new Date().toISOString(),
      entryCount: audit.length,
      chain: 'append-only · SHA-256',
      entries: audit.map((r, i) => ({
        seq: i + 1,
        timestamp: r.ts,
        actor: r.actor,
        action: r.action,
        hash: r.hash,
      })),
    },
    null,
    2
  );
}

function buildXML(caseObj, audit) {
  const entries = audit
    .map(
      (r, i) =>
        `    <AuditEntry seq="${i + 1}">\n` +
        `      <Timestamp>${xmlText(r.ts)}</Timestamp>\n` +
        `      <Actor>${xmlText(r.actor)}</Actor>\n` +
        `      <Action>${xmlText(r.action)}</Action>\n` +
        `      <ChainHash>${xmlText(r.hash)}</ChainHash>\n` +
        `    </AuditEntry>`
    )
    .join('\n');
  return (
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<FIUINDReport xmlns="http://fiuindia.gov.in/finnet/str" schemaVersion="2.0">\n` +
    `  <Header>\n` +
    `    <ReportType>AUDIT_TRAIL</ReportType>\n` +
    `    <CaseReference>${xmlText(caseObj.id)}</CaseReference>\n` +
    `    <Account>${xmlText(caseObj.account ?? '')}</Account>\n` +
    `    <RiskScore>${xmlText(caseObj.score ?? '')}</RiskScore>\n` +
    `    <GeneratedAt>${xmlText(new Date().toISOString())}</GeneratedAt>\n` +
    `    <EntryCount>${audit.length}</EntryCount>\n` +
    `  </Header>\n` +
    `  <AuditTrail>\n${entries}\n  </AuditTrail>\n` +
    `</FIUINDReport>\n`
  );
}

function exportPDF(caseObj, audit) {
  // No PDF library bundled — render a print-ready document and let the browser's
  // "Save as PDF" produce the file. Opened from a user click so it isn't blocked.
  const win = window.open('', '_blank', 'width=820,height=900');
  if (!win) throw new Error('popup-blocked');
  const rows = audit
    .map(
      (r, i) =>
        `<tr><td class="seq">${i + 1}</td><td class="ts">${xmlText(r.ts)}</td>` +
        `<td class="actor">${xmlText(r.actor)}</td><td>${xmlText(r.action)}</td>` +
        `<td class="hash">${xmlText(r.hash)}</td></tr>`
    )
    .join('');
  win.document.write(`<!doctype html><html><head><meta charset="utf-8">
    <title>Audit Trail — ${xmlText(caseObj.id)}</title>
    <style>
      *{box-sizing:border-box} body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#0f172a;margin:32px;font-size:12px}
      h1{font-size:16px;margin:0 0 2px} .sub{color:#64748b;font-size:11px;margin:0 0 16px}
      .meta{display:flex;gap:24px;font-size:11px;color:#334155;margin-bottom:16px;flex-wrap:wrap}
      .meta b{color:#0f172a}
      table{width:100%;border-collapse:collapse;font-size:11px}
      th{text-align:left;border-bottom:2px solid #0f172a;padding:6px 8px;font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:#475569}
      td{padding:6px 8px;border-bottom:1px solid #e2e8f0;vertical-align:top}
      .seq{color:#94a3b8;width:34px} .ts,.hash,.actor{font-family:ui-monospace,Menlo,monospace}
      .ts{color:#64748b;white-space:nowrap} .actor{color:#2563eb} .hash{color:#94a3b8;font-size:10px}
      .foot{margin-top:16px;font-size:10px;color:#94a3b8}
    </style></head><body>
    <h1>AML Shield — Immutable Audit Trail</h1>
    <p class="sub">Cryptographically chained, append-only record</p>
    <div class="meta">
      <span><b>Case</b> ${xmlText(caseObj.id)}</span>
      ${caseObj.account ? `<span><b>Account</b> ${xmlText(caseObj.account)}</span>` : ''}
      ${caseObj.score != null ? `<span><b>Risk score</b> ${xmlText(caseObj.score)}</span>` : ''}
      <span><b>Entries</b> ${audit.length}</span>
      <span><b>Exported</b> ${xmlText(new Date().toLocaleString())}</span>
    </div>
    <table><thead><tr><th>#</th><th>Time</th><th>Actor</th><th>Action</th><th>Chain hash</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="5">No audit entries yet.</td></tr>'}</tbody></table>
    <p class="foot">Generated by AML Shield · SHA-256 append-only chain · ${audit.length} entries</p>
    </body></html>`);
  win.document.close();
  win.focus();
  // Give the new document a tick to lay out before invoking print.
  setTimeout(() => win.print(), 250);
}

// Runs the export for `format` ('PDF' | 'CSV' | 'JSON' | 'FIU-IND XML').
// Returns a short status string for the toast.
export function exportAudit(format, caseObj, audit = []) {
  const base = `audit-${caseObj.id}-${fileStamp()}`;
  switch (format) {
    case 'CSV':
      triggerDownload(`${base}.csv`, buildCSV(caseObj, audit), 'text/csv;charset=utf-8');
      return `Audit trail downloaded as CSV`;
    case 'JSON':
      triggerDownload(`${base}.json`, buildJSON(caseObj, audit), 'application/json');
      return `Audit trail downloaded as JSON`;
    case 'FIU-IND XML':
      triggerDownload(`${base}.xml`, buildXML(caseObj, audit), 'application/xml');
      return `Audit trail downloaded as FIU-IND XML`;
    case 'PDF':
    default:
      exportPDF(caseObj, audit);
      return `Audit trail opened for PDF export`;
  }
}
