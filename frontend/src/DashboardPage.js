import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import {
  Camera, MapPin, Clock, Trash2, Search, TrendingUp, Check, BarChart3,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const API_BASE = (process.env.REACT_APP_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const CATEGORY_COLORS = {
  wallet: '#1e3a5f', phone: '#2d5a3d', keys: '#5a3d1e', bag: '#3d1e5a',
  jewelry: '#8b6914', documents: '#14608b', electronics: '#4a1e6d',
  clothing: '#6d4a1e', accessories: '#1e6d4a', other: '#7a8eaa',
};

const Spinner = ({ size = 20, color = '#1e3a5f' }) => (
  <div style={{
    width: size, height: size,
    border: `2px solid rgba(30,58,95,0.15)`,
    borderTopColor: color, borderRadius: '50%',
    animation: 'spin 0.75s linear infinite',
  }} />
);

const DashboardPage = ({ onBack }) => {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);

  const fetchMyData = useCallback(async () => {
    if (!user) return;
    try {
      setLoading(true);
      // Fetch all items, filter client-side by user_id
      const itemsRes = await fetch(`${API_BASE}/api/items`);
      if (itemsRes.ok) {
        const all = await itemsRes.json();
        const mine = all.filter(i => i.user_id === user.id);
        setItems(mine);

        // Fetch matches for user's items
        const matchResults = await Promise.all(
          mine.map(async item => {
            const res = await fetch(`${API_BASE}/api/matches/${item.item_id}`);
            if (!res.ok) return [];
            const data = await res.json();
            return data.map(m => ({ ...m, sourceItem: item }));
          })
        );
        const seen = new Set();
        const deduped = matchResults.flat().filter(m => {
          if (seen.has(m.match_id)) return false;
          seen.add(m.match_id);
          return true;
        });
        setMatches(deduped);
      }
    } catch (e) {
      console.error('Dashboard fetch error:', e);
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { fetchMyData(); }, [fetchMyData]);

  const handleDelete = async (itemId) => {
    if (!window.confirm('Delete this item? This cannot be undone.')) return;
    try {
      setDeleting(itemId);
      const res = await fetch(`${API_BASE}/api/items/${itemId}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': user.id },
      });
      if (res.ok) {
        setItems(prev => prev.filter(i => i.item_id !== itemId));
      }
    } catch (e) {
      console.error('Delete error:', e);
    } finally { setDeleting(null); }
  };

  const lostItems = items.filter(i => i.item_type === 'lost');
  const foundItems = items.filter(i => i.item_type === 'found');
  const matchedCount = items.filter(i => i.status === 'matched').length;
  const successRate = items.length > 0 ? Math.round((matchedCount / items.length) * 100) : 0;

  // Category chart data
  const catCounts = {};
  items.forEach(i => { catCounts[i.category] = (catCounts[i.category] || 0) + 1; });
  const categoryData = Object.entries(catCounts).map(([name, count]) => ({ name, count }));

  // Confidence distribution
  const confBuckets = { '50-60%': 0, '60-70%': 0, '70-80%': 0, '80-90%': 0, '90-100%': 0 };
  matches.forEach(m => {
    const p = m.confidence_score * 100;
    if (p >= 90) confBuckets['90-100%']++;
    else if (p >= 80) confBuckets['80-90%']++;
    else if (p >= 70) confBuckets['70-80%']++;
    else if (p >= 60) confBuckets['60-70%']++;
    else confBuckets['50-60%']++;
  });
  const confData = Object.entries(confBuckets).map(([name, count]) => ({ name, count }));

  if (loading) {
    return (
      <div style={ds.page}>
        <div style={ds.loadingState}><Spinner size={28} /><span style={ds.loadingText}>Loading dashboard...</span></div>
      </div>
    );
  }

  return (
    <div style={ds.page}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* Header */}
      <div style={ds.headerRow}>
        <div>
          <p style={ds.eyebrow}>Dashboard</p>
          <h2 style={ds.pageTitle}>My Items & Matches</h2>
        </div>
        <button onClick={onBack} style={ds.backBtn}>← Back</button>
      </div>

      {/* Stats */}
      <div style={ds.statsGrid}>
        {[
          { label: 'Items Posted', value: items.length, icon: TrendingUp },
          { label: 'Matches', value: matches.length, icon: Search },
          { label: 'Matched', value: matchedCount, icon: Check },
          { label: 'Success Rate', value: `${successRate}%`, icon: BarChart3 },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} style={ds.statCard}>
            <Icon size={16} color="#7a8eaa" strokeWidth={1.5} />
            <span style={ds.statValue}>{value}</span>
            <span style={ds.statLabel}>{label}</span>
          </div>
        ))}
      </div>

      {/* Charts */}
      {(categoryData.length > 0 || matches.length > 0) && (
        <div style={ds.chartsRow}>
          {categoryData.length > 0 && (
            <div style={ds.chartCard}>
              <p style={ds.chartTitle}>Items by Category</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={categoryData} margin={{ top: 5, right: 5, bottom: 5, left: -15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef1f7" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#7a8eaa' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#7a8eaa' }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: '#fff', border: '1px solid #dde3ed', borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {categoryData.map((entry, i) => (
                      <Cell key={i} fill={CATEGORY_COLORS[entry.name] || '#7a8eaa'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          {matches.length > 0 && (
            <div style={ds.chartCard}>
              <p style={ds.chartTitle}>Match Confidence Distribution</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={confData} margin={{ top: 5, right: 5, bottom: 5, left: -15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef1f7" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#7a8eaa' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#7a8eaa' }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: '#fff', border: '1px solid #dde3ed', borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="count" fill="#1a4d33" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Lost Items */}
      <div style={ds.section}>
        <p style={ds.sectionLabel}>My Lost Items ({lostItems.length})</p>
        {lostItems.length === 0 ? (
          <div style={ds.emptyRow}>
            <Search size={18} color="#c2cfe0" strokeWidth={1.5} />
            <span style={ds.emptyText}>No lost items reported yet</span>
          </div>
        ) : (
          <div style={ds.cardGrid}>
            {lostItems.map(item => (
              <DashItemCard key={item.item_id} item={item} onDelete={handleDelete} deleting={deleting} />
            ))}
          </div>
        )}
      </div>

      {/* Found Items */}
      <div style={ds.section}>
        <p style={ds.sectionLabel}>My Found Items ({foundItems.length})</p>
        {foundItems.length === 0 ? (
          <div style={ds.emptyRow}>
            <Camera size={18} color="#c2cfe0" strokeWidth={1.5} />
            <span style={ds.emptyText}>No found items reported yet</span>
          </div>
        ) : (
          <div style={ds.cardGrid}>
            {foundItems.map(item => (
              <DashItemCard key={item.item_id} item={item} onDelete={handleDelete} deleting={deleting} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/* ─── Dashboard Item Card ──────────────────────────────────────────── */
const DashItemCard = ({ item, onDelete, deleting }) => {
  const [imgError, setImgError] = useState(false);
  const imgSrc = item.image_path && !imgError ? item.image_path : null;

  return (
    <div style={ds.itemCard}>
      <div style={ds.itemImageWrap}>
        {imgSrc
          ? <img src={imgSrc} alt={item.title} style={ds.itemImage} onError={() => setImgError(true)} />
          : <div style={ds.itemImagePlaceholder}><Camera size={24} color="#c2cfe0" strokeWidth={1} /></div>}
        <span style={{
          ...ds.statusBadge,
          background: item.status === 'matched' ? '#1a4d33' : '#1e3a5f',
        }}>
          {item.status === 'matched' ? '✓ Matched' : 'Active'}
        </span>
      </div>
      <div style={ds.itemBody}>
        <p style={ds.itemTitle}>{item.title}</p>
        <p style={ds.itemDesc}>{item.description}</p>
        <div style={ds.itemMeta}>
          <span style={ds.metaRow}><MapPin size={11} color="#7a8eaa" strokeWidth={1.5} />{item.location}</span>
          <span style={ds.metaRow}><Clock size={11} color="#7a8eaa" strokeWidth={1.5} />{new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
        </div>
        <button
          onClick={() => onDelete(item.item_id)}
          disabled={deleting === item.item_id}
          style={ds.deleteBtn}
        >
          {deleting === item.item_id
            ? <Spinner size={13} color="#dc2626" />
            : <><Trash2 size={13} color="#dc2626" strokeWidth={1.5} /> Delete</>}
        </button>
      </div>
    </div>
  );
};

/* ─── Dashboard Styles ─────────────────────────────────────────────── */
const ds = {
  page: { paddingTop: 32, animation: 'fadeUp 0.28s ease both' },
  loadingState: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '80px 0' },
  loadingText: { fontSize: 13, color: '#7a8eaa' },
  headerRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 10 },
  eyebrow: { fontSize: 10, fontWeight: 700, color: '#7a8eaa', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 4 },
  pageTitle: { fontFamily: "'DM Serif Display', serif", fontStyle: 'italic', fontSize: 'clamp(22px, 5vw, 32px)', color: '#0f172a', lineHeight: 1.1 },
  backBtn: {
    padding: '8px 16px', background: '#eef1f7', color: '#2d4460',
    borderRadius: 8, fontSize: 12, fontWeight: 600, border: '1px solid #dde3ed',
    cursor: 'pointer', fontFamily: 'inherit',
  },
  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 20 },
  statCard: {
    background: '#fff', border: '1px solid #dde3ed', borderRadius: 11,
    padding: '13px 8px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
  },
  statValue: { fontFamily: "'DM Serif Display', serif", fontSize: 24, color: '#1e3a5f', lineHeight: 1.1 },
  statLabel: { fontSize: 10, color: '#7a8eaa', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em' },
  chartsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12, marginBottom: 20 },
  chartCard: { background: '#fff', border: '1px solid #dde3ed', borderRadius: 13, padding: '18px' },
  chartTitle: { fontSize: 12, fontWeight: 600, color: '#2d4460', marginBottom: 12, letterSpacing: '0.01em' },
  section: { marginBottom: 24 },
  sectionLabel: { fontSize: 10, fontWeight: 700, color: '#7a8eaa', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12 },
  emptyRow: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '24px 20px',
    background: '#fff', border: '1px solid #dde3ed', borderRadius: 11,
  },
  emptyText: { fontSize: 13, color: '#7a8eaa' },
  cardGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 },
  itemCard: { background: '#fff', border: '1px solid #dde3ed', borderRadius: 13, overflow: 'hidden' },
  itemImageWrap: { position: 'relative', height: 140, background: '#eef1f7' },
  itemImage: { width: '100%', height: '100%', objectFit: 'cover' },
  itemImagePlaceholder: { width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  statusBadge: {
    position: 'absolute', top: 8, right: 8,
    fontSize: 10, fontWeight: 700, color: '#fff',
    padding: '3px 8px', borderRadius: 5, letterSpacing: '0.04em',
  },
  itemBody: { padding: '12px 14px' },
  itemTitle: { fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 4 },
  itemDesc: {
    fontSize: 12, color: '#5c718a', lineHeight: 1.5, marginBottom: 8,
    display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
  },
  itemMeta: { display: 'flex', flexDirection: 'column', gap: 3, marginBottom: 10 },
  metaRow: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#7a8eaa' },
  deleteBtn: {
    display: 'flex', alignItems: 'center', gap: 5,
    padding: '6px 12px', borderRadius: 7,
    background: '#fef2f2', border: '1px solid #fecaca',
    fontSize: 11.5, fontWeight: 600, color: '#dc2626',
    cursor: 'pointer', fontFamily: 'inherit',
  },
};

export default DashboardPage;
