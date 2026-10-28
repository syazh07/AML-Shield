import { tToSec, T_MIN, T_SPAN, BURST_START, BURST_END, formatSec } from '../../utils/timeline.js';

export default function Scrubber({ timeline = [], playhead, setPlayhead, isPlaying, setPlaying, speed, setSpeed, replay }) {
  const burstStartPct = (BURST_START-T_MIN)/T_SPAN;
  const burstEndPct = (BURST_END-T_MIN)/T_SPAN;
  const currentT = T_MIN + playhead * T_SPAN;
  return (
    <div className="scrubber-bar">
      <button className={`play-btn ${isPlaying?"":"paused"}`} onClick={() => { if (playhead >= 0.999) replay(); else setPlaying(!isPlaying); }} title={isPlaying?"Pause":"Play replay"}>{isPlaying?"❚❚":"▶"}</button>
      <button className="speed-btn" style={{border:"1px solid var(--border-strong)",borderRadius:3}} onClick={replay} title="Restart">↺</button>
      <div className="scrub-track">
        <div className="scrub-track-bg"></div>
        <div className="scrub-burst" style={{left:`${burstStartPct*100}%`,width:`${(burstEndPct-burstStartPct)*100}%`}}>
          <div className="scrub-burst-label" style={{left:0}}>BURST 90s</div>
        </div>
        {timeline.map((d,i) => { const pct=(tToSec(d.t)-T_MIN)/T_SPAN; const passed=pct<=playhead; const color=d.dir==="credit"?"#10b981":(d.amt>100000?"#ef4444":"#f59e0b"); return (<div key={i} className={`scrub-event ${passed?"passed":""}`} style={{left:`${pct*100}%`,background:color,opacity:passed?1:0.3}}></div>); })}
        <div className="scrub-playhead" style={{left:`${playhead*100}%`}}></div>
        <input className="scrub-input" type="range" min="0" max="1000" value={Math.round(playhead*1000)} onChange={(e) => { setPlaying(false); setPlayhead(+e.target.value/1000); }} />
      </div>
      <div className="scrub-time">{formatSec(currentT)}</div>
      <div className="speed-group">{[0.5,1,2,4].map(s => (<button key={s} className={`speed-btn ${speed===s?"active":""}`} onClick={() => setSpeed(s)}>{s}×</button>))}</div>
    </div>
  );
}
