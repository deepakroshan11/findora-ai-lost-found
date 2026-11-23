import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';

const GREETING =
  "Hi! I'm Findora Assistant. Tell me what you lost or found and I'll search for matches, " +
  'or ask me about your reports.';

const SUGGESTIONS = [
  'I lost my black wallet near Gandhipuram bus stand',
  'I found a set of keys at the railway station',
  'Show my reports and their matches',
];

// What the agent did, shown as small chips under its answer
const STEP_LABELS = {
  search_items: 'Searched reports',
  get_my_items: 'Looked at your reports',
  get_item_matches: 'Checked matches',
  get_stats: 'Checked platform stats',
  draft_report: 'Drafted a report',
};

const styles = {
  card: { background: '#fff', border: '1px solid #dde3ed', borderRadius: 16, overflow: 'hidden', display: 'flex', flexDirection: 'column', height: 'min(640px, 75vh)' },
  header: { padding: '14px 18px', borderBottom: '1px solid #eef1f6', display: 'flex', alignItems: 'center', gap: 10 },
  headerTitle: { fontWeight: 600, fontSize: 15, color: '#0f172a' },
  headerSub: { fontSize: 12, color: '#7a8eaa' },
  list: { flex: 1, overflowY: 'auto', padding: 18, display: 'flex', flexDirection: 'column', gap: 12, background: '#f8fafc' },
  userBubble: { alignSelf: 'flex-end', maxWidth: '80%', background: '#1e3a5f', color: '#fff', padding: '10px 14px', borderRadius: '14px 14px 4px 14px', fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap' },
  botBubble: { alignSelf: 'flex-start', maxWidth: '85%', background: '#fff', color: '#0f172a', border: '1px solid #e2e8f0', padding: '10px 14px', borderRadius: '14px 14px 14px 4px', fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap' },
  errorBubble: { alignSelf: 'flex-start', maxWidth: '85%', background: '#fef2f2', color: '#7f1d1d', border: '1px solid #fecaca', padding: '10px 14px', borderRadius: '14px 14px 14px 4px', fontSize: 14, lineHeight: 1.5 },
  stepRow: { display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 },
  step: { fontSize: 11, color: '#4b5d78', background: '#eef2f8', borderRadius: 999, padding: '3px 9px' },
  draftBtn: { marginTop: 10, background: '#1e3a5f', color: '#fff', border: 'none', borderRadius: 10, padding: '9px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  chips: { display: 'flex', flexWrap: 'wrap', gap: 8 },
  chip: { background: '#fff', border: '1px solid #cfd8e6', color: '#1e3a5f', borderRadius: 999, padding: '7px 12px', fontSize: 13, cursor: 'pointer' },
  typing: { alignSelf: 'flex-start', color: '#7a8eaa', fontSize: 13, padding: '4px 2px' },
  note: { padding: '8px 18px', fontSize: 12, color: '#7a8eaa', background: '#fff', borderTop: '1px solid #eef1f6' },
  inputRow: { display: 'flex', gap: 10, padding: 14, borderTop: '1px solid #eef1f6', background: '#fff' },
  input: { flex: 1, border: '1px solid #cfd8e6', borderRadius: 10, padding: '11px 14px', fontSize: 14, outline: 'none', fontFamily: 'inherit' },
  sendBtn: { background: '#1e3a5f', color: '#fff', border: 'none', borderRadius: 10, width: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' },
};

export default function AgentChat({ apiBase, userId, onPrefillReport }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: GREETING, local: true }]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (endRef.current && endRef.current.scrollIntoView) {
      endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages, busy]);

  const send = async (text) => {
    const content = text.trim();
    if (!content || busy) return;

    const next = [...messages, { role: 'user', content }];
    setMessages(next);
    setInput('');
    setBusy(true);

    try {
      const res = await fetch(`${apiBase}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          // the local greeting is UI-only, so it is not sent to the model
          messages: next.filter((m) => !m.local).map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: data.reply, steps: data.steps || [], actions: data.actions || [] },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `Sorry, I couldn't answer that. ${e.message}`, error: true }]);
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    send(input);
  };

  const showSuggestions = messages.length === 1;

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <Sparkles size={20} color="#1e3a5f" />
        <div>
          <div style={styles.headerTitle}>Findora Assistant</div>
          <div style={styles.headerSub}>Searches reports, checks your matches, drafts new reports</div>
        </div>
      </div>

      <div style={styles.list}>
        {messages.map((m, i) => {
          if (m.role === 'user') return <div key={i} style={styles.userBubble}>{m.content}</div>;
          return (
            <div key={i} style={m.error ? styles.errorBubble : styles.botBubble}>
              {m.content}
              {m.steps && m.steps.length > 0 && (
                <div style={styles.stepRow}>
                  {m.steps.map((s, j) => (
                    <span key={j} style={styles.step}>{STEP_LABELS[s.tool] || s.tool}</span>
                  ))}
                </div>
              )}
              {(m.actions || []).filter((a) => a.type === 'prefill_report').map((a, j) => (
                <button key={j} type="button" style={styles.draftBtn} onClick={() => onPrefillReport(a.draft)}>
                  Open Report form with this draft
                </button>
              ))}
            </div>
          );
        })}

        {showSuggestions && (
          <div style={styles.chips}>
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" style={styles.chip} onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}
        {busy && <div style={styles.typing}>Assistant is thinking…</div>}
        <div ref={endRef} />
      </div>

      {!userId && (
        <div style={styles.note}>Sign in to let the assistant show your own reports and matches.</div>
      )}

      <form style={styles.inputRow} onSubmit={onSubmit}>
        <input
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe what you lost or found…"
          aria-label="Message the Findora assistant"
          maxLength={500}
          disabled={busy}
        />
        <button type="submit" style={{ ...styles.sendBtn, opacity: busy || !input.trim() ? 0.5 : 1 }}
          disabled={busy || !input.trim()} aria-label="Send message">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
