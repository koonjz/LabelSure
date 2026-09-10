import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { api, clearToken, getToken } from './services/api';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

function Sidebar({ user, onLogout }) {
  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">🔍</div>
        <div>
          <div className="logo-text">LabelSure</div>
          <div className="logo-sub">Officer Portal</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        <a className="nav-item active" href="#">
          <span className="nav-icon">📊</span>
          <span>Dashboard</span>
        </a>
        <a className="nav-item" href="#" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
          <span className="nav-icon">📈</span>
          <span>Analytics</span>
        </a>
        <a className="nav-item" href="#" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
          <span className="nav-icon">👥</span>
          <span>Users</span>
        </a>
        <a className="nav-item" href="#" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
          <span className="nav-icon">⚙️</span>
          <span>Settings</span>
        </a>
      </nav>
      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">
            {(user?.full_name || user?.email || 'O').charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="user-name">{user?.full_name || user?.email}</div>
            <div className="user-role">{user?.role?.charAt(0).toUpperCase() + user?.role?.slice(1)}</div>
          </div>
        </div>
        <button id="logout-btn" className="logout-btn" onClick={onLogout}>Sign Out</button>
      </div>
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (getToken()) {
      api.getMe()
        .then(setUser)
        .catch(() => { clearToken(); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  function handleLogin(u) {
    setUser(u);
  }

  function handleLogout() {
    clearToken();
    setUser(null);
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app-layout">
      <Sidebar user={user} onLogout={handleLogout} />
      <main className="main-content">
        <Dashboard user={user} />
      </main>
    </div>
  );
}

export default App;
