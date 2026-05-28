import React from "react";
import { Link, useLocation } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

// SVG Icons as components
const Icons = {
  Team: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
      <circle cx="9" cy="7" r="4"></circle>
      <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
    </svg>
  ),
  Chart: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"></line>
      <line x1="12" y1="20" x2="12" y2="4"></line>
      <line x1="6" y1="20" x2="6" y2="14"></line>
    </svg>
  ),
  Heatmap: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7"></rect>
      <rect x="14" y="3" width="7" height="7"></rect>
      <rect x="14" y="14" width="7" height="7"></rect>
      <rect x="3" y="14" width="7" height="7"></rect>
    </svg>
  ),
  Calendar: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
      <line x1="16" y1="2" x2="16" y2="6"></line>
      <line x1="8" y1="2" x2="8" y2="6"></line>
      <line x1="3" y1="10" x2="21" y2="10"></line>
    </svg>
  ),
};

export default function Sidebar() {
  const location = useLocation();

  const links = [
    { path: "/", label: "Команда на неделю", icon: Icons.Team },
    { path: "/dynamics", label: "Динамика по сотрудникам", icon: Icons.Chart },
    { path: "/clients", label: "Клиентская тепловая карта", icon: Icons.Heatmap },
    { path: "/vacations", label: "Календарь отпусков", icon: Icons.Calendar },
  ];

  return (
    <nav className="sidebar">
      <h1 className="sidebar-title">VITA Опрос</h1>
      <ul className="sidebar-nav">
        {links.map((l, index) => {
          const Icon = l.icon;
          const isActive = location.pathname === l.path;
          return (
            <li 
              key={l.path} 
              className={isActive ? "active" : ""}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <Link to={l.path}>
                <span className="nav-icon">
                  <Icon />
                </span>
                <span>{l.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      
      {/* Bottom section with theme toggle */}
      <div style={{ 
        marginTop: 'auto', 
        padding: '20px 0',
        borderTop: '1px solid var(--border-color)',
      }}>
        {/* Theme Toggle */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '16px',
        }}>
          <span style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            fontWeight: 500,
          }}>
            Тема интерфейса
          </span>
          <ThemeToggle />
        </div>
        
        {/* Status indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontSize: '12px',
          color: 'var(--text-muted)',
          opacity: 0.8,
        }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: 'var(--score-high)',
            animation: 'pulse 2s ease-in-out infinite',
            boxShadow: '0 0 8px var(--score-high)',
          }} />
          <span>Система активна</span>
        </div>
      </div>
    </nav>
  );
}