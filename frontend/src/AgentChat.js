import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Sparkles, Camera, MapPin, Clock, User, Lock, RotateCcw } from 'lucide-react';

// ─── Conversation state ───────────────────────────────────────────────────────
// The chat lives in FindoraApp (via useAgentChat), not in the tab, so switching
// tabs keeps the conversation and an answer that arrives meanwhile isn't lost.
// It is also saved to sessionStorage, per user, so a page refresh keeps it.

const STORE_PREFIX = 'findora-chat:';
const MAX_STORED = 40;
const storeKey = (userId) => STORE_PREFIX + (userId || 'guest');

const greetingFor = (userId) => ({
  role: 'assistant',
  local: true,
  content: userId
    ? "Hi! I'm Findora Assistant. Tell me what you lost or found and I'll search the reports, show you photos of possible matches and help you file a report."
    : "Hi! I'm Findora Assistant. You're in **demo mode**, so I can tell you what Findora is and how it works. **Sign in** to let me search reports, show item photos and check your matches.",
});

const loadChat = (userId) => {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storeKey(userId)) || 'null');
    if (Array.isArray(saved) && saved.length) return saved;
  } catch {}
  return [greetingFor(userId)];
};

export function useAgentChat(apiBase, userId) {
  const [chat, setChat] = useState(() => ({ owner: userId, messages: loadChat(userId) }));
  const [busy, setBusy] = useState(false);
  const chatRef = useRef(chat);
  chatRef.current = chat;

  // A different user (sign in / sign out) gets their own conversation
  useEffect(() => {
    if (chatRef.current.owner === userId) return;
    setChat({ owner: userId, messages: loadChat(userId) });
    setBusy(false);
    try {
      Object.keys(sessionStorage)
        .filter((k) => k.startsWith(STORE_PREFIX) && k !== storeKey(userId))
        .forEach((k) => sessionStorage.removeItem(k));
    } catch {}
  }, [userId]);

  useEffect(() => {
    try {
      sessionStorage.setItem(storeKey(chat.owner), JSON.stringify(chat.messages.slice(-MAX_STORED)));
    } catch {}
  }, [chat]);

  const send = useCallback(async (text) => {
    const content = (text || '').trim();
    if (!content || busy) return;
    // a reply for someone who has since signed out is dropped
    const append = (owner, message) =>
      setChat((c) => (c.owner === owner ? { ...c, messages: [...c.messages, message] } : c));
    const owner = chatRef.current.owner;
    const history = [...chatRef.current.messages, { role: 'user', content }];
    append(owner, { role: 'user', content });
    setBusy(true);

    try {
      const res = await fetch(`${apiBase}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: owner,
          // UI-only messages (greeting, errors) are not sent to the model
          messages: history.filter((m) => !m.local && !m.error).map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      append(owner, {
        role: 'assistant',
        content: data.reply,
        steps: data.steps || [],
        actions: data.actions || [],
        items: data.items || [],
      });
    } catch (e) {
      append(owner, { role: 'assistant', content: `Sorry, I couldn't answer that. ${e.message}`, error: true });
    } finally {
      setBusy(false);
    }
  }, [apiBase, busy]);

  const reset = useCallback(() => {
    setChat({ owner: chatRef.current.owner, messages: [greetingFor(chatRef.current.owner)] });
  }, []);

  return { messages: chat.messages, busy, send, reset };
}

// ─── Light formatting for the model's replies (**bold**, lists) ───────────────
// Builds React elements; no HTML is ever injected.

const INLINE_RE = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\s][^*]*\*)/g;

