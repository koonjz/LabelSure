import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { exportCompliancePdf } from '../services/pdfExport';
import ScanDetail from './ScanDetail';
import {
  IconCheck,
  IconCross,
  IconAlert,
  IconRefresh,
  IconDownload,
  IconSearch,
  IconLayers,
} from '../components/Icons';

const VERDICTS = ['COMPLIANT', 'NON_COMPLIANT', 'NEEDS_REVIEW'];

function VerdictBadge({ verdict }) {
  const v = verdict || 'UNKNOWN';
  if (v === 'COMPLIANT') {
    return (
      <span className="verdict-badge COMPLIANT">
        <IconCheck size={12} color="#4ADE80" /> Compliant
      </span>
    );
  }
  if (v === 'NON_COMPLIANT') {
    return (
      <span className="verdict-badge NON_COMPLIANT">
        <IconCross size={12} color="#F87171" /> Non-Compliant
      </span>
    );
  }
  if (v === 'NEEDS_REVIEW') {
    return (
      <span className="verdict-badge NEEDS_REVIEW">
        <IconAlert size={12} color="#FBBF24" /> Needs Review
      </span>
    );
  }
  return <span className="verdict-badge UNKNOWN">{v}</span>;
}

function ConfidenceBar({ value }) {
  if (value == null) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
  const pct = Math.round(value * 100);
  const color = pct >= 85 ? '#4ADE80' : pct >= 70 ? '#FBBF24' : '#F87171';
  return (
    <div className="conf-bar-wrap">
      <div className="conf-bar"><div className="conf-bar-fill" style={{ width: `${pct}%`, background: color }} /></div>
      <span style={{ fontSize: 12, color, fontWeight: 600 }}>{pct}%</span>
    </div>
  );
}

function StatCard({ label, value, color, icon }) {
  return (
    <div className={`stat-card ${color}`}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value ?? '—'}</div>
    </div>
  );
}

export default function Dashboard({ user }) {
  const [scans, setScans] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [verdict, setVerdict] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selectedScanId, setSelectedScanId] = useState(null);
  const [exporting, setExporting] = useState(false);
  const PAGE_SIZE = 20;

  useEffect(() => {
    load();
  }, [verdict, page]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listScans({ verdict: verdict || undefined, page, pageSize: PAGE_SIZE });
      setScans(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleExportPdf() {
    setExporting(true);
    try {
      let scansToExport = filtered;
      if (total > scans.length) {
        try {
          const fullData = await api.listScans({
            verdict: verdict || undefined,
            page: 1,
            pageSize: Math.min(total, 500),
          });
          if (fullData.items?.length) {
            scansToExport = fullData.items.filter(s =>
              !search ||
              (s.image_filename || '').toLowerCase().includes(search.toLowerCase()) ||
              (s.id || '').toLowerCase().includes(search.toLowerCase())
            );
          }
        } catch (fetchErr) {
          console.warn('Could not fetch all scans for PDF, using current page:', fetchErr);
        }
      }

      exportCompliancePdf({
        scans: scansToExport,
        verdictFilter: verdict,
        searchQuery: search,
        user,
        totalCount: total,
      });
    } catch (err) {
      console.error('PDF export failed:', err);
      alert(`Failed to generate PDF: ${err.message || err}`);
    } finally {
      setExporting(false);
    }
  }

  // Stats derived from current page
  const compliantCount = scans.filter(s => s.verdict === 'COMPLIANT').length;
  const nonCompliantCount = scans.filter(s => s.verdict === 'NON_COMPLIANT').length;
  const reviewCount = scans.filter(s => s.needs_manual_review).length;

  // Client-side search filter
  const filtered = scans.filter(s =>
    !search ||
    (s.image_filename || '').toLowerCase().includes(search.toLowerCase()) ||
    (s.id || '').toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const formatDate = (d) => d ? new Date(d).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

  if (selectedScanId) {
    return <ScanDetail scanId={selectedScanId} onBack={() => setSelectedScanId(null)} user={user} />;
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Compliance Dashboard</h1>
        <p>Scan history for all Legal Metrology compliance checks</p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <StatCard label="Total Scans" value={total} color="blue" icon={<IconLayers size={22} color="#90CAF9" />} />
        <StatCard label="Compliant" value={compliantCount} color="green" icon={<IconCheck size={22} color="#4ADE80" />} />
        <StatCard label="Non-Compliant" value={nonCompliantCount} color="red" icon={<IconCross size={22} color="#F87171" />} />
        <StatCard label="Needs Review" value={reviewCount} color="amber" icon={<IconAlert size={22} color="#FBBF24" />} />
      </div>

      {/* Filters */}
      <div className="filters-row">
        <input
          id="search-input"
          className="search-input"
          placeholder="Search by filename or ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          id="verdict-filter"
          className="filter-select"
          value={verdict}
          onChange={e => { setVerdict(e.target.value); setPage(1); }}
        >
          <option value="">All Verdicts</option>
          {VERDICTS.map(v => (
            <option key={v} value={v}>{v.replace('_', ' ')}</option>
          ))}
        </select>
        <button id="refresh-btn" className="btn btn-outline" onClick={() => load()}>
          <IconRefresh size={14} /> Refresh
        </button>
        <button
          id="export-pdf-btn"
          className="btn btn-export"
          onClick={handleExportPdf}
          disabled={exporting || loading || filtered.length === 0}
          title="Export complete compliance report as PDF"
        >
          <IconDownload size={14} /> {exporting ? 'Generating PDF...' : 'Export PDF'}
        </button>
      </div>

      {/* Table */}
      <div className="table-card">
        <div className="table-wrap">
          {loading ? (
            <div className="loading-center"><div className="spinner" /></div>
          ) : error ? (
            <div className="empty-state">
              <div className="empty-icon"><IconAlert size={36} color="#F87171" /></div>
              <p>{error}</p>
              <button className="btn btn-primary" style={{ marginTop: 14 }} onClick={load}>Retry</button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><IconSearch size={36} color="#64748B" /></div>
              <p>No scans found matching current criteria</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Scan ID</th>
                  <th>File / Product</th>
                  <th>Verdict</th>
                  <th>OCR Confidence</th>
                  <th>Language</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(scan => (
                  <tr key={scan.id} onClick={() => setSelectedScanId(scan.id)}>
                    <td style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>
                      {scan.id?.substring(0, 8).toUpperCase()}
                    </td>
                    <td style={{ fontWeight: 500 }}>{scan.image_filename || '—'}</td>
                    <td><VerdictBadge verdict={scan.verdict} /></td>
                    <td><ConfidenceBar value={scan.overall_confidence} /></td>
                    <td style={{ textTransform: 'uppercase', fontSize: 12, color: 'var(--brand-teal-light)', fontWeight: 600 }}>
                      {scan.detected_language || 'en'}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {formatDate(scan.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <div className="pagination">
            <span className="page-info">Showing {((page-1)*PAGE_SIZE)+1}–{Math.min(page*PAGE_SIZE, total)} of {total}</span>
            <button className="page-btn" onClick={() => setPage(p => p - 1)} disabled={page === 1}>‹</button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const p = Math.max(1, page - 2) + i;
              return p <= totalPages ? (
                <button key={p} className={`page-btn ${p === page ? 'active' : ''}`} onClick={() => setPage(p)}>{p}</button>
              ) : null;
            })}
            <button className="page-btn" onClick={() => setPage(p => p + 1)} disabled={page === totalPages}>›</button>
          </div>
        )}
      </div>
    </div>
  );
}
