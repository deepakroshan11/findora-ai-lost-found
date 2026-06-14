import React, { useEffect, useState } from 'react';

const SplashScreen = ({ onFinish }) => {
  const [phase, setPhase] = useState(0); // 0 = hidden, 1 = logo in, 2 = subtitle in, 3 = fade out

  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 100);
    const t2 = setTimeout(() => setPhase(2), 900);
    const t3 = setTimeout(() => setPhase(3), 2400);
    const t4 = setTimeout(() => onFinish(), 2900);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, [onFinish]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: '#f0f2f5',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      opacity: phase === 3 ? 0 : 1,
      transition: 'opacity 0.5s ease',
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&display=swap');
        @keyframes splashLogoIn {
          0%   { opacity: 0; transform: scale(0.2); filter: blur(15px); letter-spacing: 0.25em; }
          75%  { opacity: 0.9; transform: scale(1.08); filter: blur(2px); }
          100% { opacity: 1; transform: scale(1); filter: blur(0); letter-spacing: -0.03em; }
        }
        @keyframes splashMarkIn {
          0%   { opacity: 0; transform: scale(0.2); filter: blur(10px); }
          75%  { opacity: 0.9; transform: scale(1.1); filter: blur(2px); }
          100% { opacity: 1; transform: scale(1); filter: blur(0); }
        }
        @keyframes splashSubIn {
          0%   { opacity: 0; transform: translateY(12px); filter: blur(4px); }
          100% { opacity: 1; transform: translateY(0); filter: blur(0); }
        }
        @keyframes splashDotPulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50%      { opacity: 1;   transform: scale(1.15); }
        }
      `}</style>

      {/* Logo mark */}
      <div style={{
        width: 56, height: 56, borderRadius: 16,
        background: '#1e3a5f',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 20,
        animation: phase >= 1 ? 'splashMarkIn 1.3s cubic-bezier(0.19, 1, 0.22, 1) both' : 'none',
        opacity: phase >= 1 ? undefined : 0,
      }}>
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </div>

      {/* Title */}
      <h1 style={{
        fontFamily: "'DM Serif Display', serif",
        fontStyle: 'italic',
        fontSize: 'clamp(48px, 12vw, 72px)',
        color: '#0f172a',
        letterSpacing: '-0.03em',
        lineHeight: 1,
        marginBottom: 10,
        animation: phase >= 1 ? 'splashLogoIn 1.4s cubic-bezier(0.19, 1, 0.22, 1) both' : 'none',
        opacity: phase >= 1 ? undefined : 0,
      }}>
        Findora
      </h1>

      {/* Subtitle */}
      <p style={{
        fontSize: 14,
        color: '#7a8eaa',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        fontWeight: 500,
        animation: phase >= 2 ? 'splashSubIn 0.8s cubic-bezier(0.19, 1, 0.22, 1) both' : 'none',
        opacity: phase >= 2 ? undefined : 0,
      }}>
        AI-Powered Lost &amp; Found
      </p>

      {/* Loading dots */}
      <div style={{
        display: 'flex', gap: 6, marginTop: 32,
        opacity: phase >= 2 ? 1 : 0,
        transition: 'opacity 0.4s ease',
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 6, height: 6, borderRadius: '50%',
            background: '#1e3a5f',
            animation: `splashDotPulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
};

export default SplashScreen;
