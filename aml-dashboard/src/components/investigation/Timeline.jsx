import { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { fmtINR } from '../../utils/formatters.js';
import { tToSec, T_MIN, T_MAX, T_SPAN, BURST_START, BURST_END } from '../../utils/timeline.js';

export default function Timeline({ timeline = [], onSelect, selected, playhead, isPlaying }) {
  const ref = useRef(null);
  const wrapRef = useRef(null);
  const [pop, setPop] = useState(null);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    if (!timeline.length) return;
    const W = wrapRef.current.clientWidth;
    const H = 150;
    svg.attr("viewBox", `0 0 ${W} ${H}`).attr("width","100%").attr("height",H);
    const margin = {l:50,r:50,t:24,b:24};
    const x = d3.scaleLinear().domain([T_MIN-8,T_MAX+8]).range([margin.l,W-margin.r]);
    const maxAmt = d3.max(timeline, d => d.amt);
    const r = d3.scaleSqrt().domain([0,maxAmt]).range([4,22]);
    const baseline = H/2+6;
    const burstX1 = x(BURST_START), burstX2 = x(BURST_END);
    svg.append("rect").attr("x",burstX1).attr("y",baseline-50).attr("width",burstX2-burstX1).attr("height",100).attr("fill","url(#burst-grad)").attr("opacity",0.5);
    const defs = svg.append("defs");
    const grad = defs.append("linearGradient").attr("id","burst-grad").attr("x1","0%").attr("x2","0%").attr("y1","0%").attr("y2","100%");
    grad.append("stop").attr("offset","0%").attr("stop-color","#ef4444").attr("stop-opacity",0.0);
    grad.append("stop").attr("offset","50%").attr("stop-color","#ef4444").attr("stop-opacity",0.12);
    grad.append("stop").attr("offset","100%").attr("stop-color","#ef4444").attr("stop-opacity",0.0);
    svg.append("line").attr("x1",burstX1).attr("x2",burstX1).attr("y1",baseline-40).attr("y2",baseline+40).attr("stroke","#ef4444").attr("stroke-width",1).attr("stroke-dasharray","2 2").attr("opacity",0.6);
    svg.append("line").attr("x1",burstX2).attr("x2",burstX2).attr("y1",baseline-40).attr("y2",baseline+40).attr("stroke","#ef4444").attr("stroke-width",1).attr("stroke-dasharray","2 2").attr("opacity",0.6);
    svg.append("text").attr("x",(burstX1+burstX2)/2).attr("y",baseline-44).attr("text-anchor","middle").attr("font-family","JetBrains Mono").attr("font-size",9).attr("fill","#ef4444").attr("letter-spacing","0.06em").text("⚠ 90-SECOND BURST WINDOW");
    svg.append("line").attr("x1",margin.l).attr("x2",W-margin.r).attr("y1",baseline).attr("y2",baseline).attr("stroke","#243d59").attr("stroke-width",1);
    // Decide which time labels to render so clustered events (the burst) don't overlap.
    const labelShow = new Set();
    let lastLabelX = -Infinity;
    [...timeline].map(d => ({ d, px: x(tToSec(d.t)) })).sort((a,b) => a.px - b.px).forEach(({d,px}) => {
      if (px - lastLabelX >= 34) { labelShow.add(d); lastLabelX = px; }
    });
    timeline.forEach((d,i) => {
      const tt = tToSec(d.t);
      svg.append("line").attr("x1",x(tt)).attr("x2",x(tt)).attr("y1",baseline-3).attr("y2",baseline+3).attr("stroke","#243d59");
      if (labelShow.has(d)) svg.append("text").attr("x",x(tt)).attr("y",baseline+18).attr("text-anchor","middle").attr("font-family","JetBrains Mono").attr("font-size",9).attr("fill","#64748b").text(d.t);
    });
    timeline.forEach((d,i) => {
      const eventT = tToSec(d.t);
      const cx = x(eventT);
      const radius = r(d.amt);
      const isCredit = d.dir === "credit";
      const cy = isCredit ? baseline-radius-6 : baseline+radius+6;
      const color = isCredit ? "#10b981" : (d.amt > 100000 ? "#ef4444" : "#f59e0b");
      svg.append("line").attr("class",`stem-${i}`).attr("x1",cx).attr("x2",cx).attr("y1",baseline).attr("y2",cy).attr("stroke",color).attr("stroke-width",1).attr("opacity",0.4);
      const g = svg.append("g").attr("class",`event-${i}`).attr("data-event-time",eventT).style("cursor","pointer")
        .on("mouseenter", function(ev) { const rect = wrapRef.current.getBoundingClientRect(); setPop({d,x:ev.clientX-rect.left,y:ev.clientY-rect.top}); d3.select(this).select("circle.glow").attr("opacity",0.4); })
        .on("mousemove", function(ev) { const rect = wrapRef.current.getBoundingClientRect(); setPop({d,x:ev.clientX-rect.left,y:ev.clientY-rect.top}); })
        .on("mouseleave", function() { setPop(null); d3.select(this).select("circle.glow").attr("opacity",selected===d.party?0.4:0); })
        .on("click", () => onSelect && onSelect(d));
      g.append("circle").attr("class","glow").attr("cx",cx).attr("cy",cy).attr("r",radius+6).attr("fill",color).attr("opacity",selected===d.party?0.4:0);
      g.append("circle").attr("class","body").attr("cx",cx).attr("cy",cy).attr("r",radius).attr("fill",color).attr("opacity",0.18).attr("stroke",color).attr("stroke-width",1.5);
      g.append("text").attr("x",cx).attr("y",cy+3).attr("text-anchor","middle").attr("font-family","JetBrains Mono").attr("font-size",radius>14?10:9).attr("font-weight",600).attr("fill",color).text(d.amt>=100000?"₹"+(d.amt/100000).toFixed(1)+"L":"₹"+(d.amt/1000)+"k");
    });
    svg.append("line").attr("id","tl-playhead").attr("y1",baseline-60).attr("y2",baseline+50).attr("stroke","#0ea5e9").attr("stroke-width",1.5).attr("opacity",0).style("filter","drop-shadow(0 0 4px #0ea5e9)");
    svg.append("text").attr("x",4).attr("y",baseline-30).attr("font-family","Inter").attr("font-size",9).attr("fill","#64748b").text("CREDITS ↑");
    svg.append("text").attr("x",4).attr("y",baseline+38).attr("font-family","Inter").attr("font-size",9).attr("fill","#64748b").text("DEBITS ↓");
  }, [selected, onSelect, timeline]);

  useEffect(() => {
    const svg = d3.select(ref.current);
    if (!wrapRef.current) return;
    const W = wrapRef.current.clientWidth;
    const margin = {l:50,r:50};
    const x = d3.scaleLinear().domain([T_MIN-8,T_MAX+8]).range([margin.l,W-margin.r]);
    const currentT = T_MIN + playhead * T_SPAN;
    const phX = x(currentT);
    if (isPlaying || playhead > 0.001) {
      svg.select("#tl-playhead").attr("x1",phX).attr("x2",phX).attr("opacity",1);
      timeline.forEach((d,i) => { const passed = tToSec(d.t) <= currentT; svg.select(`.event-${i}`).attr("opacity",passed?1:0.25); svg.select(`.stem-${i}`).attr("opacity",passed?0.4:0.1); });
    } else {
      svg.select("#tl-playhead").attr("opacity",0);
      timeline.forEach((d,i) => { svg.select(`.event-${i}`).attr("opacity",1); svg.select(`.stem-${i}`).attr("opacity",0.4); });
    }
  }, [playhead, isPlaying, timeline]);

  return (
    <div className="timeline-wrap" ref={wrapRef}>
      <div className="timeline-stat">{(() => { const c = timeline.find(d => d.dir === "credit"); const out = timeline.filter(d => d.dir === "debit").reduce((a,d)=>a+d.amt,0); return c ? Math.round(out/c.amt*100) : 0; })()}% of funds transferred within 90s of receipt</div>
      <svg id="timeline-svg" ref={ref}></svg>
      {pop && (
        <div className="tl-popover" style={{left:Math.min(pop.x+14,(wrapRef.current?.clientWidth||600)-250),top:Math.max(pop.y-80,10)}}>
          <div className="pop-amt" style={{color:pop.d.dir==="credit"?"#10b981":"#ef4444"}}>{pop.d.dir==="credit"?"+":"−"}{fmtINR(pop.d.amt)}</div>
          <div className="pop-row"><span className="k">Direction</span><span className="v">{pop.d.dir.toUpperCase()}</span></div>
          <div className="pop-row"><span className="k">Counterparty</span><span className="v">{pop.d.party}</span></div>
          <div className="pop-row"><span className="k">Channel</span><span className="v">{pop.d.channel}</span></div>
          <div className="pop-row"><span className="k">Time</span><span className="v">{pop.d.t}</span></div>
          <div className="pop-flag"><span>⚠</span><span>{pop.d.flag}</span></div>
        </div>
      )}
    </div>
  );
}
