import React, { useEffect, useState } from 'react';

const SplashScreen = ({ onFinish }) => {
  const [phase, setPhase] = useState(0); // 0 = hidden, 1 = logo in, 2 = subtitle in, 3 = fade out

  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 100);
    const t2 = setTimeout(() => setPhase(2), 800);
    const t3 = setTimeout(() => setPhase(3), 2000);
    const t4 = setTimeout(() => onFinish(), 2550);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, [onFinish]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: '#f0f2f5',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      opacity: phase === 3 ? 0 : 1,
      transition: 'opacity 0.6s ease',
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&display=swap');
        @keyframes splashLogoIn {
          0%   { opacity: 0; transform: scale(0.7) translateY(12px); }
          100% { opacity: 1; transform: scale(1)   translateY(0); }
        }
        @keyframes splashSubIn {
          0%   { opacity: 0; transform: translateY(8px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes splashDotPulse {
          0%, 100% { opacity: 0.3; transform: scale(0.85); }
          50%      { opacity: 1;   transform: scale(1.1); }
        }
      `}</style>

      {/* Cinematic Inner Wrapper: Zooms towards screen in Phase 3 */}
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        transform: phase === 3 ? 'scale(3.5)' : 'scale(1)',
        opacity: phase === 3 ? 0 : 1,
        transition: 'transform 0.6s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.6s ease',
      }}>
        {/* Logo mark */}
        <div style={{
          width: 56, height: 56, borderRadius: 16,
          background: '#1e3a5f',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 20,
          opacity: phase >= 1 ? 1 : 0,
          transform: phase >= 1 ? 'scale(1)' : 'scale(0.7)',
          transition: 'opacity 0.6s ease, transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
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
          animation: phase >= 1 ? 'splashLogoIn 0.75s cubic-bezier(0.34, 1.56, 0.64, 1) both' : 'none',
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
          animation: phase >= 2 ? 'splashSubIn 0.55s ease both' : 'none',
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
    </div>
  );
};

export default SplashScreen;
