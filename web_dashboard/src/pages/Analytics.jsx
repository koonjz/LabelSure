import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

const DEFAULT_RULE_COUNTS = {
  'Rule 6(1)(a) Name & Address': 0,
  'Rule 6(1) Generic Name': 0,
  'Rule 6(1) Net Quantity & Font Height': 0,
  'Rule 6(1) MRP Inclusive of Taxes': 0,
  'Rule 6(1) Month & Year of Mfg/Pkg': 0,
  'Rule 18(2) Dual Pricing Check': 0,
};

export default function Analytics() {
  const [data, setData] = useState({
    total_scans: 0,
    compliant_count: 0,
    non_compliant_count: 0,
    needs_review_count: 0,
    compliance_rate: 100.0,
    rule_counts: DEFAULT_RULE_COUNTS,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  async function loadAnalytics() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAnalytics();
      setData({
        total_scans: res.total_scans ?? 0,
        compliant_count: res.compliant_count ?? 0,
        non_compliant_count: res.non_compliant_count ?? 0,
        needs_review_count: res.needs_review_count ?? 0,
        compliance_rate: res.compliance_rate ?? (res.total_scans > 0 ? ((res.compliant_count / res.total_scans) * 100).toFixed(1) : 100.0),
        rule_counts: res.rule_counts || DEFAULT_RULE_COUNTS,
      });
    } catch (err) {
      console.warn('getAnalytics failed, falling back to listScans:', err);
      // Fallback: list scans
      try {
        const scanRes = await api.listScans({ pageSize: 100 });
        const scans = scanRes.items || [];
        const total = scans.length;
        const compliant = scans.filter(s => s.verdict === 'COMPLIANT').length;
        const nonCompliant = scans.filter(s => s.verdict === 'NON_COMPLIANT').length;
        const needsReview = scans.filter(s => s.verdict === 'NEEDS_REVIEW' || s.needs_manual_review).length;
        const rate = total > 0 ? ((compliant / total) * 100).toFixed(1) : '100.0';

        setData({
          total_scans: scanRes.total || total,
          compliant_count: compliant,
          non_compliant_count: nonCompliant,
          needs_review_count: needsReview,
          compliance_rate: rate,
          rule_counts: DEFAULT_RULE_COUNTS,
        });
      } catch (fallbackErr) {
        setError(fallbackErr.message || err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  const {
    total_scans: total,
    compliant_count: compliant,
    non_compliant_count: nonCompliant,
    needs_review_count: needsReview,
    compliance_rate: complianceRate,
    rule_counts: ruleCounts,
  } = data;

  const totalViolations = Object.values(ruleCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="analytics-page" style={{ padding: '24px 32px' }}>
      <div className="page-header" style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, letterSpacing: -0.5 }}>Legal Metrology Compliance Analytics</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Aggregated compliance statistics and statutory rule enforcement metrics</p>
        </div>
        <button
          className="btn btn-outline"
          onClick={loadAnalytics}
          disabled={loading}
          style={{ fontSize: 13 }}
        >
          {loading ? '⟳ Refreshing...' : '⟳ Refresh'}
        </button>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 24, color: '#EF4444', fontSize: 13 }}>
          ⚠️ {error}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 600, letterSpacing: 0.5 }}>COMPLIANCE RATE</div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#22C55E', marginTop: 6 }}>{complianceRate}%</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Of scanned packages pass PCR 2011</div>
        </div>

        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 600, letterSpacing: 0.5 }}>TOTAL SCANS EXAMINED</div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: 6 }}>{total}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Across all enforcement zones</div>
        </div>

        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 600, letterSpacing: 0.5 }}>NON-COMPLIANT LABELS</div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#EF4444', marginTop: 6 }}>{nonCompliant}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Flagged for statutory enforcement</div>
        </div>

        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 600, letterSpacing: 0.5 }}>FLAGGED FOR MANUAL REVIEW</div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#F59E0B', marginTop: 6 }}>{needsReview}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Low OCR confidence or partial text</div>
        </div>
      </div>

      {/* Violations Breakdown */}
      <div style={{ background: 'var(--bg-card)', padding: 24, borderRadius: 16, border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Violations Breakdown by Legal Provision</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
              Legal Metrology (Packaged Commodities) Rules, 2011 statutory provisions
            </p>
          </div>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'rgba(255,255,255,0.05)', padding: '4px 10px', borderRadius: 6 }}>
            {totalViolations} Total Violation{totalViolations !== 1 ? 's' : ''}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {Object.entries(ruleCounts).map(([ruleName, count]) => {
            const baseTotal = totalViolations > 0 ? totalViolations : Math.max(1, total);
            const percentage = Math.round((count / baseTotal) * 100);

            return (
              <div key={ruleName}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 14 }}>
                  <span style={{ fontWeight: 600, color: count > 0 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                    {ruleName}
                  </span>
                  <span style={{ color: count > 0 ? (count > 2 ? '#EF4444' : '#F59E0B') : 'var(--text-muted)', fontWeight: count > 0 ? 600 : 400 }}>
                    {count} violation{count !== 1 ? 's' : ''} ({percentage}%)
                  </span>
                </div>
                <div style={{ height: 10, background: 'rgba(255,255,255,0.06)', borderRadius: 5, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${count > 0 ? Math.max(percentage, 6) : 0}%`,
                      background: count > 0 ? 'linear-gradient(90deg, #F59E0B, #EF4444)' : 'transparent',
                      borderRadius: 5,
                      transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

