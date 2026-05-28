import React from 'react';
import useTheme from '../hooks/useTheme';

// Sun Icon
const SunIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5"></circle>
    <line x1="12" y1="1" x2="12" y2="3"></line>
    <line x1="12" y1="21" x2="12" y2="23"></line>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
    <line x1="1" y1="12" x2="3" y2="12"></line>
    <line x1="21" y1="12" x2="23" y2="12"></line>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
  </svg>
);

// Moon Icon
const MoonIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
  </svg>
);

export default function ThemeToggle() {
  const { theme, toggleTheme, isDark, mounted } = useTheme();

  // Prevent hydration mismatch
  if (!mounted) {
    return (
      <div style={{
        width: '44px',
        height: '44px',
        borderRadius: '12px',
        background: 'var(--bg-glass)',
        border: '1px solid var(--border-color)',
      }} />
    );
  }

  return (
    <button
      onClick={toggleTheme}
      title={isDark ? 'Переключить на светлую тему' : 'Переключить на темную тему'}
      style={{
        width: '44px',
        height: '44px',
        borderRadius: '12px',
        background: isDark ? 'var(--bg-glass)' : 'var(--accent-gradient-subtle)',
        border: '1px solid var(--border-color)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: isDark ? 'var(--text-secondary)' : 'var(--accent-primary)',
        transition: 'all 0.3s ease',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-glass-hover)';
        e.currentTarget.style.transform = 'scale(1.05)';
        e.currentTarget.style.borderColor = 'var(--border-color-hover)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = isDark ? 'var(--bg-glass)' : 'var(--accent-gradient-subtle)';
        e.currentTarget.style.transform = 'scale(1)';
        e.currentTarget.style.borderColor = 'var(--border-color)';
      }}
    >
      <div style={{
        animation: 'rotateIn 0.3s ease',
      }}>
        {isDark ? <SunIcon /> : <MoonIcon />}
      </div>
      
      {/* Glow effect for light theme */}
      {!isDark && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'var(--accent-gradient)',
          opacity: 0,
          transition: 'opacity 0.3s ease',
          borderRadius: '12px',
        }} className="theme-glow" />
      )}
    </button>
  );
}