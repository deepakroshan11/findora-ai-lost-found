import React, { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
import { Camera, MapPin, Search, Bell, Upload, X, Check, AlertCircle, TrendingUp, Clock, Sparkles, Shield, Zap, Activity, LogOut, User, ChevronDown } from 'lucide-react';
import { useAuth } from './AuthContext';
import SplashScreen from './SplashScreen';
import AuthPage from './AuthPage';

const DashboardPage = lazy(() => import('./DashboardPage'));

// ─── IMPORTANT: set REACT_APP_API_URL in Vercel environment variables ─────────
// e.g. https://findora-ai-lost-found-1.onrender.com
const API_BASE = (process.env.REACT_APP_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const FieldError = ({ msg }) => msg ? (
  <p style={s.fieldError}><AlertCircle size={13} />{msg}</p>
) : null;

const Spinner = ({ size = 20, color = '#ffffff' }) => (
  <div style={{ width: size, height: size, border: `2px solid rgba(255,255,255,0.25)`, borderTopColor: color, borderRadius: '50%', animation: 'spin 0.75s linear infinite' }} />
);

// ─── Match Chime (Web Audio API) ──────────────────────────────────────────────
function playMatchChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const now = ctx.currentTime;
    // Note 1: C5
    const o1 = ctx.createOscillator();
    const g1 = ctx.createGain();
    o1.frequency.value = 523.25;
    o1.type = 'sine';
    g1.gain.setValueAtTime(0.25, now);
    g1.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
    o1.connect(g1).connect(ctx.destination);
    o1.start(now); o1.stop(now + 0.4);
    // Note 2: E5
    const o2 = ctx.createOscillator();
    const g2 = ctx.createGain();
    o2.frequency.value = 659.25;
    o2.type = 'sine';
    g2.gain.setValueAtTime(0.25, now + 0.12);
    g2.gain.exponentialRampToValueAtTime(0.001, now + 0.55);
    o2.connect(g2).connect(ctx.destination);
    o2.start(now + 0.12); o2.stop(now + 0.55);
    // Note 3: G5
    const o3 = ctx.createOscillator();
    const g3 = ctx.createGain();
    o3.frequency.value = 783.99;
    o3.type = 'sine';
    g3.gain.setValueAtTime(0.2, now + 0.24);
    g3.gain.exponentialRampToValueAtTime(0.001, now + 0.7);
    o3.connect(g3).connect(ctx.destination);
    o3.start(now + 0.24); o3.stop(now + 0.7);
  } catch (e) { /* AudioContext not available */ }
}

// ─── AI Agent Status Section ──────────────────────────────────────────────────
const AgentStatusSection = () => {
  const [scanPct, setScanPct] = useState(0);
  const steps = [
    { label: 'Keyword + semantic analysis', sub: 'Title, description, category overlap', done: true },
    { label: 'Computing confidence score', sub: '0–100% match confidence', done: true },
    { label: 'Scanning for matches...', sub: 'Comparing against all active items', done: false },
  ];

  useEffect(() => {
    const t1 = setInterval(() => setScanPct(p => p >= 100 ? 0 : p + 2), 60);
    return () => clearInterval(t1);
  }, []);

  return (
    <div style={s.agentSection}>
      <p style={s.sectionLabel}>AI Agent — Running</p>
      <div style={s.agentHeader}>
        <div style={s.agentDotWrap}><div style={s.agentDot} /></div>
        <div style={{ flex: 1 }}>
          <p style={s.agentTitle}>Autonomous matching agent active</p>
          <p style={s.agentSub}>Triggers on every submission · Notifies users via email when match ≥ 75%</p>
        </div>
        <span style={s.agentBadge}>Live</span>
      </div>
      <div style={s.agentEngines}>
        {[
          { label: 'Title Match', sub: 'Keyword overlap' },
          { label: 'Description', sub: 'Semantic match' },
          { label: 'Category', sub: 'Type bonus' },
        ].map((e, i) => (
          <div key={i} style={s.enginePill}>
            <p style={s.engineLabel}>{e.label}</p>
            <p style={s.engineSub}>{e.sub}</p>
          </div>
        ))}
      </div>
      <div style={s.agentSteps}>
        {steps.map((st, i) => (
          <div key={i} style={{ ...s.agentStep, background: st.done ? '#e8f2ec' : '#eef1f7', border: `1px solid ${st.done ? '#b8ddc8' : '#dde3ed'}` }}>
            <div style={{ ...s.agentStepIcon, background: st.done ? '#1a4d33' : '#1e3a5f', animation: !st.done ? 'pulse 1.4s ease-in-out infinite' : 'none' }}>
              {st.done ? <Check size={10} color="#fff" strokeWidth={2.5} /> : <Activity size={10} color="#fff" strokeWidth={2} />}
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ ...s.agentStepLabel, color: st.done ? '#1a4d33' : '#0f172a' }}>{st.label}</p>
              {!st.done && <div style={s.scanBarTrack}><div style={{ ...s.scanBarFill, width: `${scanPct}%` }} /></div>}
              {st.done && <p style={s.agentStepSub}>{st.sub}</p>}
            </div>
            <span style={{ fontSize: 10, color: st.done ? '#1a4d33' : '#7a8eaa', fontWeight: 600 }}>{st.done ? 'done' : 'active'}</span>
          </div>
        ))}
      </div>
      <div style={s.agentNotifyBar}>
        <div style={s.agentNotifyIcon}><Check size={13} color="#fff" strokeWidth={2.5} /></div>
        <div>
          <p style={s.agentNotifyTitle}>Match found → both users notified instantly</p>
          <p style={s.agentNotifySub}>Email sent automatically with contact details of the other party</p>
        </div>
      </div>
    </div>
  );
};

// ─── Home Tab ─────────────────────────────────────────────────────────────────
const HomeTab = ({ stats, activeCTA, setActiveCTA, setFormData, setActiveTab }) => (
  <div style={s.page}>
    <div style={s.hero}>
      <p style={s.heroEyebrow}>AI-Powered Platform</p>
      <h1 style={s.heroTitle}>Findora</h1>
      <p style={s.heroSub}>Reconnecting people with their belongings — intelligently.</p>
    </div>
    {stats && (
      <div style={s.statsGrid}>
        {[
          { label: 'Total', value: stats.total_items, icon: TrendingUp },
          { label: 'Lost', value: stats.lost_items, icon: Search },
          { label: 'Found', value: stats.found_items, icon: Camera },
          { label: 'Matched', value: stats.matched_items, icon: Check },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} style={s.statCard}>
            <Icon size={16} color="#7a8eaa" strokeWidth={1.5} />
            <span style={s.statValue}>{value}</span>
            <span style={s.statLabel}>{label}</span>
          </div>
        ))}
      </div>
    )}
    <div style={s.ctaGrid}>
      <button style={{ ...s.ctaCard, background: activeCTA === 'lost' ? '#1e3a5f' : '#ffffff', borderColor: activeCTA === 'lost' ? '#1e3a5f' : '#c5d0e0' }}
        onClick={() => { setActiveCTA('lost'); setFormData(f => ({ ...f, itemType: 'lost' })); setTimeout(() => setActiveTab('report'), 200); }}>
        <div style={{ ...s.ctaIconBox, background: activeCTA === 'lost' ? 'rgba(255,255,255,0.18)' : '#eef1f7' }}>
          <Search size={18} color={activeCTA === 'lost' ? '#ffffff' : '#1e3a5f'} strokeWidth={1.8} />
        </div>
        <div>
          <p style={{ ...s.ctaTitle, color: activeCTA === 'lost' ? '#ffffff' : '#0f172a' }}>Lost Something?</p>
          <p style={{ ...s.ctaSub, color: activeCTA === 'lost' ? 'rgba(255,255,255,0.72)' : '#5c718a' }}>Report &amp; let AI search for you</p>
        </div>
      </button>
      <button style={{ ...s.ctaCard, background: activeCTA === 'found' ? '#1a4d33' : '#ffffff', borderColor: activeCTA === 'found' ? '#1a4d33' : '#c5d0e0' }}
        onClick={() => { setActiveCTA('found'); setFormData(f => ({ ...f, itemType: 'found' })); setTimeout(() => setActiveTab('report'), 200); }}>
        <div style={{ ...s.ctaIconBox, background: activeCTA === 'found' ? 'rgba(255,255,255,0.18)' : '#e8f2ec' }}>
          <Camera size={18} color={activeCTA === 'found' ? '#ffffff' : '#1a4d33'} strokeWidth={1.8} />
        </div>
        <div>
          <p style={{ ...s.ctaTitle, color: activeCTA === 'found' ? '#ffffff' : '#0f172a' }}>Found Something?</p>
          <p style={{ ...s.ctaSub, color: activeCTA === 'found' ? 'rgba(255,255,255,0.72)' : '#5c718a' }}>Help return it to its owner</p>
        </div>
      </button>
    </div>
    <div style={s.howSection}>
      <p style={s.sectionLabel}>How It Works</p>
      {[
        { step: '01', title: 'Upload & Describe', desc: 'Take a clear photo and describe your item with as much detail as possible.' },
        { step: '02', title: 'AI Analyzes', desc: 'Our system cross-references title keywords, description, and category intelligently.' },
        { step: '03', title: 'Get Matched', desc: 'Receive an email notification the moment a high-confidence match is found.' },
      ].map(({ step, title, desc }, idx, arr) => (
        <div key={step} style={{ ...s.howRow, ...(idx === arr.length - 1 ? { borderBottom: 'none', marginBottom: 0, paddingBottom: 0 } : {}) }}>
          <span style={s.howStep}>{step}</span>
          <div><p style={s.howTitle}>{title}</p><p style={s.howDesc}>{desc}</p></div>
        </div>
      ))}
    </div>
    <AgentStatusSection />
    <div style={s.badges}>
      {['AI-Powered Matching', 'Secure & Private', 'Fast Results'].map(b => (
        <span key={b} style={s.badge}>{b}</span>
      ))}
    </div>
  </div>
);

