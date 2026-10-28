import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import STRDraftPanel from './STRDraftPanel.jsx';
import AIChatPanel from './AIChatPanel.jsx';

export default function IntelligencePanel({ signals = [], summary, iobPattern, totalScore, team = [], user, onHighlight, onAction, notes, addNote, confidence, setConfidence, openCase, strStatus, setStrStatus, openDrawer, caseObj, activeAccount, selectedEdge }) {
  const [activeTab, setActiveTab] = useState("intelligence");
  const [hoveredSignal, setHoveredSignal] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [lang, setLang] = useState("en");
  const [draft, setDraft] = useState("");
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  const inputRef = useRef(null);
  const scoreTag = totalScore >= 80 ? "CRITICAL" : totalScore >= 50 ? "HIGH" : "MEDIUM";

  const toggleExpand = (id) => setExpanded(e => ({...e, [id]:!e[id]}));

  const onDraftChange = (e) => {
    const v = e.target.value;
    setDraft(v);
    const lastAt = v.lastIndexOf("@");
    if (lastAt >= 0) { const after = v.slice(lastAt+1); if (!after.includes(" ") && after.length < 20) { setShowMentions(true); setMentionQuery(after); return; } }
    setShowMentions(false);
  };
  const insertMention = (handle) => { const lastAt = draft.lastIndexOf("@"); setDraft(draft.slice(0,lastAt)+"@"+handle+" "); setShowMentions(false); inputRef.current?.focus(); };
  const filteredTeam = team.filter(t => t.handle.toLowerCase().startsWith(mentionQuery.toLowerCase()));

  const submitNote = () => {
    if (!draft.trim()) return;
    const mentions = (draft.match(/@\w+/g)||[]).map(s=>s.slice(1));
    addNote(draft, mentions);
    setDraft("");
  };

  const renderBody = (body) => body.split(/(@\w+)/).map((part,i) => part.startsWith("@") ? <span key={i} className="mention">{part}</span> : <span key={i}>{part}</span>);

  const confColor = confidence >= 80 ? "var(--red)" : confidence >= 50 ? "var(--amber)" : "var(--green)";
  const confLabel = confidence >= 80 ? "High — confirm mule" : confidence >= 50 ? "Medium — escalate" : confidence >= 20 ? "Low — investigate further" : "Likely false positive";

  const strDrafted = strStatus !== "none";

  return (
    <>
      <div className="right-tabs">
        <button className={`right-tab ${activeTab==="intelligence"?"active":""}`} onClick={() => setActiveTab("intelligence")}>
          Intelligence <span className="tab-badge">{signals.length}</span>
        </button>
        <button className={`right-tab ${activeTab==="notes"?"active":""}`} onClick={() => setActiveTab("notes")}>
          Notes <span className="tab-badge">{notes.length}</span>
        </button>
        <button className={`right-tab ${activeTab==="str"?"active":""}`} onClick={() => setActiveTab("str")}>
          STR Draft {strStatus==="drafting" && <span className="str-tab-dot"></span>}
          {strDrafted && <span className="tab-badge" style={strStatus==="filed"?{background:"rgba(16,185,129,0.15)",borderColor:"rgba(16,185,129,0.3)",color:"var(--green)"}:{}}>{strStatus==="filed"?"Filed":strStatus==="review"?"Review":"Draft"}</span>}
        </button>
        <button className={`right-tab ${activeTab==="copilot"?"active":""}`} onClick={() => setActiveTab("copilot")}>
          Copilot
        </button>
      </div>

      {activeTab === "intelligence" && (
        <>
          <div className="right-scroll scroll">
            <div className="risk-bars">
              {signals.map(s => {
                const isOpen = !!expanded[s.id];
                return (
                  <div key={s.id} className={`risk-row ${hoveredSignal===s.id?"active":""} ${isOpen?"expanded":""}`}
                    onMouseEnter={() => { setHoveredSignal(s.id); onHighlight(s.highlight); }}
                    onMouseLeave={() => { setHoveredSignal(null); onHighlight(null); }}>
                    <div onClick={() => toggleExpand(s.id)}>
                      <div className="risk-row-top">
                        <span className="risk-row-title"><span className="expand-chev">{isOpen?"▾":"▸"}</span>{s.title}</span>
                        <span className="risk-row-pts">+{s.pts}</span>
                      </div>
                      <div className="risk-row-desc" style={{paddingLeft:16}}>{s.desc}</div>
                      <div className="risk-bar-track" style={{marginLeft:16}}><div className="risk-bar-fill" style={{width:(s.pts/30*100)+"%"}}></div></div>
                    </div>
                    {isOpen && (
                      <div className="evidence-card">
                        <div className="evidence-row"><span className="ek">Rule</span><span className="ev" style={{color:"var(--blue)"}}>{s.rule}</span></div>
                        <div className="evidence-row"><span className="ek">Formula</span><span className="ev" style={{fontSize:10}}>{s.formula}</span></div>
                        <div className="evidence-section">
                          <div className="es-title">Evidence (from this case)</div>
                          {s.evidence.map((e,i) => (<div key={i} className={`evidence-row ${e.emp?"emp":""}`}><span className="ek">{e.k}</span><span className="ev">{e.link?<span className="evidence-link" onClick={(ev)=>{ev.stopPropagation();openCase&&openCase(e.link);}}>{e.v}</span>:e.v}</span></div>))}
                        </div>
                        <div className="evidence-section">
                          <div className="es-title">Model</div>
                          <div className="model-meta">
                            <div className="mm"><div className="mm-k">Weight</div><div className="mm-v">{s.model.weight}</div></div>
                            <div className="mm"><div className="mm-k">Precision</div><div className="mm-v">{s.model.precision}</div></div>
                            <div className="mm"><div className="mm-k">Trained on</div><div className="mm-v">{s.model.trained}</div></div>
                          </div>
                        </div>
                        <div className="evidence-trace">⊙ {s.trace}</div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="risk-total"><div><div className="rt-label">Total Risk Score</div><div className="rt-tag">{scoreTag}</div></div><div className="rt-val">{totalScore}</div></div>
            {iobPattern && (
              <div className="iob-flag">
                <h4>⚑ IOB Pattern: {iobPattern.title}</h4>
                <div className="iob-flag-detail">{iobPattern.detail}</div>
                <div className="iob-flag-extra">{iobPattern.extra}</div>
              </div>
            )}
            <div className="summary-section">
              <div className="summary-tabs">
                <button className={`summary-tab ${lang==="en"?"active":""}`} onClick={() => setLang("en")}>English</button>
                <button className={`summary-tab ${lang==="ta"?"active":""}`} onClick={() => setLang("ta")}>தமிழ்</button>
              </div>
              <div className={`summary-body ${lang==="ta"?"tamil":""}`}>{lang==="en"?summary?.en:summary?.ta}</div>
            </div>
          </div>
          <div className="confidence-bar">
            <div className="confidence-head"><span className="ch-label">Analyst Confidence — {confLabel}</span><span className="ch-val" style={{color:confColor}}>{confidence}%</span></div>
            <Slider value={[confidence]} min={0} max={100} step={1} onValueChange={([v]) => setConfidence(v)} className="py-2" />
            <div className="confidence-scale"><span>0 · False positive</span><span>50 · Uncertain</span><span>100 · Confirmed mule</span></div>
          </div>
          <div className="action-bar">
            <Button variant="danger" size="lg" className="h-auto py-2 text-[11px]" onClick={() => onAction("confirm")}>⚑ Confirm Mule</Button>
            <Button variant="success" size="lg" className="h-auto py-2 text-[11px]" onClick={() => onAction("fp")}>✓ Mark False Positive</Button>
            <Button variant="warning" size="lg" className="h-auto py-2 text-[11px]" onClick={() => onAction("hold")}>⏸ Place Debit Hold</Button>
            <Button size="lg" className="h-auto py-2 text-[11px]" onClick={() => onAction("escalate")}>↑ Escalate to Senior</Button>
            <Button variant="purple" size="lg" className="col-span-full h-auto py-2 text-[11px]" onClick={() => { setActiveTab("str"); onAction("str"); }}>
              {strStatus==="none"?"⊕ Generate STR Draft":strStatus==="filed"?"⊞ STR Filed — View":"⊙ Open STR Draft"}
            </Button>
          </div>
        </>
      )}

      {activeTab === "notes" && (
        <div className="notes-content">
          <div className="notes-list scroll">
            {notes.map(n => (
              <div key={n.id} className={`note ${n.kind==="system"?"system":""}`}>
                <div className="note-head">
                  <div className={`note-avatar ${n.kind==="system"?"bot":""}`}>{n.kind==="system"?"⚙":n.author.split(" ").map(p=>p[0]).join("").slice(0,2)}</div>
                  <span className="note-author">{n.author}</span>
                  <span className="note-role">· {n.role}</span>
                  <span className="note-time">{n.time}</span>
                </div>
                <div className="note-body">{renderBody(n.body)}</div>
              </div>
            ))}
          </div>
          <div className="notes-input-wrap">
            {showMentions && filteredTeam.length > 0 && (
              <div className="mention-dropdown">
                {filteredTeam.map(t => (<div key={t.handle} className="mention-item" onMouseDown={e => { e.preventDefault(); insertMention(t.handle); }}><div className="note-avatar" style={{width:18,height:18,fontSize:8}}>{t.name.split(" ").map(p=>p[0]).join("")}</div><div>@{t.handle}<br/><small>{t.name} · {t.role}</small></div></div>))}
              </div>
            )}
            <Textarea ref={inputRef} className="notes-input min-h-[60px] resize-none text-[11px]" value={draft} onChange={onDraftChange} placeholder="Add a note · type @ to mention a teammate" />
            <div className="notes-input-row"><span className="notes-meta">{draft.length} chars · audit-logged</span><Button size="sm" className="text-[11px]" onClick={submitNote}>Add Note</Button></div>
          </div>
        </div>
      )}

      {activeTab === "str" && (
        <STRDraftPanel
          caseId={caseObj?.id}
          confidence={confidence}
          strStatus={strStatus}
          setStrStatus={setStrStatus}
          onCiteHighlight={onHighlight}
          openDrawer={openDrawer}
        />
      )}

      {activeTab === "copilot" && (
        <AIChatPanel
          caseObj={caseObj}
          activeAccount={activeAccount}
          selectedEdge={selectedEdge}
          onHighlight={onHighlight}
          openCase={openCase}
        />
      )}
    </>
  );
}
