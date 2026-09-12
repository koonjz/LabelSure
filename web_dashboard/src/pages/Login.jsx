import React, { useState } from 'react';
import { api, setToken } from '../services/api';
import { IconLogo, IconAlert } from '../components/Icons';

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
          <div className="logo-icon" style={{ width: 44, height: 44, borderRadius: 12, background: 'linear-gradient(135deg, var(--brand-primary), var(--brand-teal))', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 12px rgba(21,101,192,0.4)' }}>
            <IconLogo size={24} color="#FFFFFF" />
          </div>
          <div>
            <div style={{ fontSize: '1.3rem', fontWeight: 800, letterSpacing: -0.3 }}>LabelSure</div>
            <div style={{ fontSize: 10.5, color: 'var(--brand-teal-light)', fontWeight: 700, letterSpacing: 0.8, textTransform: 'uppercase' }}>OFFICER DASHBOARD</div>
          </div>
        </div>

        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: 20, textAlign: 'center' }}>Sign In</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Official Email</label>
            <input
              id="login-email"
              className="form-input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="officer@labelsure.gov.in"
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
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="form-error" style={{ marginBottom: 12, background: 'var(--status-fail-bg)', border: '1px solid var(--status-fail-border)', padding: '8px 12px', borderRadius: 6 }}>
              <IconAlert size={14} color="#F87171" />
              <span>{error}</span>
            </div>
          )}

          <button
            id="login-submit"
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '11px', marginTop: 8, fontSize: 14.5, justifyContent: 'center' }}
            disabled={loading}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 18, fontSize: 12, color: 'var(--text-muted)' }}>
          Authorized Legal Metrology Officer & Admin Access Only
        </p>
      </div>
    </div>
  );
}
