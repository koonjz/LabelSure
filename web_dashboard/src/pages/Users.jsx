import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

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
    <div className="users-page" style={{ padding: '24px' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>User & Officer Management</h1>
          <p style={{ color: 'var(--text-muted)' }}>Registered enforcement officers, inspectors, and seller accounts</p>
        </div>
        <button
          className="action-btn primary"
          onClick={() => setShowModal(true)}
          style={{ background: '#3B82F6', color: '#fff', padding: '10px 18px', borderRadius: 8, border: 'none', fontWeight: 600, cursor: 'pointer' }}
        >
          + Add New Officer / User
        </button>
      </div>

      {formSuccess && (
        <div style={{ padding: 12, borderRadius: 8, background: 'rgba(16,185,129,0.15)', border: '1px solid #10B981', color: '#10B981', marginBottom: 16 }}>
          {formSuccess}
        </div>
      )}

      <div style={{ background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--border)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: 12, textTransform: 'uppercase' }}>
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
                <td colSpan={5} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>Loading user accounts...</td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>No user accounts found</td>
              </tr>
            ) : (
              users.map(u => (
                <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '16px 20px' }}>
                    <div style={{ fontWeight: 600 }}>{u.full_name || 'N/A'}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{u.email}</div>
                  </td>
                  <td style={{ padding: '16px 20px' }}>
                    <span style={{
                      padding: '4px 10px',
                      borderRadius: 20,
                      fontSize: 12,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      background: u.role === 'officer' || u.role === 'admin' ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.1)',
                      color: u.role === 'officer' || u.role === 'admin' ? '#60A5FA' : '#9CA3AF',
                      border: u.role === 'officer' || u.role === 'admin' ? '1px solid rgba(59,130,246,0.3)' : '1px solid rgba(255,255,255,0.1)',
                    }}>
                      {u.role}
                    </span>
                  </td>
                  <td style={{ padding: '16px 20px', fontSize: 14 }}>{u.region || 'National HQ'}</td>
                  <td style={{ padding: '16px 20px' }}>
                    <span style={{ color: u.is_active ? '#10B981' : '#EF4444', fontSize: 13, fontWeight: 600 }}>
                      ● {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-muted)' }}>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 16 }}>
          <div style={{ background: '#1E293B', padding: 28, borderRadius: 16, width: '100%', maxWidth: 460, border: '1px solid var(--border)' }}>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 16 }}>Register Officer / User</h2>
            {formError && <div style={{ padding: 10, borderRadius: 6, background: 'rgba(239,68,68,0.2)', border: '1px solid #EF4444', color: '#EF4444', marginBottom: 14, fontSize: 13 }}>{formError}</div>}
            
            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="Officer R. K. Singh"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#0F172A', border: '1px solid var(--border)', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>Official Email</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={e => setFormData({ ...formData, email: e.target.value })}
                  placeholder="officer.singh@labelsure.gov.in"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#0F172A', border: '1px solid var(--border)', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>Password</label>
                <input
                  type="password"
                  required
                  value={formData.password}
                  onChange={e => setFormData({ ...formData, password: e.target.value })}
                  placeholder="At least 6 characters"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#0F172A', border: '1px solid var(--border)', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>Role</label>
                <select
                  value={formData.role}
                  onChange={e => setFormData({ ...formData, role: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#0F172A', border: '1px solid var(--border)', color: '#fff' }}
                >
                  <option value="officer">Enforcement Officer</option>
                  <option value="admin">Administrator</option>
                  <option value="seller">Manufacturer / Seller</option>
                  <option value="consumer">Consumer Auditor</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>Region / Zone</label>
                <input
                  type="text"
                  value={formData.region}
                  onChange={e => setFormData({ ...formData, region: e.target.value })}
                  placeholder="e.g. North Zone / Delhi"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: '#0F172A', border: '1px solid var(--border)', color: '#fff' }}
                />
              </div>

              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 12 }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  style={{ padding: '10px 16px', borderRadius: 8, background: 'transparent', border: '1px solid var(--border)', color: '#fff', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '10px 18px', borderRadius: 8, background: '#3B82F6', border: 'none', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
                >
                  Save User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
