import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import useStore from '../store/useStore';

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, logout } = useStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const displayName = user?.full_name || user?.email?.split('@')[0] || 'User';

  return (
    <nav style={{
      position: 'sticky',
      top: 0,
      left: 0,
      right: 0,
      background: 'rgba(2, 8, 23, 0.85)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(59, 130, 246, 0.15)',
      zIndex: 50,
      padding: '0 24px',
      height: '64px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      {/* Brand Logo */}
      <Link to={isAuthenticated ? "/dashboard" : "/"} style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none', color: 'inherit' }}>
        <div style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background: 'rgba(59, 130, 246, 0.15)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.2rem',
        }}>
          🛡️
        </div>
        <div>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem', color: '#f1f5f9' }}>
            CyberSaathi
          </span>
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', lineHeight: 1 }}>
            AI Complaint System
          </span>
        </div>
      </Link>

      {/* Center Navigation / Helpline */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {isAuthenticated && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Link
              to="/dashboard"
              style={{
                fontSize: '0.85rem',
                fontWeight: 500,
                color: location.pathname === '/dashboard' ? '#f59e0b' : '#94a3b8',
                textDecoration: 'none',
                padding: '6px 12px',
                borderRadius: '6px',
                background: location.pathname === '/dashboard' ? 'rgba(245, 158, 11, 0.1)' : 'transparent',
                transition: 'color 0.15s ease',
              }}
            >
              Cases
            </Link>
            <Link
              to="/ml-dashboard"
              style={{
                fontSize: '0.85rem',
                fontWeight: 500,
                color: location.pathname === '/ml-dashboard' ? '#f59e0b' : '#94a3b8',
                textDecoration: 'none',
                padding: '6px 12px',
                borderRadius: '6px',
                background: location.pathname === '/ml-dashboard' ? 'rgba(245, 158, 11, 0.1)' : 'transparent',
                transition: 'color 0.15s ease',
              }}
            >
              ML Models
            </Link>
          </div>
        )}

        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 12px',
          borderRadius: '999px',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          fontSize: '0.8rem',
          color: '#f87171',
          fontWeight: 600,
        }}>
          <span>📞 Helpline: 1930</span>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {isAuthenticated ? (
          <>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '4px 10px',
              borderRadius: '6px',
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              fontSize: '0.82rem',
              color: '#cbd5e1',
            }}>
              <span style={{
                width: 22,
                height: 22,
                borderRadius: '50%',
                background: '#f59e0b',
                color: '#020817',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.75rem',
              }}>
                {displayName.charAt(0).toUpperCase()}
              </span>
              <span>{displayName}</span>
            </div>
            <button
              className="btn btn-ghost"
              onClick={handleLogout}
              id="nav-logout-btn"
              style={{ fontSize: '0.82rem', padding: '6px 14px', color: '#94a3b8' }}
            >
              Sign Out
            </button>
          </>
        ) : (
          <>
            <button
              className="btn btn-ghost"
              onClick={() => navigate('/login')}
              id="nav-signin-btn"
              style={{ fontSize: '0.85rem', padding: '6px 16px' }}
            >
              Sign In
            </button>
            <button
              className="btn btn-primary"
              onClick={() => navigate('/register')}
              id="nav-getstarted-btn"
              style={{ fontSize: '0.85rem', padding: '6px 18px' }}
            >
              Get Started →
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