function renderInline(text, keyBase) {
  const out = [];
  let last = 0;
  let i = 0;
  let m;
  INLINE_RE.lastIndex = 0;
  while ((m = INLINE_RE.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    const key = `${keyBase}-${i++}`;
    if (t.startsWith('**') || t.startsWith('__')) out.push(<strong key={key} style={{ fontWeight: 600 }}>{t.slice(2, -2)}</strong>);
    else if (t.startsWith('`')) out.push(<span key={key} style={{ fontWeight: 600 }}>{t.slice(1, -1)}</span>);
    else out.push(<em key={key}>{t.slice(1, -1)}</em>);
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function RichText({ text }) {
  const blocks = [];
  let para = [];
  let list = null;
  const flushPara = () => { if (para.length) { blocks.push({ type: 'p', lines: para }); para = []; } };
  const flushList = () => { if (list) { blocks.push(list); list = null; } };

  String(text || '').replace(/\r/g, '').split('\n').forEach((raw) => {
    const line = raw.trim();
    let m;
    if (!line) { flushPara(); flushList(); return; }
    if (/^[|\s:-]+$/.test(line) && line.includes('-')) return;           // table divider row
    if ((m = line.match(/^[-*•]\s+(.*)$/))) {
      flushPara();
      if (!list || list.type !== 'ul') { flushList(); list = { type: 'ul', items: [] }; }
      list.items.push(m[1]);
      return;
    }
    if ((m = line.match(/^\d+[.)]\s+(.*)$/))) {
      flushPara();
      if (!list || list.type !== 'ol') { flushList(); list = { type: 'ol', items: [] }; }
      list.items.push(m[1]);
      return;
    }
    flushList();
    if ((m = line.match(/^#{1,6}\s+(.*)$/))) { flushPara(); blocks.push({ type: 'h', text: m[1] }); return; }
    if (line.startsWith('|')) {                                          // table row -> "a · b · c"
      para.push(line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()).filter(Boolean).join(' · '));
      return;
    }
    para.push(line);
  });
  flushPara();
  flushList();

  return (
    <div style={st.rich}>
      {blocks.map((b, i) => {
        if (b.type === 'h') return <p key={i} style={st.richHeading}>{renderInline(b.text, i)}</p>;
        if (b.type === 'p') {
          return (
            <p key={i} style={st.richPara}>
              {b.lines.map((l, j) => (
                <React.Fragment key={j}>{j > 0 && <br />}{renderInline(l, `${i}-${j}`)}</React.Fragment>
              ))}
            </p>
          );
        }
        const Tag = b.type === 'ol' ? 'ol' : 'ul';
        return (
          <Tag key={i} style={st.richList}>
            {b.items.map((it, j) => <li key={j} style={st.richItem}>{renderInline(it, `${i}-${j}`)}</li>)}
          </Tag>
        );
      })}
    </div>
  );
}

// ─── Item card (photo, type, place, date, reporter) ───────────────────────────

const safeImage = (url) => (typeof url === 'string' && /^https?:\/\//i.test(url) ? url : null);

const formatDate = (value) => {
  const d = new Date(value);
  return isNaN(d) ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

function ChatItemCard({ item }) {
  const [imgError, setImgError] = useState(false);
  const img = !imgError && safeImage(item.image_path);
  const isLost = item.item_type === 'lost';
  const pct = item.confidence_percent;

  return (
    <div style={st.itemCard}>
      <div style={st.itemImgWrap}>
        {img ? (
          <a href={img} target="_blank" rel="noopener noreferrer" title="Open photo">
            <img src={img} alt={item.title} style={st.itemImg} onError={() => setImgError(true)} loading="lazy" />
          </a>
        ) : (
          <div style={st.itemImgPlaceholder}><Camera size={22} color="#c2cfe0" strokeWidth={1} /></div>
        )}
      </div>
      <div style={st.itemBody}>
        <div style={st.badgeRow}>
          <span style={{ ...st.typeBadge, background: isLost ? '#1e3a5f' : '#1a4d33' }}>{isLost ? 'LOST' : 'FOUND'}</span>
          {typeof pct === 'number' && (
            <span style={{ ...st.pctBadge, ...(pct >= 80 ? st.pctHigh : st.pctMid) }}>{pct}% match</span>
          )}
          {item.status === 'matched' && <span style={st.matchedBadge}>✓ Matched</span>}
        </div>
        <p style={st.itemTitle}>{item.title}</p>
        {item.description && <p style={st.itemDesc}>{item.description}</p>}
        <div style={st.itemMeta}>
          {item.location && <span style={st.metaRow}><MapPin size={12} strokeWidth={1.5} color="#7a8eaa" /><span style={st.metaText}>{item.location}</span></span>}
          {item.created_at && <span style={st.metaRow}><Clock size={12} strokeWidth={1.5} color="#7a8eaa" />{formatDate(item.created_at)}</span>}
          {item.reported_by && <span style={st.metaRow}><User size={12} strokeWidth={1.5} color="#7a8eaa" />Reported by {item.reported_by}</span>}
        </div>
        {item.reward_amount > 0 && <div style={st.rewardBadge}>Reward: ${item.reward_amount}</div>}
      </div>
    </div>
  );
}

// ─── Chat UI ──────────────────────────────────────────────────────────────────

const STEP_LABELS = {
  search_items: 'Searched reports',
  get_my_items: 'Looked at your reports',
  get_item_matches: 'Checked matches',
  get_stats: 'Checked platform stats',
  draft_report: 'Drafted a report',
};

const SUGGESTIONS = [
  'I lost my black wallet near Gandhipuram bus stand',
  'I found a set of keys at the railway station',
  'Show my reports and their matches',
];

const DEMO_SUGGESTIONS = [
  'What is Findora?',
  'How does the AI matching work?',
  'How do I report a lost item?',
];

export default function AgentChat({ chat, demo, onSignIn, onPrefillReport }) {
  const { messages, busy, send, reset } = chat;
  const [input, setInput] = useState('');
  const listRef = useRef(null);
  const firstScroll = useRef(true);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: firstScroll.current ? 'auto' : 'smooth' });
    firstScroll.current = false;
  }, [messages, busy]);

  const onSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    send(input);
    setInput('');
  };

  const fresh = messages.length === 1;
  const suggestions = demo ? DEMO_SUGGESTIONS : SUGGESTIONS;

  return (
    <div style={st.page}>
      <style>{chatCss}</style>

      <div style={st.pageHeader}>
        <p style={st.eyebrow}>AI Assistant</p>
        <h2 style={st.pageTitle}>Ask Findora</h2>
        <p style={st.pageSub}>Describe what you lost or found in your own words. The assistant searches the reports, shows photos of possible matches and helps you file a report.</p>
      </div>

      {demo && (
        <div style={st.demoBanner}>
          <div style={st.demoIcon}><Lock size={16} color="#1e3a5f" strokeWidth={1.8} /></div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <p style={st.demoTitle}>You're in demo mode</p>
            <p style={st.demoText}>Sign in to search reports, see item photos, check your matches and draft reports. In demo mode the assistant can only explain how Findora works.</p>
          </div>
          <button type="button" style={st.demoBtn} onClick={onSignIn}>Sign in</button>
        </div>
      )}

      <div style={st.card}>
        <div style={st.header}>
          <div style={st.headerIcon}><Sparkles size={17} color="#ffffff" strokeWidth={1.8} /></div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={st.headerTitle}>Findora Assistant</div>
            <div style={st.headerSub}>{demo ? 'Demo mode · explains how Findora works' : 'Searches reports, checks your matches, drafts new reports'}</div>
          </div>
          {!fresh && (
            <button type="button" style={st.newChatBtn} onClick={reset} disabled={busy} title="Start a new conversation">
              <RotateCcw size={13} strokeWidth={1.8} /> New chat
            </button>
          )}
        </div>

        <div style={st.list} ref={listRef}>
          {messages.map((m, i) => {
            if (m.role === 'user') {
              return <div key={i} className="fa-msg" style={st.userBubble}>{m.content}</div>;
            }
            const drafts = (m.actions || []).filter((a) => a.type === 'prefill_report');
            return (
              <div key={i} className="fa-msg" style={st.botRow}>
                <div style={st.botAvatar}><Sparkles size={13} color="#ffffff" strokeWidth={1.8} /></div>
                <div style={st.botCol}>
                  <div style={m.error ? st.errorBubble : st.botBubble}>
                    {m.error ? m.content : <RichText text={m.content} />}
                    {drafts.map((a, j) => (
                      <button key={j} type="button" style={st.draftBtn} onClick={() => onPrefillReport(a.draft)}>
                        Open Report form with this draft
                      </button>
                    ))}
                  </div>
                  {m.items && m.items.length > 0 && (
                    <div style={st.cardGrid}>
                      {m.items.map((it) => <ChatItemCard key={it.item_id} item={it} />)}
                    </div>
                  )}
                  {m.steps && m.steps.length > 0 && (
                    <div style={st.stepRow}>
                      {[...new Set(m.steps.map((s) => s.tool))].map((t) => (
                        <span key={t} style={st.step}>{STEP_LABELS[t] || t}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {fresh && (
            <div style={st.chips}>
              {suggestions.map((s) => (
                <button key={s} type="button" style={st.chip} onClick={() => send(s)} disabled={busy}>{s}</button>
              ))}
            </div>
          )}

          {busy && (
            <div style={st.botRow}>
              <div style={st.botAvatar}><Sparkles size={13} color="#ffffff" strokeWidth={1.8} /></div>
              <div style={st.typingBubble} aria-label="Assistant is thinking">
                <span className="fa-dot" /><span className="fa-dot" /><span className="fa-dot" />
              </div>
            </div>
          )}
        </div>

        <form style={st.inputRow} onSubmit={onSubmit}>
          <input
            style={st.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={demo ? 'Ask how Findora works…' : 'Describe what you lost or found…'}
            aria-label="Message the Findora assistant"
            maxLength={500}
          />
          <button type="submit" style={{ ...st.sendBtn, opacity: busy || !input.trim() ? 0.5 : 1 }}
            disabled={busy || !input.trim()} aria-label="Send message">
            <Send size={17} />
          </button>
        </form>
      </div>
    </div>
  );
}

// ─── Styles (same palette and fonts as the rest of the app) ───────────────────

const chatCss = `
  .fa-msg { animation: faIn 0.22s ease both; }
  @keyframes faIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  .fa-dot { width: 6px; height: 6px; border-radius: 50%; background: #7a8eaa; display: inline-block; animation: faDot 1.2s infinite ease-in-out; }
  .fa-dot:nth-child(2) { animation-delay: 0.15s; }
  .fa-dot:nth-child(3) { animation-delay: 0.3s; }
  @keyframes faDot { 0%, 80%, 100% { opacity: 0.3; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }
`;

const st = {
  page: { paddingTop: 32 },
  pageHeader: { marginBottom: 20 },
  eyebrow: { fontSize: 10, fontWeight: 700, color: '#7a8eaa', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 },
  pageTitle: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 'clamp(22px, 5vw, 32px)', color: '#0f172a', marginTop: 4, lineHeight: 1.1 },
  pageSub: { fontSize: 13, color: '#5c718a', marginTop: 6, lineHeight: 1.65, maxWidth: 640 },

  demoBanner: { display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', background: '#ffffff', border: '1px solid #dde3ed', borderLeft: '3px solid #1e3a5f', borderRadius: 12, padding: '12px 14px', marginBottom: 14 },
  demoIcon: { width: 34, height: 34, borderRadius: 9, background: '#eef2f8', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  demoTitle: { fontSize: 13.5, fontWeight: 600, color: '#0f172a' },
  demoText: { fontSize: 12.5, color: '#5c718a', lineHeight: 1.55, marginTop: 2 },
  demoBtn: { padding: '9px 22px', background: '#1e3a5f', color: '#fff', borderRadius: 9, fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none', fontFamily: 'inherit' },

  card: { background: '#ffffff', border: '1px solid #dde3ed', borderRadius: 16, overflow: 'hidden', display: 'flex', flexDirection: 'column', height: 'min(680px, calc(100vh - 230px))', minHeight: 420 },
  header: { padding: '13px 16px', borderBottom: '1px solid #eef1f6', display: 'flex', alignItems: 'center', gap: 11 },
  headerIcon: { width: 32, height: 32, borderRadius: 9, background: '#1e3a5f', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  headerTitle: { fontWeight: 600, fontSize: 14.5, color: '#0f172a' },
  headerSub: { fontSize: 12, color: '#7a8eaa', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  newChatBtn: { display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 500, color: '#2d4460', background: '#eef1f7', border: '1px solid #dde3ed', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', fontFamily: 'inherit', flexShrink: 0 },

  list: { flex: 1, overflowY: 'auto', padding: '18px 16px', display: 'flex', flexDirection: 'column', gap: 14, background: '#f8fafc' },
  userBubble: { alignSelf: 'flex-end', maxWidth: '78%', background: '#1e3a5f', color: '#ffffff', padding: '10px 14px', borderRadius: '14px 14px 4px 14px', fontSize: 14, lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word' },
  botRow: { display: 'flex', gap: 9, alignItems: 'flex-start', maxWidth: '100%' },
  botAvatar: { width: 26, height: 26, borderRadius: 8, background: '#1e3a5f', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2 },
  botCol: { display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0, flex: 1, maxWidth: 'calc(100% - 35px)' },
  botBubble: { alignSelf: 'flex-start', maxWidth: '88%', background: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', padding: '10px 14px', borderRadius: '4px 14px 14px 14px', fontSize: 14, lineHeight: 1.55, wordBreak: 'break-word' },
  errorBubble: { alignSelf: 'flex-start', maxWidth: '88%', background: '#fef2f2', color: '#7f1d1d', border: '1px solid #fecaca', padding: '10px 14px', borderRadius: '4px 14px 14px 14px', fontSize: 14, lineHeight: 1.55 },
  typingBubble: { display: 'flex', gap: 5, alignItems: 'center', background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '4px 14px 14px 14px', padding: '13px 14px' },

  rich: { display: 'flex', flexDirection: 'column', gap: 8 },
  richPara: { margin: 0 },
  richHeading: { margin: 0, fontWeight: 600 },
  richList: { margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 },
  richItem: { paddingLeft: 2 },

  cardGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: 10 },
  itemCard: { display: 'flex', gap: 12, background: '#ffffff', border: '1px solid #dde3ed', borderRadius: 13, padding: 10, minWidth: 0 },
  itemImgWrap: { width: 92, height: 92, borderRadius: 9, overflow: 'hidden', background: '#eef1f7', flexShrink: 0 },
  itemImg: { width: '100%', height: '100%', objectFit: 'cover', display: 'block' },
  itemImgPlaceholder: { width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  itemBody: { flex: 1, minWidth: 0 },
  badgeRow: { display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 5 },
  typeBadge: { fontSize: 9.5, fontWeight: 700, letterSpacing: '0.08em', padding: '2px 7px', borderRadius: 5, color: '#ffffff' },
  pctBadge: { fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5, border: '1px solid' },
  pctHigh: { color: '#1a4d33', background: '#e8f2ec', borderColor: '#b8ddc8' },
  pctMid: { color: '#1e3a5f', background: '#eef2f8', borderColor: '#cfd8e6' },
  matchedBadge: { fontSize: 10, fontWeight: 700, color: '#1a4d33', background: '#e8f2ec', border: '1px solid #b8ddc8', borderRadius: 5, padding: '2px 7px' },
  itemTitle: { fontSize: 13.5, fontWeight: 600, color: '#0f172a', marginBottom: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  itemDesc: { fontSize: 12, color: '#5c718a', lineHeight: 1.45, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', marginBottom: 6 },
  itemMeta: { display: 'flex', flexDirection: 'column', gap: 3 },
  metaRow: { display: 'flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: '#7a8eaa', minWidth: 0 },
  metaText: { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  rewardBadge: { marginTop: 7, fontSize: 11.5, color: '#1a4d33', background: '#e8f2ec', border: '1px solid #a7d4b8', borderRadius: 6, padding: '3px 9px', fontWeight: 600, display: 'inline-block' },

  stepRow: { display: 'flex', flexWrap: 'wrap', gap: 6 },
  step: { fontSize: 11, color: '#4b5d78', background: '#eef2f8', borderRadius: 999, padding: '3px 9px' },
  draftBtn: { display: 'block', marginTop: 10, background: '#1e3a5f', color: '#ffffff', border: 'none', borderRadius: 10, padding: '9px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' },
  chips: { display: 'flex', flexWrap: 'wrap', gap: 8, paddingLeft: 35 },
  chip: { background: '#ffffff', border: '1px solid #cfd8e6', color: '#1e3a5f', borderRadius: 999, padding: '7px 12px', fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' },

  inputRow: { display: 'flex', gap: 10, padding: 12, borderTop: '1px solid #eef1f6', background: '#ffffff' },
  input: { flex: 1, minWidth: 0, border: '1px solid #cfd8e6', borderRadius: 10, padding: '11px 14px', fontSize: 14, outline: 'none', fontFamily: 'inherit' },
  sendBtn: { background: '#1e3a5f', color: '#ffffff', border: 'none', borderRadius: 10, width: 46, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' },
};
