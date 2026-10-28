import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api.js';
import RiskBadge from '@/components/common/RiskBadge.jsx';
import StatusBadge from '@/components/common/StatusBadge.jsx';
import STRStatusBadge from '@/components/common/STRStatusBadge.jsx';
import { Button } from '@/components/ui/button';
import Sidebar from './Sidebar.jsx';
import Timeline from './Timeline.jsx';
import Graph from './Graph.jsx';
import Scrubber from './Scrubber.jsx';
import IntelligencePanel from './IntelligencePanel.jsx';
import STRDrawer from './STRDrawer.jsx';
import ActionModal from './ActionModal.jsx';

export default function Investigation({ caseObj, goBack, toast, openCase, session }) {
  const [inv, setInv] = useState(null);          // full per-case bundle from the API
  const [highlight, setHighlight] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [activeAccount, setActiveAccount] = useState(null);
  const [modal, setModal] = useState(null);
  const [notes, setNotes] = useState([]);
  const [confidence, setConfidence] = useState(50);
  const [strStatus, setStrStatus] = useState("none");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const [playhead, setPlayhead] = useState(0);
  const [isPlaying, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const rafRef = useRef(null);
  const lastTickRef = useRef(0);

  const caseId = caseObj?.id;

  const loadInvestigation = useCallback(async () => {
    if (!caseId) return;
    try {
      const bundle = await api.getInvestigation(caseId);
      setInv(bundle);
      setActiveAccount(bundle.account_profile);
      setNotes(bundle.notes || []);
      setConfidence(bundle.confidence ?? 50);
      setStrStatus(bundle.str_status || "none");
    } catch {
      setInv(null);
    }
  }, [caseId]);

  useEffect(() => { setInv(null); loadInvestigation(); }, [loadInvestigation]);

  useEffect(() => {
    if (!isPlaying) { if (rafRef.current) cancelAnimationFrame(rafRef.current); return; }
    const tick = (now) => {
      if (!lastTickRef.current) lastTickRef.current = now;
      const dt = (now-lastTickRef.current)/1000;
      lastTickRef.current = now;
      setPlayhead(p => { const next = p+(dt*speed/10); if (next >= 1) { setPlaying(false); lastTickRef.current=0; return 1; } return next; });
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); lastTickRef.current=0; };
  }, [isPlaying, speed]);

  const replay = useCallback(() => { setPlayhead(0); lastTickRef.current=0; setPlaying(true); }, []);

  const primaryAccount = inv?.account_profile?.account;
  const onTimelineSelect = useCallback((d) => {
    setSelectedEdge(d.party);
    if (primaryAccount) setHighlight({ type: "edge", from: primaryAccount, to: d.party });
    setTimeout(() => setHighlight(null), 2000);
  }, [primaryAccount]);

  const onNodeClick = useCallback((d) => {
    // clicking a node shows what we know about it; the primary node has the full profile
    if (inv && d.id === inv.account_profile.account) { setActiveAccount(inv.account_profile); return; }
    setActiveAccount({
      account: d.id, type: d.type, opened: "—", dormant: "—", branch: "—",
      kyc: "—", mobile: "—", pan: "—",
      balanceBefore: d.balance, balancePeak: d.balance, balanceCurrent: d.balance,
    });
  }, [inv]);

  const addNote = useCallback(async (body, mentions) => {
    if (!body?.trim()) return;
    try {
      const note = await api.addNote(caseId, body, mentions);
      setNotes((curr) => [...curr, note]);
      if (mentions && mentions.length) mentions.forEach(m => toast({kind:"blue",title:"@Mention sent",msg:`@${m} notified about this case.`}));
      else toast({kind:"blue",title:"Note added",msg:"Comment recorded to case audit trail."});
    } catch {
      toast({kind:"warn",title:"Note failed",msg:"Could not reach the backend."});
    }
  }, [caseId, toast]);

  const changeConfidence = useCallback((v) => {
    setConfidence(v);
    api.updateConfidence(caseId, v).catch(() => { /* non-fatal */ });
  }, [caseId]);

  const openDrawer = () => setDrawerOpen(true);
  const onAction = (kind) => { if (kind === "str") openDrawer(); else setModal(kind); };

  const handleStrStatusChange = (s) => {
    setStrStatus(s);
    if (s === "review") toast({kind:"purple",title:"STR submitted for review",msg:`${caseId} · Ravi Kumar notified.`});
    if (s === "filed") toast({kind:"green",title:"STR filed to FIU-IND",msg:`Reference: FIU-2024-IOB-${Math.floor(Math.random()*99999)}`});
  };

  return (
    <div className={`view invest ${drawerOpen?"drawer-open":""}`}>
      <div className="invest-bar">
        <Button variant="outline" size="sm" className="crumb-back h-auto px-2.5 py-1 text-[11px]" onClick={goBack}>← Back to Pool</Button>
        <div className="crumbs"><span>Case Pool</span><span>→</span><span className="current">{caseObj.id}</span></div>
        <div className="sep"></div>
        <div className="invest-meta">
          <span><strong>{caseObj.account}</strong></span>
          <RiskBadge score={caseObj.score} />
          <StatusBadge status={caseObj.status} />
          <STRStatusBadge strStatus={strStatus} />
          <span className="handoff-pill"><span className="live-dot"></span>You · live session</span>
        </div>
        <div style={{flex:1}}></div>
        <div className="invest-meta">
          <Button variant="sky" size="sm" className="text-[11px]" onClick={() => setModal("audit")} title="Export immutable audit trail">⤓ Audit Export</Button>
          <Button variant="sky" size="sm" className="text-[11px]" onClick={() => setModal("handoff")} title="Hand off to another analyst">↔ Handoff</Button>
          <span style={{color:"var(--muted)",fontSize:11}}>{caseObj.claimedBy ? `Claimed by ${caseObj.claimedBy}` : "Unclaimed"}</span>
        </div>
      </div>

      {!inv ? (
        <div className="invest-center" style={{display:"flex",alignItems:"center",justifyContent:"center",color:"var(--muted)"}}>
          Loading investigation…
        </div>
      ) : (
        <>
          <Sidebar activeAccount={activeAccount} openCase={openCase} />

          <div className="invest-center">
            <Timeline timeline={inv.timeline} onSelect={onTimelineSelect} selected={selectedEdge} playhead={playhead} isPlaying={isPlaying} />
            <Graph graph={inv.graph} highlight={highlight} onNodeClick={onNodeClick} selectedEdge={selectedEdge} playhead={playhead} isPlaying={isPlaying} />
            <Scrubber timeline={inv.timeline} playhead={playhead} setPlayhead={setPlayhead} isPlaying={isPlaying} setPlaying={setPlaying} speed={speed} setSpeed={setSpeed} replay={replay} />
          </div>

          <div className="invest-right">
            <IntelligencePanel
              signals={inv.risk_signals}
              summary={inv.summary}
              iobPattern={inv.iob_pattern}
              totalScore={inv.total_score}
              team={session?.team || []}
              user={session?.user}
              onHighlight={setHighlight}
              onAction={onAction}
              notes={notes}
              addNote={addNote}
              confidence={confidence}
              setConfidence={changeConfidence}
              openCase={openCase}
              strStatus={strStatus}
              setStrStatus={handleStrStatusChange}
              openDrawer={openDrawer}
              caseObj={caseObj}
              activeAccount={activeAccount}
              selectedEdge={selectedEdge}
            />
          </div>
        </>
      )}

      {drawerOpen && (
        <STRDrawer
          caseId={caseId}
          caseObj={caseObj}
          onClose={() => setDrawerOpen(false)}
          onHighlight={setHighlight}
          strStatus={strStatus}
          setStrStatus={handleStrStatusChange}
        />
      )}

      {modal && (
        <ActionModal
          kind={modal}
          caseObj={caseObj}
          audit={inv?.audit || []}
          session={session}
          close={() => setModal(null)}
          toast={toast}
          onMutated={loadInvestigation}
        />
      )}
    </div>
  );
}
