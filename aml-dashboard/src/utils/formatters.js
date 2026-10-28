export const fmtINR = (n) => "₹" + n.toLocaleString("en-IN");
export const fmtMin = (m) => { if (m < 60) return m + " min"; const h = Math.floor(m/60), mm = m % 60; return `${h}h ${mm}m`; };
export const fmtHrs = (h) => {
  if (h == null) return "—";
  if (h < 24) { const hh = Math.floor(h), mm = Math.round((h - hh)*60); return `${hh}h ${mm}m`; }
  const d = Math.floor(h/24); const hh = Math.floor(h - d*24); return `${d}d ${hh}h`;
};
export const riskClass = (s) => { if (s >= 90) return "risk-critical"; if (s >= 70) return "risk-red"; if (s >= 40) return "risk-amber"; return "risk-green"; };
export const statusLabel = { unclaimed: "Unclaimed", "in-progress": "In Progress", review: "Pending Review", ready: "STR Ready", closed: "Closed" };
export const statusClass = { unclaimed: "status-unclaimed", "in-progress": "status-progress", review: "status-review", ready: "status-ready", closed: "status-closed" };
