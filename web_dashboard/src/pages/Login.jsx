import React, { useState } from 'react';
import { api, setToken } from '../services/api';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await api.login(email, password);
      setToken(data.access_token);
      onLogin(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div className="logo-icon" style={{ width: 48, height: 48, borderRadius: 14, background: 'linear-gradient(135deg,#3B82F6,#8B5CF6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24 }}>
            🔍
          </div>
          <div>
            <div style={{ fontSize: '1.3rem', fontWeight: 800 }}>LabelSure</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: 1 }}>OFFICER DASHBOARD</div>
          </div>
        </div>
        <h2>Sign In</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              id="login-email"
              className="form-input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="officer@dept.gov.in"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              id="login-password"
              className="form-input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          {error && <div className="form-error" style={{ marginBottom: 12 }}>⚠ {error}</div>}
          <button
            id="login-submit"
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '12px', marginTop: 8, fontSize: 15, justifyContent: 'center' }}
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
          Officer / Admin access only. Contact your administrator to register.
        </p>
      </div>
    </div>
  );
}