// ─── Report Tab ───────────────────────────────────────────────────────────────
const ReportTab = ({ formData, setFormData, formErrors, setFormErrors, previewUrl, setPreviewUrl, loading, handleSubmit, getLocation, showNotification }) => (
  <div style={s.page}>
    <div style={s.pageHeader}>
      <p style={s.heroEyebrow}>Submit a Report</p>
      <h2 style={s.pageTitle}>Report {formData.itemType === 'lost' ? 'Lost' : 'Found'} Item</h2>
      <p style={s.pageSub}>The more detail you provide, the better our AI can find a match.</p>
    </div>
    <div style={s.toggle}>
      {['lost', 'found'].map(t => (
        <button key={t} onClick={() => setFormData(f => ({ ...f, itemType: t }))}
          style={{ ...s.toggleBtn, background: formData.itemType === t ? (t === 'lost' ? '#1e3a5f' : '#1a4d33') : 'transparent', color: formData.itemType === t ? '#ffffff' : '#7a8eaa' }}>
          {t === 'lost' ? 'Lost Item' : 'Found Item'}
        </button>
      ))}
    </div>
    <div style={s.formStack}>
      <div style={s.formGroup}>
        <label style={s.label}>Photo <span style={s.req}>*</span></label>
        <div style={{ ...s.uploadZone, ...(formErrors.image ? s.uploadZoneError : {}) }}>
          {previewUrl ? (
            <div style={s.previewWrap}>
              <img src={previewUrl} alt="Preview" style={s.previewImg} />
              <button onClick={() => { setPreviewUrl(null); setFormData(f => ({ ...f, image: null })); }} style={s.removeBtn}><X size={14} /></button>
            </div>
          ) : (
            <label style={s.uploadLabel}>
              <Upload size={22} color="#9aafc4" strokeWidth={1.5} />
              <span style={s.uploadText}>Click to upload</span>
              <span style={s.uploadHint}>JPG, PNG, WEBP — max 10 MB</span>
              <input type="file" accept="image/*" onChange={e => {
                const file = e.target.files[0];
                if (!file) return;
                if (file.size > 10 * 1024 * 1024) { showNotification('Image too large — max 10 MB', 'error'); return; }
                setFormData(f => ({ ...f, image: file }));
                setFormErrors(fe => ({ ...fe, image: null }));
                const reader = new FileReader();
                reader.onloadend = () => setPreviewUrl(reader.result);
                reader.readAsDataURL(file);
              }} style={{ display: 'none' }} />
            </label>
          )}
        </div>
        <FieldError msg={formErrors.image} />
      </div>

      <div style={s.formGroup}>
        <label style={s.label}>Item Title <span style={s.req}>*</span></label>
        <input type="text" value={formData.title} placeholder="e.g. Black leather wallet"
          onChange={e => { setFormData(f => ({ ...f, title: e.target.value })); setFormErrors(fe => ({ ...fe, title: null })); }}
          style={{ ...s.input, ...(formErrors.title ? s.inputError : {}) }} />
        <FieldError msg={formErrors.title} />
      </div>

      <div style={s.formGroup}>
        <label style={s.label}>Category <span style={s.req}>*</span></label>
        <select value={formData.category} onChange={e => setFormData(f => ({ ...f, category: e.target.value }))} style={s.input}>
          {['wallet','phone','keys','bag','jewelry','documents','electronics','clothing','accessories','other'].map(c => (
            <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
          ))}
        </select>
      </div>

      <div style={s.formGroup}>
        <label style={s.label}>Description <span style={s.req}>*</span></label>
        <textarea value={formData.description} rows={4}
          placeholder="Describe color, size, brand, unique marks, where and when it was lost or found..."
          onChange={e => { setFormData(f => ({ ...f, description: e.target.value })); setFormErrors(fe => ({ ...fe, description: null })); }}
          style={{ ...s.input, ...s.textarea, ...(formErrors.description ? s.inputError : {}) }} />
        <div style={s.charRow}>
          <FieldError msg={formErrors.description} />
          <span style={s.charCount}>{formData.description.length} chars</span>
        </div>
      </div>

      <div style={s.formGroup}>
        <label style={s.label}>Location <span style={s.req}>*</span></label>
        <div style={s.locationRow}>
          <input type="text" value={formData.location} placeholder="e.g. Central Bus Station, Main Street"
            onChange={e => { setFormData(f => ({ ...f, location: e.target.value })); setFormErrors(fe => ({ ...fe, location: null })); }}
            style={{ ...s.input, flex: 1, ...(formErrors.location ? s.inputError : {}) }} />
          <button onClick={getLocation} disabled={loading} style={s.gpsBtn} title="Use GPS">
            <MapPin size={16} color="#ffffff" strokeWidth={1.5} />
          </button>
        </div>
        {formData.latitude && (
          <p style={s.gpsConfirm}><Check size={13} /> GPS: {formData.latitude.toFixed(4)}, {formData.longitude.toFixed(4)}</p>
        )}
        <FieldError msg={formErrors.location} />
      </div>

      <div style={s.contactSection}>
        <p style={s.contactSectionTitle}>Contact Information</p>
        <p style={s.contactSectionSub}>When a match is found, we'll send the other person your contact details so they can reach you directly.</p>
        <div style={{ ...s.formGroup, marginTop: 12 }}>
          <label style={s.label}>Email Address <span style={s.req}>*</span></label>
          <input type="email" value={formData.contactEmail} placeholder="yourname@email.com"
            onChange={e => { setFormData(f => ({ ...f, contactEmail: e.target.value })); setFormErrors(fe => ({ ...fe, contactEmail: null })); }}
            style={{ ...s.input, ...(formErrors.contactEmail ? s.inputError : {}) }} />
          <p style={s.contactHint}>You'll receive match alerts at this email</p>
          <FieldError msg={formErrors.contactEmail} />
        </div>
        <div style={{ ...s.formGroup, marginTop: 10 }}>
          <label style={s.label}>Mobile Number <span style={s.optional}>(optional)</span></label>
          <input type="tel" value={formData.contactPhone} placeholder="+91 98765 43210"
            onChange={e => setFormData(f => ({ ...f, contactPhone: e.target.value }))}
            style={s.input} />
          <p style={s.contactHint}>If provided, shown in the match email for faster communication</p>
        </div>
      </div>

      {formData.itemType === 'lost' && (
        <div style={s.formGroup}>
          <label style={s.label}>Reward Amount <span style={s.optional}>(optional)</span></label>
          <div style={s.rewardWrap}>
            <span style={s.currencySymbol}>$</span>
            <input type="number" value={formData.rewardAmount || ''} placeholder="0" min="0" step="0.01"
              onChange={e => setFormData(f => ({ ...f, rewardAmount: parseFloat(e.target.value) || 0 }))}
              style={{ ...s.input, paddingLeft: 36 }} />
          </div>
        </div>
      )}

      <button onClick={handleSubmit} disabled={loading}
        style={{ ...s.submitBtn, background: formData.itemType === 'lost' ? '#1e3a5f' : '#1a4d33', opacity: loading ? 0.65 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}>
        {loading ? <Spinner size={18} color="#fff" /> : `Submit ${formData.itemType === 'lost' ? 'Lost' : 'Found'} Report`}
      </button>
    </div>
  </div>
);

// ─── Browse Tab ───────────────────────────────────────────────────────────────
const BrowseTab = ({ items, loading, filterType, setFilterType, searchQuery, setSearchQuery, setActiveTab }) => {
  const filteredItems = items.filter(item => {
    const matchesType   = filterType === 'all' || item.item_type === filterType;
    const matchesSearch = !searchQuery || [item.title, item.description, item.location]
      .some(f => f?.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesType && matchesSearch;
  });

  return (
    <div style={s.page}>
      <div style={s.pageHeader}>
        <p style={s.heroEyebrow}>Database</p>
        <h2 style={s.pageTitle}>Browse Items</h2>
      </div>
      <div style={s.searchRow}>
        <div style={s.searchWrap}>
          <Search size={15} color="#9aafc4" style={s.searchIcon} strokeWidth={1.5} />
          <input type="text" placeholder="Search by title, description, location..."
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)} style={s.searchInput} />
        </div>
        <div style={s.filterRow}>
          {['all','lost','found'].map(t => (
            <button key={t} onClick={() => setFilterType(t)}
              style={{ ...s.filterBtn, background: filterType === t ? '#1e3a5f' : '#ffffff', color: filterType === t ? '#ffffff' : '#4a6080', borderColor: filterType === t ? '#1e3a5f' : '#dde3ed' }}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div style={s.loadingState}><Spinner size={28} color="#1e3a5f" /><span style={s.loadingText}>Loading items...</span></div>
      ) : filteredItems.length === 0 ? (
        <div style={s.emptyState}>
          <Search size={36} color="#c2cfe0" strokeWidth={1} />
          <p style={s.emptyTitle}>{searchQuery || filterType !== 'all' ? 'No matching items' : 'No items yet'}</p>
          <p style={s.emptyDesc}>{searchQuery || filterType !== 'all' ? 'Try adjusting your search or filters.' : 'Be the first to report an item.'}</p>
          {!searchQuery && filterType === 'all' && <button onClick={() => setActiveTab('report')} style={s.emptyBtn}>Report First Item</button>}
        </div>
      ) : (
        <>
          <p style={s.resultCount}>{filteredItems.length} {filteredItems.length === 1 ? 'item' : 'items'}</p>
          <div style={s.cardGrid}>
            {filteredItems.map(item => (
              <ItemCard key={item.item_id} item={item} />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

// ─── Item Card with image error fallback ──────────────────────────────────────
const ItemCard = ({ item }) => {
  const [imgError, setImgError] = useState(false);

  // image_path from API is now an absolute URL (https://...)
  const imgSrc = item.image_path && !imgError ? item.image_path : null;

  return (
    <div style={s.itemCard}>
      <div style={s.itemImageWrap}>
        {imgSrc
          ? <img src={imgSrc} alt={item.title} style={s.itemImage} onError={() => setImgError(true)} />
          : <div style={s.itemImagePlaceholder}><Camera size={28} color="#c2cfe0" strokeWidth={1} /></div>}
        <span style={{ ...s.typeBadge, background: item.item_type === 'lost' ? '#1e3a5f' : '#1a4d33', color: '#ffffff' }}>
          {item.item_type.toUpperCase()}
        </span>
        {item.status === 'matched' && <span style={s.matchedBadge}>✓ Matched</span>}
      </div>
      <div style={s.itemBody}>
        <p style={s.itemTitle}>{item.title}</p>
        <p style={s.itemDesc}>{item.description}</p>
        <div style={s.itemMeta}>
          <span style={s.itemMetaRow}><MapPin size={12} strokeWidth={1.5} color="#7a8eaa" />{item.location}</span>
          <span style={s.itemMetaRow}><Clock size={12} strokeWidth={1.5} color="#7a8eaa" />
            {new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        </div>
        {item.reward_amount > 0 && <div style={s.rewardBadge}>Reward: ${item.reward_amount}</div>}
      </div>
    </div>
  );
};

// ─── Matches Tab ──────────────────────────────────────────────────────────────
const MatchesTab = ({ matches, loading, setActiveTab, onRefresh }) => (
  <div style={s.page}>
    <div style={{ ...s.pageHeader, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
      <div>
        <p style={s.heroEyebrow}>AI Results</p>
        <h2 style={s.pageTitle}>Potential Matches</h2>
        <p style={s.pageSub}>Showing matches with 50%+ confidence. Auto-refreshes every 15s.</p>
      </div>
      <button onClick={onRefresh} disabled={loading}
        style={{ marginTop: 6, padding: '8px 16px', background: '#1e3a5f', color: '#fff', borderRadius: 8, fontSize: 12, fontWeight: 600, border: 'none', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1, display: 'flex', alignItems: 'center', gap: 6 }}>
        {loading ? <Spinner size={13} color="#fff" /> : <Activity size={13} color="#fff" />}
        Refresh
      </button>
    </div>
    {loading ? (
      <div style={s.loadingState}><Spinner size={28} color="#1e3a5f" /><span style={s.loadingText}>Analyzing matches...</span></div>
    ) : matches.length === 0 ? (
      <div style={s.emptyState}>
        <Sparkles size={36} color="#c2cfe0" strokeWidth={1} />
        <p style={s.emptyTitle}>No matches yet</p>
        <p style={s.emptyDesc}>Submit a lost and a found item with similar titles to trigger a match.</p>
        <button onClick={() => setActiveTab('report')} style={s.emptyBtn}>Submit a Report</button>
      </div>
    ) : (
      <div style={s.matchGrid}>
        {matches.map((match, i) => (
          <div key={match.match_id || i} style={s.matchCard}>
            <div style={s.matchHeader}>
              <span style={s.matchLabel}>Match Found</span>
              <span style={{ ...s.matchScore, color: match.confidence_score >= 0.9 ? '#1a4d33' : '#1e3a5f' }}>
                {Math.round(match.confidence_score * 100)}%
              </span>
            </div>
            {match.sourceItem && (
              <div style={s.matchSource}>
                <p style={s.matchSourceLabel}>Source Item</p>
                <p style={s.matchSourceTitle}>{match.sourceItem.title}</p>
                <p style={s.matchSourceDesc}>{match.sourceItem.description}</p>
              </div>
            )}
            <div style={s.matchBarWrap}>
              <div style={s.matchBarTrack}>
                <div style={{ ...s.matchBarFill, width: `${Math.round(match.confidence_score * 100)}%`, background: match.confidence_score >= 0.9 ? '#1a4d33' : '#1e3a5f' }} />
              </div>
            </div>
            <p style={s.matchConfidenceLabel}>{match.confidence_score >= 0.75 ? '✉️ Email notification sent' : 'Below email threshold'}</p>
          </div>
        ))}
      </div>
    )}
  </div>
);

// ─── Login Prompt Modal ───────────────────────────────────────────────────────
const LoginPromptModal = ({ onClose, message }) => (
  <div style={s.modalOverlay} onClick={onClose}>
    <div style={s.modalCard} onClick={e => e.stopPropagation()}>
      <div style={s.modalIconWrap}>
        <User size={22} color="#1e3a5f" strokeWidth={1.5} />
      </div>
      <h3 style={s.modalTitle}>Sign in required</h3>
      <p style={s.modalDesc}>{message || 'You need to sign in to access this feature.'}</p>
      <button onClick={onClose} style={s.modalBtn}>Got it</button>
    </div>
  </div>
);

// ─── Profile Dropdown ─────────────────────────────────────────────────────────
const ProfileDropdown = ({ user, profile, onDashboard, onSignOut }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const name = profile?.full_name || user?.user_metadata?.full_name || user?.user_metadata?.name || 'User';
  const email = user?.email || '';
  const avatarUrl = profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture || '';
  const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U';

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button onClick={() => setOpen(!open)} style={s.profileBtn}>
        {avatarUrl ? (
          <img src={avatarUrl} alt="" style={s.profileAvatar} referrerPolicy="no-referrer" />
        ) : (
          <div style={s.profileInitials}>{initials}</div>
        )}
        <ChevronDown size={13} color="#4a6080" style={{ transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }} />
      </button>
      {open && (
        <div style={s.profileDropdown}>
          <div style={s.profileDropdownHeader}>
            {avatarUrl ? (
              <img src={avatarUrl} alt="" style={s.profileDropdownAvatar} referrerPolicy="no-referrer" />
            ) : (
              <div style={s.profileDropdownInitials}>{initials}</div>
            )}
            <div>
              <p style={s.profileDropdownName}>{name}</p>
              <p style={s.profileDropdownEmail}>{email}</p>
            </div>
          </div>
          <div style={s.profileDropdownDivider} />
          <button onClick={() => { setOpen(false); onDashboard(); }} style={s.profileDropdownItem}>
            <TrendingUp size={14} color="#5c718a" strokeWidth={1.5} /> My Dashboard
          </button>
          <button onClick={() => { setOpen(false); onSignOut(); }} style={s.profileDropdownItem}>
            <LogOut size={14} color="#dc2626" strokeWidth={1.5} /> <span style={{ color: '#dc2626' }}>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );
};

// ─── Notification Panel ───────────────────────────────────────────────────────
const NotificationPanel = ({ notifications, open, onClose, onMarkRead }) => {
  useEffect(() => {
    if (open && notifications.some(n => !n.read)) {
      onMarkRead(notifications.filter(n => !n.read).map(n => n.id));
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      {open && <div style={s.panelOverlay} onClick={onClose} />}
      <div style={{ ...s.notifPanel, transform: open ? 'translateX(0)' : 'translateX(100%)' }}>
        <div style={s.notifPanelHeader}>
          <p style={s.notifPanelTitle}>Notifications</p>
          <button onClick={onClose} style={s.notifPanelClose}><X size={18} color="#4a6080" /></button>
        </div>
        {notifications.length === 0 ? (
          <div style={s.notifEmpty}>
            <Bell size={28} color="#c2cfe0" strokeWidth={1} />
            <p style={{ fontSize: 13, color: '#7a8eaa', marginTop: 8 }}>No notifications yet</p>
          </div>
        ) : (
          <div style={s.notifList}>
            {notifications.map(n => (
              <div key={n.id} style={{ ...s.notifItem, background: n.read ? '#fff' : '#f0f7ff' }}>
                <div style={s.notifDot(n.read)} />
                <div style={{ flex: 1 }}>
                  <p style={s.notifItemTitle}>{n.item_title || 'Match found'}</p>
                  <p style={s.notifItemConf}>{n.confidence ? `${Math.round(n.confidence * 100)}% confidence` : 'Potential match detected'}</p>
                  <p style={s.notifItemTime}>{n.created_at ? new Date(n.created_at).toLocaleString() : ''}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
};

// ─── Onboarding Tour ──────────────────────────────────────────────────────────
const OnboardingTour = ({ onFinish }) => {
  const [step, setStep] = useState(0);
  const steps = [
    { title: 'Report Items', desc: 'Upload photos and details of lost or found items. Our AI extracts features automatically.', icon: Upload },
    { title: 'Browse & Search', desc: 'Search through all reported items by title, description, location, or category.', icon: Search },
    { title: 'AI Matches', desc: 'Our matching engine compares items and notifies both parties when a match is found.', icon: Sparkles },
  ];
  const cur = steps[step];
  const Icon = cur.icon;

  return (
    <div style={s.tourOverlay}>
      <div style={s.tourCard}>
        <div style={s.tourIconWrap}><Icon size={26} color="#1e3a5f" strokeWidth={1.5} /></div>
        <p style={s.tourStep}>Step {step + 1} of {steps.length}</p>
        <h3 style={s.tourTitle}>{cur.title}</h3>
        <p style={s.tourDesc}>{cur.desc}</p>
        <div style={s.tourActions}>
          <button onClick={onFinish} style={s.tourSkip}>Skip tour</button>
          <button onClick={() => step < steps.length - 1 ? setStep(step + 1) : onFinish()} style={s.tourNext}>
            {step < steps.length - 1 ? 'Next →' : 'Get Started'}
          </button>
        </div>
        <div style={s.tourDots}>
          {steps.map((_, i) => <div key={i} style={{ ...s.tourDot, background: i === step ? '#1e3a5f' : '#dde3ed' }} />)}
        </div>
      </div>
    </div>
  );
};

// ─── Main App ─────────────────────────────────────────────────────────────────
const FindoraApp = ({ showOnboarding, setShowOnboarding }) => {
  const { user, isGuest, signOut, profile } = useAuth();
  const [activeTab, setActiveTab]   = useState('home');
  const [activeCTA, setActiveCTA]   = useState(null);
  const [items, setItems]           = useState([]);
  const [matches, setMatches]       = useState([]);
  const [loading, setLoading]       = useState(false);
  const [stats, setStats]           = useState(null);
  const [filterType, setFilterType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [notification, setNotification] = useState(null);
  const [formErrors, setFormErrors] = useState({});
  const [previewUrl, setPreviewUrl] = useState(null);
  const [backendOnline, setBackendOnline] = useState(true);
  const [loginPrompt, setLoginPrompt] = useState(null);
  const [notifPanelOpen, setNotifPanelOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [showDashboard, setShowDashboard] = useState(false);
  const prevMatchCountRef = useRef(0);

  const userId = user?.id || null;

  const [formData, setFormData] = useState({
    title: '', description: '', category: 'wallet', location: '',
    latitude: null, longitude: null, itemType: 'lost', rewardAmount: 0,
    contactEmail: user?.email || '', contactPhone: '', image: null
  });

  // Pre-fill email when user logs in
  useEffect(() => {
    if (user?.email && !formData.contactEmail) {
      setFormData(f => ({ ...f, contactEmail: user.email }));
    }
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Keep-alive ping every 8 minutes to prevent Render sleep ──────────────
  useEffect(() => {
    const ping = () => fetch(`${API_BASE}/ping`).then(() => setBackendOnline(true)).catch(() => setBackendOnline(false));
    ping();
    const t = setInterval(ping, 8 * 60 * 1000);
    return () => clearInterval(t);
  }, []);

  // ── Tab data ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab === 'browse')  fetchItems();
    if (activeTab === 'home')    fetchStats();
    if (activeTab === 'matches') fetchMatches();
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-poll matches every 15s ───────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'matches') return;
    const interval = setInterval(fetchMatches, 15000);
    return () => clearInterval(interval);
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Poll notifications every 30s ──────────────────────────────────────────
  useEffect(() => {
    if (!userId) return;
    const fetchNotif = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/notifications/${userId}`);
        if (res.ok) {
          const data = await res.json();
          setNotifications(data);
          // Play chime on new notifications
          if (data.length > prevMatchCountRef.current && prevMatchCountRef.current > 0) {
            playMatchChime();
          }
          prevMatchCountRef.current = data.length;
        }
      } catch {}
    };
    fetchNotif();
    const t = setInterval(fetchNotif, 30000);
    return () => clearInterval(t);
  }, [userId]);

  const showNotificationMsg = useCallback((message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      if (res.ok) setStats(await res.json());
    } catch {}
  };

  const fetchItems = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/items`);
      if (res.ok) setItems(await res.json());
      else showNotificationMsg('Failed to load items', 'error');
    } catch {
      showNotificationMsg('Cannot reach backend — it may be starting up (30s)', 'error');
    } finally { setLoading(false); }
  };

  const fetchMatches = useCallback(async () => {
    try {
      setLoading(true);
      const itemsRes = await fetch(`${API_BASE}/api/items`);
      if (!itemsRes.ok) throw new Error();
      const allItems = await itemsRes.json();
      setItems(allItems);

      const matchResults = await Promise.all(
        allItems.map(async item => {
          const res = await fetch(`${API_BASE}/api/matches/${item.item_id}`);
          if (!res.ok) return [];
          const data = await res.json();
          return data
            .filter(m => m.confidence_score >= 0.50)
            .map(m => ({ ...m, sourceItem: item }));
        })
      );

      const seen = new Set();
      const deduped = matchResults.flat().filter(m => {
        if (seen.has(m.match_id)) return false;
        seen.add(m.match_id);
        return true;
      });
      setMatches(deduped);
    } catch {
      showNotificationMsg('Failed to load matches', 'error');
    } finally { setLoading(false); }
  }, [showNotificationMsg]);

  const validateForm = () => {
    const errors = {};
    if (!formData.title.trim()) errors.title = 'Title is required';
    if (!formData.description.trim() || formData.description.length < 10)
      errors.description = 'Description must be at least 10 characters';
    if (!formData.location.trim()) errors.location = 'Location is required';
    if (!formData.contactEmail.trim()) errors.contactEmail = 'Email is required';
    if (formData.contactEmail && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(formData.contactEmail))
      errors.contactEmail = 'Enter a valid email address';
    if (!formData.image) errors.image = 'Photo is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) { showNotificationMsg('Please fix the errors below', 'error'); return; }
    if (!userId) { showNotificationMsg('You must be signed in to report items', 'error'); return; }
    try {
      setLoading(true);
      const contactInfo = formData.contactPhone.trim()
        ? `${formData.contactEmail.trim()} | ${formData.contactPhone.trim()}`
        : formData.contactEmail.trim();

      const data = new FormData();
      data.append('title',         formData.title.trim());
      data.append('description',   formData.description.trim());
      data.append('category',      formData.category);
      data.append('location',      formData.location.trim());
      data.append('item_type',     formData.itemType);
      data.append('reward_amount', formData.rewardAmount || 0);
      data.append('contact_info',  contactInfo);
      data.append('user_id',       userId);
      data.append('image',         formData.image);
      if (formData.latitude)  data.append('latitude',  formData.latitude);
      if (formData.longitude) data.append('longitude', formData.longitude);

      const res = await fetch(`${API_BASE}/api/items/report`, { method: 'POST', body: data });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || `HTTP ${res.status}`);
      }

      showNotificationMsg('✅ Item reported! AI is scanning for matches...', 'success');
      setFormData({ title: '', description: '', category: 'wallet', location: '',
        latitude: null, longitude: null, itemType: 'lost', rewardAmount: 0,
        contactEmail: user?.email || '', contactPhone: '', image: null });
      setPreviewUrl(null);
      setFormErrors({});
      setTimeout(() => setActiveTab('browse'), 1800);
    } catch (err) {
      showNotificationMsg(err.message || 'Submission failed — backend may be starting up', 'error');
    } finally { setLoading(false); }
  };

  const getLocation = () => {
    if (!navigator.geolocation) { showNotificationMsg('Geolocation not supported', 'error'); return; }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      pos => {
        setFormData(f => ({ ...f, latitude: pos.coords.latitude, longitude: pos.coords.longitude }));
        showNotificationMsg('Location captured', 'success');
        setLoading(false);
      },
      () => { showNotificationMsg('Could not get location', 'error'); setLoading(false); },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handleTabClick = (tabId) => {
    if (isGuest && (tabId === 'report' || tabId === 'matches')) {
      setLoginPrompt(tabId === 'report'
        ? 'Sign in to report lost or found items and receive match notifications.'
        : 'Sign in to view your AI-powered match results.');
      return;
    }
    setShowDashboard(false);
    setActiveTab(tabId);
  };

  const markNotifRead = async (ids) => {
    try {
      await fetch(`${API_BASE}/api/notifications/mark-read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notification_ids: ids }),
      });
      setNotifications(prev => prev.map(n => ids.includes(n.id) ? { ...n, read: true } : n));
    } catch {}
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  if (showDashboard) {
    return (
      <div style={s.root}>
        <style>{globalCss}</style>
        <header style={s.header}>
          <div style={s.headerInner}>
            <div style={s.logo} onClick={() => { setShowDashboard(false); setActiveTab('home'); }} role="button" tabIndex={0}>
              <div style={s.logoMark}><Search size={15} color="#ffffff" strokeWidth={2} /></div>
              <div><p style={s.logoName}>Findora</p><p style={s.logoTag}>AI Lost &amp; Found</p></div>
            </div>
          </div>
        </header>
        <main style={s.main}>
          <Suspense fallback={<div style={s.loadingState}><Spinner size={28} color="#1e3a5f" /></div>}>
            <DashboardPage onBack={() => setShowDashboard(false)} />
          </Suspense>
        </main>
      </div>
    );
  }

  return (
    <div style={s.root}>
      <style>{globalCss}</style>

      {notification && (
        <div style={{ ...s.notification, background: notification.type === 'success' ? '#1a4d33' : '#7f1d1d' }}>
          {notification.type === 'success' ? <Check size={16} /> : <AlertCircle size={16} />}
          <span>{notification.message}</span>
        </div>
      )}

      {!backendOnline && (
        <div style={s.offlineBanner}>
          ⚠️ Backend is starting up (Render free tier) — please wait ~30 seconds and refresh
        </div>
      )}

      {loginPrompt && <LoginPromptModal onClose={() => setLoginPrompt(null)} message={loginPrompt} />}

      {showOnboarding && <OnboardingTour onFinish={() => setShowOnboarding(false)} />}

      <NotificationPanel
        notifications={notifications}
        open={notifPanelOpen}
        onClose={() => setNotifPanelOpen(false)}
        onMarkRead={markNotifRead}
      />

      <header style={s.header}>
        <div style={s.headerInner}>
          <div style={s.logo} onClick={() => { setActiveTab('home'); }} role="button" tabIndex={0}>
            <div style={s.logoMark}><Search size={15} color="#ffffff" strokeWidth={2} /></div>
            <div><p style={s.logoName}>Findora</p><p style={s.logoTag}>AI Lost &amp; Found</p></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button style={s.bellBtn} onClick={() => setNotifPanelOpen(true)}>
              <Bell size={17} strokeWidth={1.5} color="#4a6080" />
              {unreadCount > 0 && <span style={s.bellBadge}>{unreadCount > 9 ? '9+' : unreadCount}</span>}
            </button>
            {user && !isGuest ? (
              <ProfileDropdown
                user={user}
                profile={profile}
                onDashboard={() => setShowDashboard(true)}
                onSignOut={signOut}
              />
            ) : (
              <button onClick={() => setLoginPrompt('Sign in to access all features including reporting items and viewing matches.')} style={s.signInHeaderBtn}>
                Sign in
              </button>
            )}
          </div>
        </div>
      </header>

      <nav style={s.nav}>
        <div style={s.navInner}>
          {[
            { id: 'home',    label: 'Home' },
            { id: 'report',  label: 'Report' },
            { id: 'browse',  label: 'Browse' },
            { id: 'matches', label: `Matches${matches.length > 0 ? ` (${matches.length})` : ''}` },
          ].map(tab => (
            <button key={tab.id} onClick={() => handleTabClick(tab.id)}
              style={{ ...s.navBtn, color: activeTab === tab.id ? '#1e3a5f' : '#7a8eaa', borderBottom: `2px solid ${activeTab === tab.id ? '#1e3a5f' : 'transparent'}`, fontWeight: activeTab === tab.id ? 600 : 500 }}>
              {tab.label}
              {isGuest && (tab.id === 'report' || tab.id === 'matches') && <span style={s.lockIcon}>🔒</span>}
            </button>
          ))}
        </div>
      </nav>

      <main style={s.main}>
        <div className="tab-fade" key={activeTab}>
          {activeTab === 'home'    && <HomeTab stats={stats} activeCTA={activeCTA} setActiveCTA={setActiveCTA} setFormData={setFormData} setActiveTab={handleTabClick} />}
          {activeTab === 'report'  && <ReportTab formData={formData} setFormData={setFormData} formErrors={formErrors} setFormErrors={setFormErrors} previewUrl={previewUrl} setPreviewUrl={setPreviewUrl} loading={loading} handleSubmit={handleSubmit} getLocation={getLocation} showNotification={showNotificationMsg} />}
          {activeTab === 'browse'  && <BrowseTab items={items} loading={loading} filterType={filterType} setFilterType={setFilterType} searchQuery={searchQuery} setSearchQuery={setSearchQuery} setActiveTab={handleTabClick} />}
          {activeTab === 'matches' && <MatchesTab matches={matches} loading={loading} setActiveTab={handleTabClick} onRefresh={fetchMatches} />}
        </div>
      </main>

      <footer style={s.footer}>
        <div style={s.footerInner}>
          <div style={s.footerBrand}>
            <div style={s.footerLogoMark}><Search size={14} color="#ffffff" strokeWidth={2} /></div>
            <p style={s.footerName}>Findora</p>
          </div>
          <p style={s.footerTagline}>Intelligent Lost &amp; Found — Powered by AI</p>
          <div style={s.footerPillRow}>
            <span style={s.footerPill}><Zap size={11} color="#7a9bbf" strokeWidth={1.5} style={{ marginRight: 5 }} />Keyword AI Matching</span>
            <span style={s.footerPill}><Search size={11} color="#7a9bbf" strokeWidth={1.5} style={{ marginRight: 5 }} />Semantic Analysis</span>
            <span style={s.footerPill}><Shield size={11} color="#7a9bbf" strokeWidth={1.5} style={{ marginRight: 5 }} />Secure &amp; Private</span>
          </div>
          <div style={s.footerDivider} />
          <div style={s.footerContact}>
            <div style={s.footerAuthor}>
              <div style={s.footerAvatar}>DR</div>
              <div>
                <p style={s.footerAuthorName}>Deepak Roshan A</p>
                <p style={s.footerAuthorRole}>AI Engineer</p>
              </div>
            </div>
            <a href="mailto:deepakroshan380@gmail.com" style={s.footerEmail}>deepakroshan380@gmail.com</a>
          </div>
          <p style={s.footerCopy}>© {new Date().getFullYear()} Findora. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

// ─── Top-Level App (Splash → Auth → Main) ─────────────────────────────────────
const App = () => {
  const { user, loading, isGuest } = useAuth();
  const [showSplash, setShowSplash] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);

  if (showSplash) return <SplashScreen onFinish={() => setShowSplash(false)} />;

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
      <Spinner size={32} color="#1e3a5f" />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (!user && !isGuest) return <AuthPage onSignupComplete={() => setShowOnboarding(true)} />;

  return <FindoraApp showOnboarding={showOnboarding} setShowOnboarding={setShowOnboarding} />;
};

// ─── Global CSS ───────────────────────────────────────────────────────────────
const globalCss = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #f0f2f5 !important; -webkit-font-smoothing: antialiased; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.55;transform:scale(.8)} }
  @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .tab-fade { animation: fadeUp 0.28s ease both; }
  button { cursor: pointer; border: none; background: none; font-family: inherit; font-size: inherit; }
  input, textarea, select { font-family: inherit; font-size: inherit; outline: none; color: #0f172a; background: #ffffff; }
  input::placeholder, textarea::placeholder { color: #9aafc4 !important; }
  input:focus, textarea:focus, select:focus { border-color: #1e3a5f !important; box-shadow: 0 0 0 3px rgba(30,58,95,0.1); }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: #f0f2f5; }
  ::-webkit-scrollbar-thumb { background: #c5d0e0; border-radius: 10px; }
`;

// ─── Styles ───────────────────────────────────────────────────────────────────
const s = {
  root: { fontFamily: "'DM Sans', system-ui, sans-serif", minHeight: '100vh', background: '#f0f2f5', color: '#0f172a' },
  offlineBanner: { background: '#7f1d1d', color: '#fff', textAlign: 'center', padding: '10px 20px', fontSize: 13, fontWeight: 500 },
  header: { background: '#ffffff', borderBottom: '1px solid #dde3ed', position: 'sticky', top: 0, zIndex: 50 },
  headerInner: { maxWidth: 960, margin: '0 auto', padding: '10px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  logo: { display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' },
  logoMark: { width: 34, height: 34, borderRadius: 10, background: '#1e3a5f', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  logoName: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 17, color: '#0f172a', lineHeight: 1.1 },
  logoTag: { fontSize: 9, color: '#7a8eaa', letterSpacing: '0.09em', textTransform: 'uppercase' },
  bellBtn: { position: 'relative', width: 34, height: 34, borderRadius: 8, background: '#eef1f7', display: 'flex', alignItems: 'center', justifyContent: 'center', border: 'none', cursor: 'pointer' },
  bellBadge: { position: 'absolute', top: 3, right: 3, minWidth: 16, height: 16, background: '#e05252', borderRadius: 10, border: '1.5px solid #fff', fontSize: 9, fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 3px' },
  nav: { background: '#ffffff', borderBottom: '1px solid #dde3ed', position: 'sticky', top: 54, zIndex: 40 },
  navInner: { maxWidth: 960, margin: '0 auto', padding: '0 20px', display: 'flex' },
  navBtn: { padding: '12px 18px', fontSize: 13, letterSpacing: '0.01em', transition: 'color 0.2s', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 4 },
  lockIcon: { fontSize: 10, opacity: 0.5 },
  main: { maxWidth: 960, margin: '0 auto', padding: '0 20px 60px' },
  page: { paddingTop: 32 },
  pageHeader: { marginBottom: 24 },
  pageTitle: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 'clamp(22px, 5vw, 32px)', color: '#0f172a', marginTop: 4, lineHeight: 1.1 },
  pageSub: { fontSize: 13, color: '#5c718a', marginTop: 6, lineHeight: 1.65 },
  hero: { textAlign: 'center', padding: '36px 0 28px' },
  heroEyebrow: { fontSize: 10, fontWeight: 700, color: '#7a8eaa', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 },
  heroTitle: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 'clamp(40px, 10vw, 68px)', color: '#0f172a', lineHeight: 1, letterSpacing: '-0.02em' },
  heroSub: { fontSize: 14, color: '#5c718a', marginTop: 12, lineHeight: 1.7, maxWidth: 400, margin: '12px auto 0' },
  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 },
  statCard: { background: '#ffffff', border: '1px solid #dde3ed', borderRadius: 11, padding: '13px 8px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 },
  statValue: { fontFamily: "'DM Serif Display', serif", fontSize: 24, color: '#1e3a5f', lineHeight: 1.1 },
  statLabel: { fontSize: 10, color: '#7a8eaa', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em' },
  ctaGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10, marginBottom: 22 },
  ctaCard: { display: 'flex', alignItems: 'center', gap: 13, padding: '18px 16px', borderRadius: 13, cursor: 'pointer', textAlign: 'left', border: '1.5px solid #c5d0e0', transition: 'background 0.22s ease, border-color 0.22s ease', width: '100%' },
  ctaIconBox: { width: 38, height: 38, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'background 0.22s ease' },
  ctaTitle: { fontSize: 14, fontWeight: 700, marginBottom: 3 },
  ctaSub: { fontSize: 12, lineHeight: 1.45 },
  howSection: { background: '#ffffff', border: '1px solid #dde3ed', borderRadius: 13, padding: '22px 20px', marginBottom: 18 },
  sectionLabel: { fontSize: 10, fontWeight: 700, color: '#7a8eaa', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 18 },
  howRow: { display: 'flex', alignItems: 'flex-start', gap: 15, marginBottom: 16, paddingBottom: 16, borderBottom: '1px solid #eef1f7' },
  howStep: { fontFamily: "'DM Serif Display', serif", fontSize: 26, color: '#dde3ed', lineHeight: 1, flexShrink: 0, width: 38 },
  howTitle: { fontSize: 14, fontWeight: 600, color: '#0f172a', marginBottom: 3 },
  howDesc: { fontSize: 13, color: '#5c718a', lineHeight: 1.55 },
  agentSection: { background: '#ffffff', border: '1px solid #dde3ed', borderRadius: 13, padding: '22px 20px', marginBottom: 18 },
  agentHeader: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 },
  agentDotWrap: { flexShrink: 0 },
  agentDot: { width: 10, height: 10, borderRadius: '50%', background: '#1a4d33', animation: 'pulse 1.8s ease-in-out infinite', boxShadow: '0 0 0 3px rgba(26,77,51,0.15)' },
  agentTitle: { fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 2 },
  agentSub: { fontSize: 11.5, color: '#5c718a', lineHeight: 1.5 },
  agentBadge: { fontSize: 10, fontWeight: 700, color: '#1a4d33', background: '#e8f2ec', border: '1px solid #b8ddc8', borderRadius: 20, padding: '3px 10px', flexShrink: 0 },
  agentEngines: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 14 },
  enginePill: { background: '#f8fafc', border: '1px solid #eef1f7', borderRadius: 9, padding: '10px 12px', textAlign: 'center' },
  engineLabel: { fontSize: 12, fontWeight: 600, color: '#1e3a5f', marginBottom: 2 },
  engineSub: { fontSize: 10, color: '#7a8eaa' },
  agentSteps: { display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 14 },
  agentStep: { display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 8 },
  agentStepIcon: { width: 20, height: 20, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  agentStepLabel: { fontSize: 12, fontWeight: 600, marginBottom: 3 },
  agentStepSub: { fontSize: 11, color: '#2d7a50' },
  scanBarTrack: { height: 3, background: '#dde3ed', borderRadius: 2, overflow: 'hidden', marginTop: 4 },
  scanBarFill: { height: '100%', background: '#1e3a5f', borderRadius: 2, transition: 'width 0.06s linear' },
  agentNotifyBar: { display: 'flex', alignItems: 'center', gap: 12, background: '#1e3a5f', borderRadius: 10, padding: '13px 15px' },
  agentNotifyIcon: { width: 28, height: 28, borderRadius: 8, background: '#1a4d33', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  agentNotifyTitle: { fontSize: 12.5, fontWeight: 600, color: '#ffffff', marginBottom: 2 },
  agentNotifySub: { fontSize: 11, color: '#7a9bbf' },
  badges: { display: 'flex', gap: 7, flexWrap: 'wrap', marginBottom: 8 },
  badge: { fontSize: 12, color: '#4a6080', background: '#eef1f7', borderRadius: 20, padding: '5px 12px', fontWeight: 500 },
  toggle: { display: 'flex', background: '#eef1f7', borderRadius: 9, padding: 3, marginBottom: 22, gap: 3 },
  toggleBtn: { flex: 1, padding: '10px', borderRadius: 7, fontSize: 13, fontWeight: 500, transition: 'background 0.22s, color 0.22s', border: 'none', cursor: 'pointer', fontFamily: 'inherit' },
  formStack: { display: 'flex', flexDirection: 'column', gap: 18 },
  formGroup: { display: 'flex', flexDirection: 'column', gap: 5 },
  label: { fontSize: 12, fontWeight: 600, color: '#2d4460', letterSpacing: '0.01em' },
  req: { color: '#e05252', marginLeft: 2 },
  optional: { fontWeight: 400, color: '#7a8eaa', fontSize: 11 },
  input: { width: '100%', border: '1px solid #dde3ed', borderRadius: 9, padding: '10px 13px', fontSize: 13, color: '#0f172a', background: '#ffffff', transition: 'border 0.15s, box-shadow 0.15s' },
  inputError: { borderColor: '#fca5a5', background: '#fff5f5' },
  textarea: { resize: 'vertical', minHeight: 96, lineHeight: 1.6 },
  charRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  charCount: { fontSize: 11, color: '#9aafc4' },
  locationRow: { display: 'flex', gap: 8 },
  gpsBtn: { flexShrink: 0, width: 42, height: 42, background: '#1e3a5f', borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', border: 'none', cursor: 'pointer' },
  gpsConfirm: { display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: '#1a4d33', fontWeight: 500, marginTop: 4 },
  contactSection: { background: '#f8fafc', border: '1px solid #dde3ed', borderRadius: 11, padding: '16px' },
  contactSectionTitle: { fontSize: 12, fontWeight: 700, color: '#2d4460', marginBottom: 4, letterSpacing: '0.01em' },
  contactSectionSub: { fontSize: 11.5, color: '#5c718a', lineHeight: 1.6 },
  contactHint: { fontSize: 11, color: '#9aafc4', marginTop: 4 },
  rewardWrap: { position: 'relative' },
  currencySymbol: { position: 'absolute', left: 13, top: '50%', transform: 'translateY(-50%)', fontSize: 13, color: '#9aafc4' },
  uploadZone: { border: '1.5px dashed #c2cfe0', borderRadius: 11, padding: 26, textAlign: 'center', background: '#f8fafc' },
  uploadZoneError: { borderColor: '#fca5a5', background: '#fff5f5' },
  uploadLabel: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 7, cursor: 'pointer' },
  uploadText: { fontSize: 13, fontWeight: 500, color: '#2d4460' },
  uploadHint: { fontSize: 11, color: '#9aafc4' },
  previewWrap: { position: 'relative', display: 'inline-block' },
  previewImg: { maxHeight: 200, borderRadius: 8, objectFit: 'contain' },
  removeBtn: { position: 'absolute', top: -8, right: -8, width: 26, height: 26, background: '#e05252', color: '#fff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: 'none' },
  fieldError: { display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: '#e05252', fontWeight: 500 },
  submitBtn: { width: '100%', padding: '13px', borderRadius: 11, fontSize: 14, fontWeight: 600, color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 4, border: 'none', transition: 'opacity 0.15s' },
  searchRow: { display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 16 },
  searchWrap: { position: 'relative', flex: 1, minWidth: 200 },
  searchIcon: { position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)' },
  searchInput: { width: '100%', border: '1px solid #dde3ed', borderRadius: 9, padding: '10px 13px 10px 33px', fontSize: 13, color: '#0f172a', background: '#ffffff' },
  filterRow: { display: 'flex', gap: 6 },
  filterBtn: { padding: '9px 15px', borderRadius: 8, fontSize: 12, fontWeight: 500, border: '1px solid', transition: 'all 0.18s', cursor: 'pointer', fontFamily: 'inherit' },
  resultCount: { fontSize: 12, color: '#7a8eaa', marginBottom: 12, fontWeight: 500 },
  cardGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 },
  itemCard: { background: '#ffffff', border: '1px solid #dde3ed', borderRadius: 13, overflow: 'hidden' },
  itemImageWrap: { position: 'relative', height: 170, background: '#eef1f7' },
  itemImage: { width: '100%', height: '100%', objectFit: 'cover' },
  itemImagePlaceholder: { width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  typeBadge: { position: 'absolute', top: 9, right: 9, fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', padding: '3px 8px', borderRadius: 5 },
  matchedBadge: { position: 'absolute', bottom: 9, left: 9, fontSize: 10, fontWeight: 700, color: '#1a4d33', background: '#e8f2ec', border: '1px solid #b8ddc8', borderRadius: 5, padding: '3px 8px' },
  itemBody: { padding: '13px 15px' },
  itemTitle: { fontSize: 14, fontWeight: 600, color: '#0f172a', marginBottom: 5 },
  itemDesc: { fontSize: 12.5, color: '#5c718a', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', marginBottom: 9 },
  itemMeta: { display: 'flex', flexDirection: 'column', gap: 4 },
  itemMetaRow: { display: 'flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: '#7a8eaa' },
  rewardBadge: { marginTop: 9, fontSize: 12, color: '#1a4d33', background: '#e8f2ec', border: '1px solid #a7d4b8', borderRadius: 6, padding: '4px 10px', fontWeight: 600, display: 'inline-block' },
  matchGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 },
  matchCard: { background: '#ffffff', border: '1px solid #dde3ed', borderRadius: 13, padding: '18px' },
  matchHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  matchLabel: { fontSize: 12.5, fontWeight: 600, color: '#2d4460' },
  matchScore: { fontSize: 22, fontFamily: "'DM Serif Display', serif" },
  matchSource: { background: '#f0f2f5', borderRadius: 9, padding: '11px', marginBottom: 12 },
  matchSourceLabel: { fontSize: 9, fontWeight: 700, color: '#7a8eaa', textTransform: 'uppercase', letterSpacing: '0.09em', marginBottom: 4 },
  matchSourceTitle: { fontSize: 13.5, fontWeight: 600, color: '#0f172a', marginBottom: 3 },
  matchSourceDesc: { fontSize: 12, color: '#5c718a', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' },
  matchBarWrap: { marginBottom: 7 },
  matchBarTrack: { height: 5, background: '#eef1f7', borderRadius: 4, overflow: 'hidden' },
  matchBarFill: { height: '100%', borderRadius: 4, transition: 'width 0.6s ease' },
  matchConfidenceLabel: { fontSize: 12, color: '#5c718a', fontWeight: 500 },
  loadingState: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '60px 0' },
  loadingText: { fontSize: 13, color: '#7a8eaa' },
  emptyState: { display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '60px 20px', gap: 10 },
  emptyTitle: { fontSize: 15, fontWeight: 600, color: '#2d4460' },
  emptyDesc: { fontSize: 13, color: '#7a8eaa', lineHeight: 1.6 },
  emptyBtn: { marginTop: 8, padding: '10px 22px', background: '#1e3a5f', color: '#fff', borderRadius: 9, fontSize: 13, fontWeight: 500, cursor: 'pointer', border: 'none' },
  notification: { position: 'fixed', top: 14, right: 14, zIndex: 999, color: '#fff', padding: '10px 16px', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500, animation: 'slideDown 0.25s ease', maxWidth: 340 },
  footer: { background: '#1e3a5f', marginTop: 20 },
  footerInner: { maxWidth: 960, margin: '0 auto', padding: '40px 20px 32px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 },
  footerBrand: { display: 'flex', alignItems: 'center', gap: 10 },
  footerLogoMark: { width: 32, height: 32, borderRadius: 9, background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.16)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  footerName: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 22, color: '#ffffff', lineHeight: 1 },
  footerTagline: { fontSize: 13, color: '#94b8d4', letterSpacing: '0.02em', textAlign: 'center' },
  footerPillRow: { display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 16, width: '100%' },
  footerPill: { display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: '#7a9bbf', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 20, padding: '5px 12px', fontWeight: 500 },
  footerDivider: { width: '100%', borderTop: '1px solid rgba(255,255,255,0.08)', marginTop: 2 },
  footerContact: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: 12, paddingTop: 4 },
  footerAuthor: { display: 'flex', alignItems: 'center', gap: 10 },
  footerAvatar: { width: 36, height: 36, borderRadius: '50%', background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, color: '#ffffff', letterSpacing: '0.04em', flexShrink: 0 },
  footerAuthorName: { fontSize: 13, fontWeight: 600, color: '#ffffff', marginBottom: 2 },
  footerAuthorRole: { fontSize: 11, color: '#7a9bbf', letterSpacing: '0.04em' },
  footerEmail: { fontSize: 12, color: '#94b8d4', textDecoration: 'none', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 20, padding: '6px 14px', fontWeight: 500 },
  footerCopy: { fontSize: 11, color: '#4a6a8a', marginTop: 2, textAlign: 'center' },

  // ── New V2 styles ──────────────────────────────────────────────────────────
  signInHeaderBtn: { padding: '7px 16px', background: '#1e3a5f', color: '#fff', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer', border: 'none' },

  // Profile dropdown
  profileBtn: { display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px 4px 4px', background: '#eef1f7', borderRadius: 20, border: '1px solid #dde3ed', cursor: 'pointer' },
  profileAvatar: { width: 28, height: 28, borderRadius: '50%', objectFit: 'cover' },
  profileInitials: { width: 28, height: 28, borderRadius: '50%', background: '#1e3a5f', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, letterSpacing: '0.04em' },
  profileDropdown: { position: 'absolute', top: 42, right: 0, width: 240, background: '#fff', border: '1px solid #dde3ed', borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.1)', zIndex: 100, overflow: 'hidden', animation: 'fadeUp 0.2s ease both' },
  profileDropdownHeader: { display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px' },
  profileDropdownAvatar: { width: 36, height: 36, borderRadius: '50%', objectFit: 'cover' },
  profileDropdownInitials: { width: 36, height: 36, borderRadius: '50%', background: '#1e3a5f', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700 },
  profileDropdownName: { fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 2 },
  profileDropdownEmail: { fontSize: 11, color: '#7a8eaa' },
  profileDropdownDivider: { height: 1, background: '#eef1f7' },
  profileDropdownItem: { display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '11px 16px', fontSize: 13, fontWeight: 500, color: '#2d4460', cursor: 'pointer', border: 'none', background: 'none', fontFamily: 'inherit', textAlign: 'left', transition: 'background 0.12s' },

  // Notification panel
  panelOverlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', zIndex: 200 },
  notifPanel: { position: 'fixed', top: 0, right: 0, bottom: 0, width: 340, maxWidth: '90vw', background: '#fff', borderLeft: '1px solid #dde3ed', zIndex: 201, display: 'flex', flexDirection: 'column', transition: 'transform 0.3s ease', boxShadow: '-4px 0 20px rgba(0,0,0,0.08)' },
  notifPanelHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #dde3ed' },
  notifPanelTitle: { fontSize: 15, fontWeight: 600, color: '#0f172a' },
  notifPanelClose: { background: 'none', border: 'none', cursor: 'pointer', padding: 4 },
  notifEmpty: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40 },
  notifList: { flex: 1, overflowY: 'auto', padding: '8px 0' },
  notifItem: { display: 'flex', alignItems: 'flex-start', gap: 10, padding: '14px 20px', borderBottom: '1px solid #f0f2f5', transition: 'background 0.15s' },
  notifDot: (read) => ({ width: 8, height: 8, borderRadius: '50%', background: read ? '#dde3ed' : '#1e3a5f', marginTop: 5, flexShrink: 0 }),
  notifItemTitle: { fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 3 },
  notifItemConf: { fontSize: 12, color: '#1a4d33', fontWeight: 500, marginBottom: 2 },
  notifItemTime: { fontSize: 11, color: '#9aafc4' },

  // Login prompt modal
  modalOverlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 },
  modalCard: { background: '#fff', borderRadius: 16, padding: '32px 28px', maxWidth: 360, width: '100%', textAlign: 'center', animation: 'fadeUp 0.25s ease both' },
  modalIconWrap: { width: 52, height: 52, borderRadius: 14, background: '#eef1f7', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' },
  modalTitle: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 20, color: '#0f172a', marginBottom: 8 },
  modalDesc: { fontSize: 13, color: '#5c718a', lineHeight: 1.65, marginBottom: 20 },
  modalBtn: { padding: '10px 28px', background: '#1e3a5f', color: '#fff', borderRadius: 9, fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none' },

  // Onboarding tour
  tourOverlay: { position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', zIndex: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 },
  tourCard: { background: '#fff', borderRadius: 18, padding: '36px 32px 28px', maxWidth: 380, width: '100%', textAlign: 'center', animation: 'fadeUp 0.3s ease both' },
  tourIconWrap: { width: 56, height: 56, borderRadius: 16, background: '#eef1f7', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 18px' },
  tourStep: { fontSize: 10, fontWeight: 700, color: '#7a8eaa', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 10 },
  tourTitle: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 22, color: '#0f172a', marginBottom: 8 },
  tourDesc: { fontSize: 13, color: '#5c718a', lineHeight: 1.65, marginBottom: 24 },
  tourActions: { display: 'flex', gap: 10, justifyContent: 'center' },
  tourSkip: { padding: '9px 18px', fontSize: 13, color: '#7a8eaa', fontWeight: 500, cursor: 'pointer', border: 'none', background: 'none' },
  tourNext: { padding: '9px 22px', background: '#1e3a5f', color: '#fff', borderRadius: 9, fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none' },
  tourDots: { display: 'flex', gap: 6, justifyContent: 'center', marginTop: 20 },
  tourDot: { width: 7, height: 7, borderRadius: '50%', transition: 'background 0.2s' },
};

export default App;