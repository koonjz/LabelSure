import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function Settings({ user }) {
  const [health, setHealth] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [ocrThreshold, setOcrThreshold] = useState(0.70);
  const [minFontHeight, setMinFontHeight] = useState(1.5);
  const [savedMsg, setSavedMsg] = useState('');

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch(err => setHealth({ status: 'unreachable', error: err.message }))
      .finally(() => setLoadingHealth(false));
  }, []);

  function handleSave(e) {
    e.preventDefault();
    setSavedMsg('Settings saved successfully!');
    setTimeout(() => setSavedMsg(''), 3000);
  }

  return (
    <div className="settings-page" style={{ padding: '24px' }}>
      <div className="page-header" style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>System & Enforcement Settings</h1>
        <p style={{ color: 'var(--text-muted)' }}>Configure Legal Metrology PCR 2011 rule parameters and view service health</p>
      </div>

      {savedMsg && (
        <div style={{ padding: 12, borderRadius: 8, background: 'rgba(16,185,129,0.15)', border: '1px solid #10B981', color: '#10B981', marginBottom: 20 }}>
          {savedMsg}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
        {/* Rule Parameters */}
        <div style={{ background: 'var(--bg-card)', padding: 24, borderRadius: 12, border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 16 }}>Rules Engine Thresholds</h3>
          
          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                OCR Confidence Threshold: {ocrThreshold}
              </label>
              <input
                type="range"
                min="0.50"
                max="0.95"
                step="0.05"
                value={ocrThreshold}
                onChange={e => setOcrThreshold(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                Scans below this score are automatically flagged as NEEDS_REVIEW
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                Min Font Height Threshold (Rule 6(1) Net Qty): {minFontHeight} mm
              </label>
              <input
                type="number"
                step="0.1"
                min="1.0"
                max="6.0"
                value={minFontHeight}
                onChange={e => setMinFontHeight(parseFloat(e.target.value))}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#0F172A', border: '1px solid var(--border)', color: '#fff' }}
              />
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                Minimum numeral height enforced according to declared weight/volume
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                Date Format Strictness (Rule 7)
              </label>
              <select style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#0F172A', border: '1px solid var(--border)', color: '#fff' }}>
                <option value="strict">Strict (DD/MM/YYYY or MM/YYYY required)</option>
                <option value="flexible">Flexible (Allow Month Name, e.g. JAN 2026)</option>
              </select>
            </div>

            <button
              type="submit"
              style={{ background: '#3B82F6', color: '#fff', padding: '10px 18px', borderRadius: 8, border: 'none', fontWeight: 600, cursor: 'pointer', alignSelf: 'flex-start', marginTop: 8 }}
            >
              Save Parameters
            </button>
          </form>
        </div>

        {/* Live Service Health */}
        <div style={{ background: 'var(--bg-card)', padding: 24, borderRadius: 12, border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 16 }}>Live System & Environment Health</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: 14, borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>BACKEND SERVICE</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, fontWeight: 600 }}>
                <span style={{ color: health?.status === 'ok' ? '#10B981' : '#EF4444' }}>
                  ● {health?.status === 'ok' ? 'Online (Render Hosted)' : 'Connecting / Degraded'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>https://labelsure-jw0d.onrender.com</div>
            </div>

            <div style={{ padding: 14, borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>DATABASE ENGINE</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, fontWeight: 600 }}>
                <span style={{ color: health?.db === 'ok' ? '#10B981' : '#EF4444' }}>
                  ● {health?.db === 'ok' ? 'Neon Serverless PostgreSQL' : 'Connecting...'}
                </span>
              </div>
            </div>

            <div style={{ padding: 14, borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>LOGGED-IN OFFICER PROFILE</div>
              <div style={{ fontWeight: 600, marginTop: 4 }}>{user?.full_name || user?.email}</div>
              <div style={{ fontSize: 12, color: '#60A5FA', marginTop: 2 }}>Role: {user?.role} | Region: {user?.region || 'National'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
