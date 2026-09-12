import React, { useState, useEffect } from 'react';
import { api, clearToken, getToken } from './services/api';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Users from './pages/Users';
import Settings from './pages/Settings';
import {
  IconDashboard,
  IconAnalytics,
  IconUsers,
  IconSettings,
  IconLogo,
} from './components/Icons';

function Sidebar({ user, activeTab, onTabChange, onLogout }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <IconDashboard size={17} /> },
    { id: 'analytics', label: 'Analytics', icon: <IconAnalytics size={17} /> },
    { id: 'users', label: 'Users', icon: <IconUsers size={17} /> },
    { id: 'settings', label: 'Settings', icon: <IconSettings size={17} /> },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">
          <IconLogo size={22} color="#FFFFFF" />
        </div>
        <div>
          <div className="logo-text">LabelSure</div>
          <div className="logo-sub">Officer Portal</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => onTabChange(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
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

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

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
    setActiveTab('dashboard');
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
      <Sidebar
        user={user}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onLogout={handleLogout}
      />
      <main className="main-content">
        {activeTab === 'dashboard' && <Dashboard user={user} />}
        {activeTab === 'analytics' && <Analytics user={user} />}
        {activeTab === 'users' && <Users user={user} />}
        {activeTab === 'settings' && <Settings user={user} />}
      </main>
    </div>
  );
}
