import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { exportSingleScanPdf } from '../services/pdfExport';
import {
  IconCheck,
  IconCross,
  IconAlert,
  IconInfo,
  IconArrowLeft,
  IconDownload,
  IconChevronUp,
  IconChevronDown,
} from '../components/Icons';

function RuleItem({ rule }) {
  const [expanded, setExpanded] = useState(!rule.passed);
  const isInfo = rule.severity === 'info';
  const icon = isInfo ? (
    <IconInfo size={16} color="#90CAF9" />
  ) : rule.passed ? (
    <IconCheck size={16} color="#4ADE80" />
  ) : (
    <IconCross size={16} color="#F87171" />
  );

  const color = isInfo ? '#90CAF9' : rule.passed ? '#4ADE80' : '#F87171';
  const label = isInfo ? 'INFO' : rule.passed ? 'PASS' : 'FAIL';

  return (
    <div
      className="rule-item"
      style={{ cursor: 'pointer', borderLeft: `3px solid ${color}` }}
      onClick={() => setExpanded(e => !e)}
    >
      <div className="rule-icon">{icon}</div>
      <div style={{ flex: 1 }}>
        <div className="rule-name" style={{ color }}>{rule.rule_name}</div>
        <span style={{ fontSize: 11, fontWeight: 700, color, letterSpacing: 0.5 }}>{label}</span>
        {expanded && rule.explanation && (
          <p className="rule-expl" style={{ marginTop: 6 }}>{rule.explanation}</p>
        )}
      </div>
      <div style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
        {expanded ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
      </div>
    </div>
  );
}

function FieldGrid({ fields }) {
  const nonEmpty = fields.filter(f => f.field_value);
  const names = {
    manufacturer_name: 'Manufacturer',
    manufacturer_address: 'Address',
    generic_name: 'Generic Name',
    net_quantity_value: 'Net Qty',
    net_quantity_unit: 'Unit',
    mrp: 'MRP (₹)',
    manufacture_month: 'Mfg Month',
    manufacture_year: 'Mfg Year',
    measured_font_height_mm: 'Font Height (mm)',
    fssai_license: 'FSSAI License',
    consumer_care: 'Consumer Care',
    batch_number: 'Batch Number',
    expiry_date: 'Expiry / Best Before',
  };

  return (
    <div className="fields-grid">
      {nonEmpty.map(f => (
        <div key={f.field_name} className="field-card">
          <div className="field-label">{names[f.field_name] || f.field_name}</div>
          <div className="field-value">{f.field_value}</div>
        </div>
      ))}
    </div>
  );
}

export default function ScanDetail({ scanId, onBack, user }) {
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getScan(scanId)
      .then(setScan)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [scanId]);

  if (loading) {
    return (
      <div className="page">
        <button className="btn btn-outline" style={{ marginBottom: 20 }} onClick={onBack}>
          <IconArrowLeft size={14} /> Back
        </button>
        <div className="loading-center"><div className="spinner" /></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <button className="btn btn-outline" style={{ marginBottom: 20 }} onClick={onBack}>
          <IconArrowLeft size={14} /> Back
        </button>
        <div className="empty-state">
          <div className="empty-icon"><IconAlert size={36} color="#F87171" /></div>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const v = scan?.verdict || 'UNKNOWN';
  const verdictIcon = v === 'COMPLIANT' ? (
    <IconCheck size={36} color="#4ADE80" />
  ) : v === 'NON_COMPLIANT' ? (
    <IconCross size={36} color="#F87171" />
  ) : (
    <IconAlert size={36} color="#FBBF24" />
  );

  const verdictColor = v === 'COMPLIANT' ? '#4ADE80' : v === 'NON_COMPLIANT' ? '#F87171' : '#FBBF24';
  const passCount = (scan.rule_results || []).filter(r => r.passed).length;
  const totalCount = (scan.rule_results || []).length;
  const formatDate = (d) => d ? new Date(d).toLocaleString('en-IN', { dateStyle: 'long', timeStyle: 'short' }) : '—';

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <button id="back-btn" className="btn btn-outline" onClick={onBack}>
          <IconArrowLeft size={14} /> Back to Dashboard
        </button>
        <button
          id="export-scan-pdf-btn"
          className="btn btn-export"
          onClick={() => exportSingleScanPdf(scan, user)}
          title="Export single scan audit certificate as PDF"
        >
          <IconDownload size={14} /> Export PDF Report
        </button>
      </div>

      <div className="detail-panel">
        <div className="detail-header">
          <div className={`verdict-circle ${v}`}>
            {verdictIcon}
          </div>
          <div>
            <h2 style={{ color: verdictColor, marginBottom: 4 }}>{v.replace('_', ' ')}</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              Scan ID: <code>{scan.id?.substring(0, 8).toUpperCase()}</code>
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>{formatDate(scan.created_at)}</p>
            <p style={{ marginTop: 6, fontSize: 13 }}>
              <span style={{ color: '#4ADE80', fontWeight: 600 }}>{passCount} rules passed</span>
              {' / '}
              <span style={{ color: '#F87171', fontWeight: 600 }}>{totalCount - passCount} failed</span>
            </p>
          </div>
        </div>

        {scan.needs_manual_review && (
          <div style={{ background: 'rgba(217,119,6,0.12)', border: '1px solid rgba(217,119,6,0.35)', borderRadius: 8, padding: '12px 16px', marginBottom: 20, fontSize: 13, color: '#FBBF24', display: 'flex', alignItems: 'center', gap: 10 }}>
            <IconAlert size={18} color="#FBBF24" />
            <span><strong>Manual Review Required:</strong> {scan.review_reason}</span>
          </div>
        )}

        {/* Summary row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px,1fr))', gap: 12, marginBottom: 28 }}>
          <div className="field-card">
            <div className="field-label">OCR Confidence</div>
            <div className="field-value">{scan.overall_confidence != null ? `${(scan.overall_confidence * 100).toFixed(1)}%` : '—'}</div>
          </div>
          <div className="field-card">
            <div className="field-label">Language</div>
            <div className="field-value" style={{ textTransform: 'uppercase', color: 'var(--brand-teal-light)' }}>
              {scan.detected_language || 'en'}
            </div>
          </div>
          <div className="field-card">
            <div className="field-label">Image</div>
            <div className="field-value" style={{ fontSize: 12, wordBreak: 'break-all' }}>{scan.image_filename || '—'}</div>
          </div>
          {scan.entered_sale_price != null && (
            <div className="field-card">
              <div className="field-label">Sale Price</div>
              <div className="field-value">₹{scan.entered_sale_price.toFixed(2)}</div>
            </div>
          )}
        </div>

        {/* Rule checklist */}
        <h3 style={{ marginBottom: 14 }}>Compliance Rules</h3>
        <div className="rule-list">
          {(scan.rule_results || []).map(r => <RuleItem key={r.rule_id} rule={r} />)}
        </div>

        {/* Extracted fields */}
        {(scan.extracted_fields || scan.fields)?.length > 0 && (
          <>
            <h3 style={{ marginTop: 28, marginBottom: 4 }}>Extracted Label Fields</h3>
            <FieldGrid fields={scan.extracted_fields || scan.fields} />
          </>
        )}
      </div>
    </div>
  );
}
