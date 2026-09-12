import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { IconPlus, IconCheck, IconCross } from '../components/Icons';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'officer',
    region: 'Delhi Wing',
  });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  function loadUsers() {
    setLoading(true);
    api.listUsers()
      .then(setUsers)
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleRegister(e) {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    try {
      await api.registerUser(formData);
      setFormSuccess(`User ${formData.email} registered successfully!`);
      setFormData({ email: '', password: '', full_name: '', role: 'officer', region: 'Delhi Wing' });
      setShowModal(false);
      loadUsers();
    } catch (err) {
      setFormError(err.message || 'Registration failed.');
    }
  }

  return (
    <div className="users-page" style={{ padding: '28px 36px' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.85rem', fontWeight: 800, letterSpacing: -0.5 }}>User & Officer Management</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13.5, marginTop: 4 }}>
            Registered enforcement officers, inspectors, and system accounts
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowModal(true)}
          style={{ padding: '9px 18px' }}
        >
          <IconPlus size={15} /> Add Officer / User
        </button>
      </div>

      {formSuccess && (
        <div style={{ padding: 12, borderRadius: 8, background: 'var(--status-pass-bg)', border: '1px solid var(--status-pass-border)', color: '#4ADE80', marginBottom: 16, fontSize: 13.5, display: 'flex', alignItems: 'center', gap: 8 }}>
          <IconCheck size={16} color="#4ADE80" />
          <span>{formSuccess}</span>
        </div>
      )}

      <div style={{ background: 'var(--bg-card)', borderRadius: 14, border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'var(--bg-2)', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6 }}>
              <th style={{ padding: '14px 20px' }}>Name & Email</th>
              <th style={{ padding: '14px 20px' }}>Role</th>
              <th style={{ padding: '14px 20px' }}>Region / Jurisdiction</th>
              <th style={{ padding: '14px 20px' }}>Status</th>
              <th style={{ padding: '14px 20px' }}>Registered On</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div className="spinner" style={{ margin: '0 auto 12px' }} />
                  Loading user accounts...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>No user accounts found</td>
              </tr>
            ) : (
              users.map(u => (
                <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '14px 20px' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.full_name || 'N/A'}</div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{u.email}</div>
                  </td>
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{
                      padding: '3px 10px',
                      borderRadius: 20,
                      fontSize: 11.5,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: 0.4,
                      background: u.role === 'admin' ? 'rgba(21,101,192,0.18)' : 'rgba(0,137,123,0.18)',
                      color: u.role === 'admin' ? '#90CAF9' : '#80CBC4',
                      border: u.role === 'admin' ? '1px solid rgba(21,101,192,0.35)' : '1px solid rgba(0,137,123,0.35)',
                    }}>
                      {u.role}
                    </span>
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: 13.5, color: 'var(--text-secondary)' }}>
                    {u.region || 'National HQ'}
                  </td>
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: 12.5,
                      fontWeight: 600,
                      color: u.is_active ? '#4ADE80' : '#F87171',
                    }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: u.is_active ? '#4ADE80' : '#F87171' }} />
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: 12.5, color: 'var(--text-muted)' }}>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : 'N/A'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 16 }}>
          <div style={{ background: 'var(--bg-card)', padding: 28, borderRadius: 16, width: '100%', maxWidth: 440, border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: 16 }}>Register Officer / User</h2>
            {formError && (
              <div style={{ padding: 10, borderRadius: 6, background: 'var(--status-fail-bg)', border: '1px solid var(--status-fail-border)', color: '#F87171', marginBottom: 14, fontSize: 13 }}>
                {formError}
              </div>
            )}
            
            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="Officer R. K. Singh"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Official Email</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={e => setFormData({ ...formData, email: e.target.value })}
                  placeholder="officer.singh@labelsure.gov.in"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Password</label>
                <input
                  type="password"
                  required
                  value={formData.password}
                  onChange={e => setFormData({ ...formData, password: e.target.value })}
                  placeholder="Minimum 6 characters"
                  className="form-input"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Role</label>
                <select
                  value={formData.role}
                  onChange={e => setFormData({ ...formData, role: e.target.value })}
                  className="filter-select"
                  style={{ width: '100%' }}
                >
                  <option value="officer">Enforcement Officer</option>
                  <option value="admin">Administrator</option>
                  <option value="consumer">Auditor / Consumer</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Region / Zone</label>
                <input
                  type="text"
                  value={formData.region}
                  onChange={e => setFormData({ ...formData, region: e.target.value })}
                  placeholder="e.g. North Zone / Delhi Wing"
                  className="form-input"
                />
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 8, justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                >
                  Create Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
