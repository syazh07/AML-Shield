import { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { fmtINR } from '../../utils/formatters.js';
import { tToSec, T_MIN, T_SPAN } from '../../utils/timeline.js';
import { Button } from '@/components/ui/button';

const GRAPH_W = 960;
const GRAPH_H = 540;

// Fixed layout by topology slot (source, primary, relay-1, relay-2, cash-out, linked).
// Bundles always emit nodes in this order, so positions work for every case.
const NODE_POS = [
  { x: 200, y: 270 },
  { x: 420, y: 270 },
  { x: 660, y: 140 },
  { x: 680, y: 240 },
  { x: 680, y: 360 },
  { x: 660, y: 440 },
];

export default function Graph({ graph, highlight, onNodeClick, selectedEdge, playhead, isPlaying }) {
  const ref = useRef(null);
  const wrapRef = useRef(null);
  const [tip, setTip] = useState(null);

  const gnodes = graph?.nodes || [];
  const glinks = graph?.links || [];
  const primaryId = gnodes.find((n) => n.role === 'primary')?.id;

  useEffect(() => {
    if (!ref.current || !gnodes.length) return;

    const svg = d3.select(ref.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${GRAPH_W} ${GRAPH_H}`).attr('preserveAspectRatio', 'xMidYMid meet');

    const defs = svg.append('defs');
    const gridPattern = defs
      .append('pattern')
      .attr('id', 'graph-grid')
      .attr('width', 32)
      .attr('height', 32)
      .attr('patternUnits', 'userSpaceOnUse');
    gridPattern.append('path').attr('d', 'M 32 0 L 0 0 0 32').attr('fill', 'none').attr('stroke', 'var(--border)').attr('stroke-opacity', 0.35);

    gnodes.forEach((n) => {
      defs
        .append('marker')
        .attr('id', `arrow-${n.id}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 8)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', n.color)
        .attr('opacity', 0.85);
    });

    const canvas = svg.append('g').attr('class', 'graph-canvas');
    canvas.append('rect').attr('width', GRAPH_W).attr('height', GRAPH_H).attr('fill', 'url(#graph-grid)');

    const nodes = gnodes.map((d) => ({ ...d }));
    const links = glinks.map((d) => ({ ...d }));
    const maxAmt = d3.max(links, (d) => d.amt);
    const linkW = d3.scaleSqrt().domain([0, maxAmt]).range([1.2, 5.5]);

    nodes.forEach((n, idx) => {
      const pos = NODE_POS[idx] || { x: GRAPH_W / 2, y: GRAPH_H / 2 };
      n.x = pos.x;
      n.y = pos.y;
      n.fx = n.x;
      n.fy = n.y;
    });

    const sim = d3
      .forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(160))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(GRAPH_W / 2, GRAPH_H / 2))
      .alpha(0.05)
      .alphaDecay(0.1);

    const edgeG = canvas.append('g').attr('class', 'edges');
    const edge = edgeG
      .selectAll('path')
      .data(links)
      .join('path')
      .attr('data-id', (d) => `${d.source.id || d.source}-${d.target.id || d.target}`)
      .attr('fill', 'none')
      .attr('stroke', (d) => {
        const tn = gnodes.find((n) => n.id === (d.target.id || d.target));
        return tn ? tn.color : '#64748b';
      })
      .attr('stroke-width', (d) => linkW(d.amt))
      .attr('stroke-opacity', 0.55)
      .attr('marker-end', (d) => `url(#arrow-${d.target.id || d.target})`)
      .style('cursor', 'pointer')
      .on('mouseenter', function (ev, d) {
        d3.select(this).attr('stroke-opacity', 1).attr('stroke-width', linkW(d.amt) + 1.5);
        const rect = wrapRef.current.getBoundingClientRect();
        setTip({ kind: 'edge', data: d, x: ev.clientX - rect.left, y: ev.clientY - rect.top });
      })
      .on('mousemove', function (ev, d) {
        const rect = wrapRef.current.getBoundingClientRect();
        setTip({ kind: 'edge', data: d, x: ev.clientX - rect.left, y: ev.clientY - rect.top });
      })
      .on('mouseleave', function (ev, d) {
        d3.select(this).attr('stroke-opacity', 0.55).attr('stroke-width', linkW(d.amt));
        setTip(null);
      });

    const particlesG = canvas.append('g').attr('class', 'particles');
    const particles = [];
    links.forEach((l, i) => {
      const tn = gnodes.find((n) => n.id === (l.target.id || l.target));
      const p = particlesG
        .append('circle')
        .attr('r', 2.5)
        .attr('fill', tn ? tn.color : '#64748b')
        .attr('opacity', 0.8);
      particles.push({ circle: p, link: l, offset: i * 0.2 });
    });

    const nodeG = canvas.append('g').attr('class', 'nodes');
    const nodeSel = nodeG
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('data-id', (d) => d.id)
      .style('cursor', 'pointer')
      .on('click', (ev, d) => onNodeClick && onNodeClick(d))
      .on('mouseenter', function (ev, d) {
        const rect = wrapRef.current.getBoundingClientRect();
        setTip({ kind: 'node', data: d, x: ev.clientX - rect.left, y: ev.clientY - rect.top });
        d3.select(this).select('circle.body').attr('stroke-width', 4);
      })
      .on('mousemove', function (ev, d) {
        const rect = wrapRef.current.getBoundingClientRect();
        setTip({ kind: 'node', data: d, x: ev.clientX - rect.left, y: ev.clientY - rect.top });
      })
      .on('mouseleave', function (ev, d) {
        setTip(null);
        d3.select(this).select('circle.body').attr('stroke-width', d.role === 'primary' ? 2.5 : 1.5);
      });

    nodeSel.append('circle').attr('class', 'halo').attr('r', (d) => d.size + 8).attr('fill', (d) => d.color).attr('opacity', 0.08);
    nodeSel
      .append('circle')
      .attr('class', 'body')
      .attr('r', (d) => d.size)
      .attr('fill', (d) => d.color)
      .attr('fill-opacity', 0.18)
      .attr('stroke', (d) => d.color)
      .attr('stroke-width', (d) => (d.role === 'primary' ? 2.5 : 1.5));
    nodeSel
      .filter((d) => d.role === 'primary')
      .append('circle')
      .attr('class', 'primary-pulse')
      .attr('r', (d) => d.size)
      .attr('fill', 'none')
      .attr('stroke', (d) => d.color)
      .attr('stroke-width', 2)
      .attr('opacity', 0.6)
      .append('animate')
      .attr('attributeName', 'r')
      .attr('from', (d) => d.size)
      .attr('to', (d) => d.size + 14)
      .attr('dur', '1.6s')
      .attr('repeatCount', 'indefinite');
    nodeSel
      .filter((d) => d.role === 'primary')
      .select('.primary-pulse')
      .append('animate')
      .attr('attributeName', 'opacity')
      .attr('from', 0.6)
      .attr('to', 0)
      .attr('dur', '1.6s')
      .attr('repeatCount', 'indefinite');
    nodeSel
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 3)
      .attr('font-family', 'JetBrains Mono')
      .attr('font-size', (d) => (d.size > 30 ? 10 : 9))
      .attr('font-weight', 700)
      .attr('fill', (d) => d.color)
      .text((d) => d.label);
    nodeSel
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => d.size + 16)
      .attr('font-family', 'JetBrains Mono')
      .attr('font-size', 10)
      .attr('fill', 'var(--text-dim)')
      .text((d) => d.id);

    sim.on('tick', () => {
      edge.attr('d', (d) => {
        const sx = d.source.x;
        const sy = d.source.y;
        const tx = d.target.x;
        const ty = d.target.y;
        const dx = tx - sx;
        const dy = ty - sy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const tSize = d.target.size || 24;
        const sSize = d.source.size || 24;
        const ux = dx / dist;
        const uy = dy / dist;
        const x1 = sx + ux * sSize;
        const y1 = sy + uy * sSize;
        const x2 = tx - ux * (tSize + 6);
        const y2 = ty - uy * (tSize + 6);
        return `M${x1},${y1} L${x2},${y2}`;
      });
      nodeSel.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    let raf;
    const start = performance.now();
    const animate = (now) => {
      const elapsed = (now - start) / 1000;
      particles.forEach((p) => {
        const phase = ((elapsed / 2.5) + p.offset) % 1;
        const sx = p.link.source.x;
        const sy = p.link.source.y;
        const tx = p.link.target.x;
        const ty = p.link.target.y;
        const dx = tx - sx;
        const dy = ty - sy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const ux = dx / dist;
        const uy = dy / dist;
        const startX = sx + ux * (p.link.source.size || 24);
        const startY = sy + uy * (p.link.source.size || 24);
        const endX = tx - ux * ((p.link.target.size || 24) + 6);
        const endY = ty - uy * ((p.link.target.size || 24) + 6);
        const x = startX + (endX - startX) * phase;
        const y = startY + (endY - startY) * phase;
        p.circle.attr('cx', x).attr('cy', y).attr('opacity', phase < 0.1 || phase > 0.9 ? 0.2 : 0.85);
      });
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(raf);
      sim.stop();
    };
  }, [onNodeClick, graph]);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll('g.nodes g circle.body').attr('stroke-width', function () {
      const id = d3.select(this.parentNode).attr('data-id');
      return id === primaryId ? 2.5 : 1.5;
    });
    svg.selectAll('g.edges path').attr('stroke-opacity', 0.55);
    if (highlight) {
      if (highlight.type === 'node') {
        svg
          .selectAll('g.nodes g')
          .filter(function () {
            return d3.select(this).attr('data-id') === highlight.id;
          })
          .select('circle.body')
          .attr('stroke-width', 4);
      } else if (highlight.type === 'edge') {
        const want = `${highlight.from}-${highlight.to}`;
        svg
          .selectAll('g.edges path')
          .filter(function () {
            return d3.select(this).attr('data-id') === want;
          })
          .attr('stroke-opacity', 1)
          .attr('stroke-width', 5.5);
      }
    }
    if (selectedEdge && primaryId) {
      const want = `${primaryId}-${selectedEdge}`;
      svg
        .selectAll('g.edges path')
        .filter(function () {
          return d3.select(this).attr('data-id') === want;
        })
        .attr('stroke-opacity', 1)
        .attr('stroke-width', 6);
    }
  }, [highlight, selectedEdge, graph, primaryId]);

  useEffect(() => {
    if (!ref.current || !glinks.length) return;
    const svg = d3.select(ref.current);
    const currentT = T_MIN + playhead * T_SPAN;
    const playing = isPlaying || playhead > 0.001;
    glinks.forEach((link) => {
      const lt = tToSec(link.t);
      const arrived = lt + 0.5 <= currentT;
      const key = `${link.source}-${link.target}`;
      const path = svg.selectAll('g.edges path').filter(function () {
        return d3.select(this).attr('data-id') === key;
      });
      if (!playing) path.attr('stroke-opacity', 0.55).attr('stroke-dasharray', null);
      else if (arrived) path.attr('stroke-opacity', 0.85).attr('stroke-dasharray', null);
      else path.attr('stroke-opacity', 0.12).attr('stroke-dasharray', '2 3');
    });
    gnodes.forEach((node) => {
      const allLinks = [...glinks.filter((l) => l.target === node.id), ...glinks.filter((l) => l.source === node.id)];
      const everyReached = allLinks.some((l) => tToSec(l.t) <= currentT);
      const justNow = allLinks.some((l) => Math.abs(tToSec(l.t) - currentT) < 1.5);
      const g = svg.selectAll('g.nodes g').filter(function () {
        return d3.select(this).attr('data-id') === node.id;
      });
      if (!playing) g.select('circle.body').attr('fill-opacity', 0.18);
      else if (justNow) g.select('circle.body').attr('fill-opacity', 0.55);
      else if (everyReached || node.role === 'victim') g.select('circle.body').attr('fill-opacity', 0.28);
      else g.select('circle.body').attr('fill-opacity', 0.08);
    });
  }, [playhead, isPlaying, graph]);

  return (
    <div className="graph-wrap" ref={wrapRef}>
      <TransformWrapper
        wrapperClass="graph-pan-zoom-root"
        initialScale={1}
        minScale={0.35}
        maxScale={2.75}
        centerOnInit
        limitToBounds={false}
        smooth={false}
        wheel={{ step: 0.06 }}
        pinch={{ step: 5 }}
        panning={{ velocityDisabled: true, excluded: ['graph-no-pan'] }}
        doubleClick={{ mode: 'reset' }}
      >
        {({ zoomIn, zoomOut, resetTransform }) => (
          <>
            <div className="graph-zoom-controls graph-no-pan">
              <Button variant="outline" size="icon-xs" onClick={() => zoomIn()} aria-label="Zoom in" title="Zoom in">
                <ZoomIn />
              </Button>
              <Button variant="outline" size="icon-xs" onClick={() => zoomOut()} aria-label="Zoom out" title="Zoom out">
                <ZoomOut />
              </Button>
              <Button variant="outline" size="icon-xs" onClick={() => resetTransform()} aria-label="Reset view" title="Reset view">
                <RotateCcw />
              </Button>
            </div>
            <TransformComponent wrapperClass="graph-transform-wrapper" contentClass="graph-transform-content">
              <svg id="graph-svg" ref={ref} width={GRAPH_W} height={GRAPH_H} />
            </TransformComponent>
          </>
        )}
      </TransformWrapper>

      <div className="graph-hint graph-no-pan">Scroll to zoom · Drag to pan · Double-click to reset</div>

      <div className="graph-legend graph-no-pan">
        <div className="lg-title">Node Types</div>
        <div className="lg-row"><span className="lg-dot" style={{ background: '#ef4444' }}></span>Victim</div>
        <div className="lg-row"><span className="lg-dot" style={{ background: '#f59e0b' }}></span>Mule / Relay</div>
        <div className="lg-row"><span className="lg-dot" style={{ background: '#8b5cf6' }}></span>Cash-out</div>
        <div className="lg-row"><span className="lg-dot" style={{ background: '#94a3b8' }}></span>Linked</div>
      </div>

      {tip && tip.kind === 'node' && (
        <div className="graph-tooltip graph-no-pan" style={{ left: Math.min(tip.x + 14, (wrapRef.current?.clientWidth || 0) - 200), top: Math.max(tip.y - 90, 10) }}>
          <div style={{ fontFamily: 'JetBrains Mono', fontWeight: 600, color: tip.data.color, fontSize: 12, marginBottom: 4 }}>{tip.data.id}</div>
          <div className="gt-row"><span className="k">Role</span><span className="v">{tip.data.label}</span></div>
          <div className="gt-row"><span className="k">Type</span><span className="v">{tip.data.type}</span></div>
          <div className="gt-row"><span className="k">Balance</span><span className="v">{tip.data.balance}</span></div>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 5, paddingTop: 5, borderTop: '1px solid var(--border)' }}>{tip.data.note}</div>
        </div>
      )}
      {tip && tip.kind === 'edge' && (
        <div className="graph-tooltip graph-no-pan" style={{ left: Math.min(tip.x + 14, (wrapRef.current?.clientWidth || 0) - 200), top: Math.max(tip.y - 70, 10) }}>
          <div className="gt-row"><span className="k">Amount</span><span className="v" style={{ color: '#f59e0b', fontWeight: 600 }}>{fmtINR(tip.data.amt)}</span></div>
          <div className="gt-row"><span className="k">Time</span><span className="v">{tip.data.t}</span></div>
          <div className="gt-row"><span className="k">Channel</span><span className="v">{tip.data.channel}</span></div>
          <div className="gt-row"><span className="k">From</span><span className="v">{tip.data.source.id || tip.data.source}</span></div>
          <div className="gt-row"><span className="k">To</span><span className="v">{tip.data.target.id || tip.data.target}</span></div>
        </div>
      )}
    </div>
  );
}
