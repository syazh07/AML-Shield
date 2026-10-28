import { useState, useEffect } from 'react';
import { api } from '@/lib/api.js';
import { Button } from '@/components/ui/button';

export default function STRDrawer({ caseId, caseObj, onClose, onHighlight, strStatus, setStrStatus }) {
  const [draft, setDraft] = useState(null);
  const [drawerTab, setDrawerTab] = useState('narrative');
  const [citedChip, setCitedChip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [narrativeDraft, setNarrativeDraft] = useState('');
  const [saveState, setSaveState] = useState('idle');  // idle | saving | saved

  useEffect(() => {
    let cancelled = false;
    const pollJob = async (jobId) => {
      for (let i = 0; i < 90; i++) {
        const j = await api.strJob(caseId, jobId);
        if (j.status === 'completed') return j.draft || api.strGet(caseId);
        if (j.status === 'failed') return null;
        await new Promise((r) => setTimeout(r, 400));
      }
      // Timed out on the job; the draft may still have persisted server-side.
      return api.strGet(caseId).catch(() => null);
    };
    (async () => {
      setLoading(true);
      try {
        let d = await api.strGet(caseId);
        if (!d) {                                   // no draft yet → generate one
          const job = await api.strGenerate(caseId);
          d = await pollJob(job.job_id);
          if (d) setStrStatus('drafting');
        }
        if (!cancelled) setDraft(d);
      } catch { if (!cancelled) setDraft(null); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [caseId]);

  const handleCiteHover = (seg) => { setCitedChip(seg.chipId); onHighlight(seg.highlight); };
  const handleCiteLeave = () => { setCitedChip(null); onHighlight(null); };

  const submitReview = async () => { try { await api.strSubmitReview(caseId); } catch { /* ignore */ } setStrStatus('review'); };
  const fileStr = async () => { try { await api.strFile(caseId); } catch { /* ignore */ } setStrStatus('filed'); onClose(); };

  const startEdit = () => { setNarrativeDraft(draft?.narrative || ''); setEditing(true); setSaveState('idle'); };
  const cancelEdit = () => { setEditing(false); setSaveState('idle'); };
  const saveNarrative = async () => {
    setSaveState('saving');
    try {
      const updated = await api.strUpdate(caseId, { narrative: narrativeDraft });
      setDraft(updated);
      setEditing(false);
      setSaveState('saved');
      setTimeout(() => setSaveState('idle'), 2000);
    } catch { setSaveState('idle'); }
  };
  const toggleChip = async (id) => {
    const next = (draft?.evidenceChips || []).map((c) => (c.id === id ? { ...c, checked: !c.checked } : c));
    setDraft((d) => ({ ...d, evidenceChips: next }));           // optimistic
    try { const updated = await api.strUpdate(caseId, { evidenceChips: next }); setDraft(updated); }
    catch { /* keep optimistic state */ }
  };

  const narrative = draft?.narrative || '';
  const citeSegments = draft?.citeSegments || [];
  const entities = draft?.entities || [];
  const chips = draft?.evidenceChips || [];
  const compliance = draft?.complianceItems || [];
  const wordCount = narrative.trim() ? narrative.trim().split(/\s+/).length : 0;

  const renderNarrative = () => {
    if (!citeSegments.length) return <span>{narrative}</span>;
    let remaining = narrative;
    const parts = [];
    let key = 0;
    citeSegments.forEach((seg) => {
      const idx = remaining.indexOf(seg.text);
      if (idx >= 0) {
        if (idx > 0) parts.push(<span key={key++}>{remaining.slice(0, idx)}</span>);
        parts.push(
          <span key={key++} className={`str-cite ${citedChip===seg.chipId?"graph-lit":""}`}
            onMouseEnter={() => handleCiteHover(seg)} onMouseLeave={handleCiteLeave}
            title="Hover to cite in graph">
            {seg.text}
          </span>
        );
        remaining = remaining.slice(idx + seg.text.length);
      }
    });
    if (remaining) parts.push(<span key={key++}>{remaining}</span>);
    return parts;
  };

  return (
    <div className="str-drawer">
      <div className="drawer-head">
        <div className="drawer-title">
          STR Draft
          <span className="drawer-badge">FIU-IND FORMAT</span>
          <span className={`str-status-badge ${strStatus==="drafting"?"str-badge-drafting":strStatus==="review"?"str-badge-review":strStatus==="filed"?"str-badge-filed":"str-badge-none"}`} style={{marginLeft:4}}>
            <span className="str-badge-dot"></span>
            {strStatus==="drafting"?"Drafting":strStatus==="review"?"Pending Review":strStatus==="filed"?"Filed":"Draft"}
          </span>
        </div>
        <div className="drawer-tabs" style={{marginLeft:14}}>
          {["narrative","entities","attachments"].map(t => (
            <button key={t} className={`drawer-tab ${drawerTab===t?"active":""}`} onClick={() => setDrawerTab(t)}>
              {t.charAt(0).toUpperCase()+t.slice(1)}
            </button>
          ))}
        </div>
        <div className="spacer"></div>
        <div style={{display:"flex",gap:8,alignItems:"center"}}>
          <Button variant="sky" size="sm" className="text-[11px]" onClick={submitReview}>↑ Submit for Senior Review</Button>
          <Button size="sm" className="text-[11px]" onClick={fileStr}>⊞ File to FIU-IND</Button>
          <button className="drawer-close" onClick={onClose}>×</button>
        </div>
      </div>

      <div className="drawer-body">
        <div className="drawer-main">
          {loading && <div style={{padding:24,color:"var(--muted)",fontSize:12}}>Generating STR draft…</div>}
          {!loading && drawerTab === "narrative" && (
            <>
              <div style={{marginBottom:10,display:"flex",alignItems:"center",gap:12}}>
                <div style={{fontSize:11,color:"var(--muted)"}}>Case: <span style={{fontFamily:"var(--mono)",color:"var(--blue)"}}>{caseObj?.id}</span></div>
                <div style={{fontSize:11,color:"var(--muted)"}}>Account: <span style={{fontFamily:"var(--mono)",color:"var(--text)"}}>{caseObj?.account}</span></div>
              </div>
              <div style={{display:"flex",alignItems:"center",marginBottom:8,gap:8}}>
                <div style={{fontSize:11,color:"var(--muted)",fontWeight:600,textTransform:"uppercase",letterSpacing:"0.08em"}}>Narrative</div>
                <div style={{marginLeft:"auto",display:"flex",alignItems:"center",gap:8}}>
                  {saveState==="saved" && <span style={{fontSize:10,color:"var(--green)"}}>✓ Saved</span>}
                  {!editing ? (
                    <Button variant="sky" size="sm" className="text-[11px]" onClick={startEdit} disabled={strStatus==="filed"}>✎ Edit</Button>
                  ) : (
                    <>
                      <Button variant="outline" size="sm" className="text-[11px]" onClick={cancelEdit}>Cancel</Button>
                      <Button size="sm" className="text-[11px]" onClick={saveNarrative} disabled={saveState==="saving"}>{saveState==="saving"?"Saving…":"✓ Save"}</Button>
                    </>
                  )}
                </div>
              </div>
              {!editing && (
                <div className="cite-graph-banner">
                  <span className="cg-icon">⟳</span>
                  <span><strong>Cite-to-Graph:</strong> Hover highlighted phrases to illuminate the corresponding node or edge in the transaction graph above.</span>
                </div>
              )}
              <div className="drawer-narrative-wrap">
                {editing ? (
                  <textarea
                    className="drawer-narrative"
                    style={{minHeight:200,width:"100%",resize:"vertical",background:"var(--bg)",border:"1px solid var(--border-strong)",borderRadius:3,padding:"10px 12px",fontSize:12,lineHeight:1.7,color:"var(--text)",fontFamily:"inherit"}}
                    value={narrativeDraft}
                    onChange={(e) => setNarrativeDraft(e.target.value)}
                    placeholder="Draft the STR narrative…"
                    autoFocus
                  />
                ) : (
                  <div className="drawer-narrative" style={{minHeight:160,overflowY:"auto",cursor:"text"}}>
                    {renderNarrative()}
                  </div>
                )}
                <div className="drawer-hint">
                  {editing
                    ? <span><span className="hint-tag">Editing</span> changes are saved to the case draft on Save</span>
                    : <><span className="hint-tag">Hover</span> highlighted text to cross-reference the graph</>}
                  <span style={{marginLeft:"auto",fontFamily:"var(--mono)",color:"var(--muted)",fontSize:10}}>{(editing ? (narrativeDraft.trim() ? narrativeDraft.trim().split(/\s+/).length : 0) : wordCount)} words · FIU-IND min: 100</span>
                </div>
              </div>
              <div className="str-fields">
                <div className="str-field"><label>Reporting Entity</label><input defaultValue="Indian Overseas Bank" /></div>
                <div className="str-field"><label>Report Type</label><select defaultValue="STR"><option>STR (Suspicious Transaction Report)</option><option>CTR (Cash Transaction Report)</option></select></div>
                <div className="str-field"><label>Alert Reference</label><input defaultValue={caseObj?.id} /></div>
                <div className="str-field full"><label>Primary Account</label><input defaultValue={`${caseObj?.account} — ${caseObj?.type || ''}`} /></div>
                <div className="str-field"><label>Analyst Confidence</label><input defaultValue={draft?.analystConfidence != null ? `${draft.analystConfidence}%` : "—"} /></div>
              </div>
            </>
          )}
          {!loading && drawerTab === "entities" && (
            <div>
              <div style={{marginBottom:12,fontSize:11,color:"var(--muted)"}}>All entities linked to this suspicious activity report.</div>
              <table className="str-entity-table" style={{width:"100%"}}>
                <thead><tr><th>Account</th><th>Type</th><th>Role in Pattern</th><th>Amount</th><th>Notes</th></tr></thead>
                <tbody>
                  {entities.map((e,i) => (
                    <tr key={i}>
                      <td className="hl">{e.account}</td>
                      <td>{e.type}</td>
                      <td style={{color:"var(--amber)"}}>{e.role}</td>
                      <td>{e.amount}</td>
                      <td style={{color:"var(--text-dim)",fontSize:10}}>{e.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!loading && drawerTab === "attachments" && (
            <div>
              <div style={{marginBottom:12,fontSize:11,color:"var(--muted)"}}>Evidence attachments to include with the STR filing.</div>
              {[
                { label:"Transaction graph (PNG)", checked:true, size:"42 KB" },
                { label:"Timeline replay export", checked:true, size:"18 KB" },
                { label:`Audit trail (case ${caseObj?.id})`, checked:true, size:"6 KB" },
              ].map((a,i) => (
                <div key={i} style={{display:"flex",alignItems:"center",gap:12,padding:"9px 12px",background:"var(--panel-2)",border:"1px solid var(--border)",borderRadius:3,marginBottom:6}}>
                  <input type="checkbox" defaultChecked={a.checked} style={{accentColor:"var(--blue)"}} />
                  <span style={{flex:1,fontSize:12,color:"var(--text)"}}>{a.label}</span>
                  <span style={{fontFamily:"var(--mono)",fontSize:10,color:"var(--muted)"}}>{a.size}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="drawer-sidebar">
          <div style={{fontSize:9,color:"var(--muted)",textTransform:"uppercase",letterSpacing:"0.1em",fontWeight:600,marginBottom:10}}>Evidence References</div>
          <div style={{display:"flex",flexDirection:"column",gap:6}}>
            {chips.map(chip => (
              <div key={chip.id} className={`evidence-chip ${chip.cls}`} style={{justifyContent:"flex-start",fontSize:10,opacity:chip.checked===false?0.4:1,cursor:strStatus==="filed"?"default":"pointer"}}
                onClick={() => strStatus!=="filed" && toggleChip(chip.id)} title="Toggle whether this rule is cited in the filing">
                <span className="chip-check">{chip.checked===false?"☐":"☑"}</span>{chip.label}
              </div>
            ))}
          </div>
          <div style={{marginTop:16,fontSize:9,color:"var(--muted)",textTransform:"uppercase",letterSpacing:"0.1em",fontWeight:600,marginBottom:10}}>Compliance</div>
          <div className="compliance-list">
            {compliance.map((item,i) => (
              <div key={i} className={`compliance-item ${item.status}`} style={{fontSize:10}}>
                <span className="ci-icon" style={{color:item.status==="ok"?"var(--green)":item.status==="warn"?"var(--amber)":"var(--red)"}}>{item.icon}</span>
                <span className="ci-label" style={{fontSize:10}}>{item.label}</span>
              </div>
            ))}
          </div>
          {draft?.fiuReference && (
            <div style={{marginTop:16,padding:"8px 10px",background:"rgba(16,185,129,0.08)",border:"1px solid rgba(16,185,129,0.25)",borderRadius:3}}>
              <div style={{fontSize:9,color:"var(--green)",textTransform:"uppercase",letterSpacing:"0.1em",fontWeight:600,marginBottom:4}}>FIU-IND Reference</div>
              <div style={{fontFamily:"var(--mono)",fontSize:13,color:"var(--text)",fontWeight:600}}>{draft.fiuReference}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
