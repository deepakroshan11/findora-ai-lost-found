import React, { useState } from 'react';
import { useAuth } from './AuthContext';
import { Search, Mail, Lock, User, Eye, EyeOff, AlertCircle } from 'lucide-react';

const AuthPage = ({ onSignupComplete }) => {
  const { signInWithEmail, signUpWithEmail, signInWithGoogle, continueAsGuest } = useAuth();
  const [mode, setMode] = useState('signin'); // 'signin' | 'signup'
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  const update = (k, v) => { setForm(f => ({ ...f, [k]: v })); setError(''); };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');

    if (!form.email.trim() || !form.password.trim()) {
      setError('Email and password are required'); return;
    }
    if (mode === 'signup' && !form.name.trim()) {
      setError('Name is required'); return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters'); return;
    }

    try {
      setLoading(true);
      if (mode === 'signin') {
        await signInWithEmail(form.email.trim(), form.password);
      } else {
        await signUpWithEmail(form.email.trim(), form.password, form.name.trim());
        setSuccess('Account created! Check your email to confirm, then sign in.');
        if (onSignupComplete) onSignupComplete();
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    try {
      setError('');
      await signInWithGoogle();
    } catch (err) {
      setError(err.message || 'Google sign-in failed');
    }
  };

  return (
    <div style={st.root}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #f0f2f5 !important; }
        @keyframes authFadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        input::placeholder { color: #9aafc4 !important; }
        input:focus { border-color: #1e3a5f !important; box-shadow: 0 0 0 3px rgba(30,58,95,0.1); outline: none; }
      `}</style>

      <div style={st.card}>
        {/* Header */}
        <div style={st.header}>
          <div style={st.logoRow}>
            <div style={st.logoMark}>
              <Search size={16} color="#ffffff" strokeWidth={2} />
            </div>
            <div>
              <p style={st.logoName}>Findora</p>
              <p style={st.logoTag}>AI Lost &amp; Found</p>
            </div>
          </div>
        </div>

        {/* Title */}
        <div style={st.body}>
          <h2 style={st.title}>{mode === 'signin' ? 'Welcome back' : 'Create an account'}</h2>
          <p style={st.subtitle}>
            {mode === 'signin'
              ? 'Sign in to manage your items and view matches.'
              : 'Get started with AI-powered lost & found matching.'}
          </p>

          {/* Google OAuth */}
          <button onClick={handleGoogle} style={st.googleBtn} type="button">
            <svg width="18" height="18" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            <span>Continue with Google</span>
          </button>

          {/* Divider */}
          <div style={st.divider}>
            <div style={st.dividerLine} />
            <span style={st.dividerText}>or</span>
            <div style={st.dividerLine} />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} style={st.form}>
            {mode === 'signup' && (
              <div style={st.fieldWrap}>
                <User size={16} color="#9aafc4" style={st.fieldIcon} />
                <input
                  type="text" placeholder="Full name" value={form.name}
                  onChange={e => update('name', e.target.value)}
                  style={st.input}
                />
              </div>
            )}
            <div style={st.fieldWrap}>
              <Mail size={16} color="#9aafc4" style={st.fieldIcon} />
              <input
                type="email" placeholder="Email address" value={form.email}
                onChange={e => update('email', e.target.value)}
                style={st.input} autoComplete="email"
              />
            </div>
            <div style={st.fieldWrap}>
              <Lock size={16} color="#9aafc4" style={st.fieldIcon} />
              <input
                type={showPwd ? 'text' : 'password'} placeholder="Password"
                value={form.password}
                onChange={e => update('password', e.target.value)}
                style={{ ...st.input, paddingRight: 42 }} autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
              />
              <button type="button" onClick={() => setShowPwd(!showPwd)} style={st.eyeBtn}>
                {showPwd ? <EyeOff size={16} color="#9aafc4" /> : <Eye size={16} color="#9aafc4" />}
              </button>
            </div>

            {error && (
              <div style={st.error}>
                <AlertCircle size={14} /> {error}
              </div>
            )}
            {success && (
              <div style={st.success}>{success}</div>
            )}

            <button type="submit" disabled={loading} style={{ ...st.submitBtn, opacity: loading ? 0.65 : 1 }}>
              {loading ? (
                <div style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
              ) : (
                mode === 'signin' ? 'Sign In' : 'Create Account'
              )}
            </button>
          </form>

          {/* Toggle */}
          <p style={st.toggle}>
            {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(''); setSuccess(''); }}
              style={st.toggleLink}
            >
              {mode === 'signin' ? 'Sign up' : 'Sign in'}
            </button>
          </p>

          {/* Guest */}
          <button type="button" onClick={continueAsGuest} style={st.guestLink}>
            Continue as guest →
          </button>
        </div>
      </div>

      {/* Footer */}
      <p style={st.footer}>© {new Date().getFullYear()} Findora — AI Lost &amp; Found</p>
    </div>
  );
};

/* ─── Styles ─────────────────────────────────────────────────────── */
const st = {
  root: {
    fontFamily: "'DM Sans', system-ui, sans-serif",
    minHeight: '100vh', background: '#f0f2f5',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    padding: '40px 20px',
  },
  card: {
    width: '100%', maxWidth: 420,
    background: '#ffffff', borderRadius: 16,
    border: '1px solid #dde3ed',
    overflow: 'hidden',
    animation: 'authFadeUp 0.5s ease both',
  },
  header: {
    background: '#1e3a5f', padding: '22px 28px',
  },
  logoRow: { display: 'flex', alignItems: 'center', gap: 10 },
  logoMark: {
    width: 36, height: 36, borderRadius: 10,
    background: 'rgba(255,255,255,0.15)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  logoName: {
    fontFamily: "'DM Serif Display', serif", fontStyle: 'italic',
    fontSize: 18, color: '#ffffff', lineHeight: 1.1,
  },
  logoTag: { fontSize: 9, color: 'rgba(255,255,255,0.55)', letterSpacing: '0.1em', textTransform: 'uppercase' },
  body: { padding: '28px 28px 24px' },
  title: {
    fontFamily: "'DM Serif Display', serif", fontStyle: 'italic',
    fontSize: 24, color: '#0f172a', marginBottom: 6,
  },
  subtitle: { fontSize: 13, color: '#5c718a', lineHeight: 1.6, marginBottom: 22 },
  googleBtn: {
    width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
    padding: '11px 16px', borderRadius: 10,
    background: '#ffffff', border: '1.5px solid #dde3ed',
    fontSize: 13.5, fontWeight: 500, color: '#2d4460',
    cursor: 'pointer', fontFamily: 'inherit',
    transition: 'background 0.15s, border-color 0.15s',
  },
  divider: { display: 'flex', alignItems: 'center', gap: 14, margin: '20px 0' },
  dividerLine: { flex: 1, height: 1, background: '#eef1f7' },
  dividerText: { fontSize: 12, color: '#9aafc4', fontWeight: 500 },
  form: { display: 'flex', flexDirection: 'column', gap: 12 },
  fieldWrap: { position: 'relative' },
  fieldIcon: { position: 'absolute', left: 13, top: '50%', transform: 'translateY(-50%)' },
  input: {
    width: '100%', padding: '11px 13px 11px 38px',
    border: '1px solid #dde3ed', borderRadius: 9,
    fontSize: 13.5, color: '#0f172a', background: '#ffffff',
    fontFamily: 'inherit', transition: 'border 0.15s, box-shadow 0.15s', outline: 'none',
  },
  eyeBtn: {
    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
    background: 'none', border: 'none', cursor: 'pointer', padding: 4,
  },
  error: {
    display: 'flex', alignItems: 'center', gap: 6,
    fontSize: 12.5, color: '#dc2626', fontWeight: 500,
    background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8,
    padding: '9px 12px',
  },
  success: {
    fontSize: 12.5, color: '#166534', fontWeight: 500,
    background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8,
    padding: '9px 12px',
  },
  submitBtn: {
    width: '100%', padding: '12px',
    background: '#1e3a5f', color: '#ffffff', borderRadius: 10,
    fontSize: 14, fontWeight: 600, border: 'none', cursor: 'pointer',
    fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'opacity 0.15s',
    marginTop: 4,
  },
  toggle: {
    textAlign: 'center', fontSize: 13, color: '#5c718a', marginTop: 18,
  },
  toggleLink: {
    background: 'none', border: 'none', color: '#1e3a5f',
    fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', fontSize: 13,
    textDecoration: 'underline',
  },
  guestLink: {
    display: 'block', width: '100%', textAlign: 'center',
    fontSize: 12.5, color: '#7a8eaa', fontWeight: 500,
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'inherit', marginTop: 14,
    transition: 'color 0.15s',
  },
  footer: {
    fontSize: 11, color: '#9aafc4', marginTop: 28, textAlign: 'center',
  },
};

export default AuthPage;
