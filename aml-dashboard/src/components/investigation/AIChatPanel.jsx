import { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api.js';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

const SUGGESTIONS = [
  'What triggered this alert?',
  'Explain the device fingerprint match',
  'Show pass-through ratio breakdown',
  'Which related cases are linked?',
  'Summarise outbound transactions',
];

const INITIAL_MESSAGES = [
  {
    id: 0,
    role: 'assistant',
    time: null,
    body: 'I have context on this case — account profile, risk signals, transaction graph, and linked investigations. Ask me anything about the evidence.',
  },
];

export default function AIChatPanel({ caseObj, activeAccount, selectedEdge }) {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [streamingId, setStreamingId] = useState(null);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const busy = thinking || streamingId !== null;

  // load persisted chat history for this case (survives restart/reopen)
  useEffect(() => {
    let cancelled = false;
    const id = caseObj?.id;
    if (!id) return;
    api.copilotHistory(id)
      .then((history) => {
        if (cancelled || !history?.length) return;
        setMessages([
          ...INITIAL_MESSAGES,
          ...history.map((m, i) => ({ id: `h${i}`, role: m.role, time: m.time, body: m.body })),
        ]);
      })
      .catch(() => { /* no history / backend down — keep intro */ });
    return () => { cancelled = true; };
  }, [caseObj?.id]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, thinking, streamingId]);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    const ts = new Date().toTimeString().slice(0, 8);
    const asstId = Date.now() + 1;
    setMessages((m) => [...m, { id: Date.now(), role: 'user', time: ts, body: trimmed }]);
    setInput('');
    setThinking(true);          // show typing dots until the first token arrives

    let started = false;
    try {
      await api.copilotStream(caseObj?.id, trimmed, (token) => {
        if (!started) {
          started = true;
          setThinking(false);
          setStreamingId(asstId);
          setMessages((m) => [
            ...m,
            { id: asstId, role: 'assistant', time: new Date().toTimeString().slice(0, 8), body: token },
          ]);
        } else {
          setMessages((m) => m.map((msg) => (msg.id === asstId ? { ...msg, body: msg.body + token } : msg)));
        }
      });
    } catch (err) {
      const msg = String(err).includes('503')
        ? 'Copilot is unavailable — set OPENAI_API_KEY in backend/.env and restart the backend.'
        : 'Could not reach the copilot service. Is the backend running?';
      setMessages((m) => [
        ...m.filter((msg) => msg.id !== asstId),
        { id: asstId, role: 'assistant', time: new Date().toTimeString().slice(0, 8), body: msg, error: true },
      ]);
    } finally {
      setThinking(false);
      setStreamingId(null);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const contextLabel = selectedEdge
    ? `Focused: ${selectedEdge}`
    : `${caseObj?.account || activeAccount?.account} · ${caseObj?.id || ''}`;

  return (
    <div className="chat-content">
      <div className="chat-context-bar">
        <span className="chat-context-dot"></span>
        <span className="chat-context-label">{contextLabel}</span>
      </div>

      <div className="chat-list scroll" ref={listRef}>
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-msg ${msg.role}`}>
            <div className="chat-msg-head">
              <div className={`chat-avatar ${msg.role}`}>{msg.role === 'assistant' ? 'AI' : 'You'}</div>
              <span className="chat-msg-role">{msg.role === 'assistant' ? 'Case Copilot' : 'You'}</span>
              {msg.time && <span className="chat-msg-time">{msg.time}</span>}
            </div>
            <div className="chat-msg-body" style={msg.error ? { color: 'var(--danger, #ef4444)' } : undefined}>
              {msg.body.split('\n').map((line, i, arr) => (
                <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
              ))}
              {msg.id === streamingId && <span className="chat-cursor" />}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="chat-msg assistant">
            <div className="chat-msg-head">
              <div className="chat-avatar assistant">AI</div>
              <span className="chat-msg-role">Case Copilot</span>
            </div>
            <div className="chat-typing"><span></span><span></span><span></span></div>
          </div>
        )}
      </div>

      {messages.length <= 1 && !thinking && (
        <div className="chat-suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className="chat-suggestion" onClick={() => sendMessage(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-wrap">
        <Textarea
          ref={inputRef}
          className="chat-input min-h-[52px] resize-none text-[11px]"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about this case…"
          disabled={busy}
        />
        <div className="chat-input-row">
          <span className="chat-meta">Case-grounded · OpenAI · not audit-logged</span>
          <Button size="sm" className="text-[11px]" onClick={() => sendMessage(input)} disabled={!input.trim() || busy}>
            {streamingId ? 'Streaming…' : 'Ask'}
          </Button>
        </div>
      </div>
    </div>
  );
}
