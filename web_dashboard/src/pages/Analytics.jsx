import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function Analytics() {
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listScans({ pageSize: 100 })
      .then(res => setScans(res.items || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const total = scans.length;
  const compliant = scans.filter(s => s.verdict === 'COMPLIANT').length;
  const nonCompliant = scans.filter(s => s.verdict === 'NON_COMPLIANT').length;
  const needsReview = scans.filter(s => s.verdict === 'NEEDS_REVIEW').length;
  const complianceRate = total > 0 ? ((compliant / total) * 100).toFixed(1) : '100.0';

  // Rule violation distribution
  const ruleCounts = {
    'Rule 6(1)(a) Name & Address': 0,
    'Rule 6(1) Generic Name': 0,
    'Rule 6(1) Net Quantity & Font Height': 0,
    'Rule 6(1) MRP Inclusive of Taxes': 0,
    'Rule 6(1) Month & Year of Mfg/Pkg': 0,
    'Rule 18(2) Dual Pricing Check': 0,
  };

  scans.forEach(s => {
    (s.violations || []).forEach(v => {
      const code = v.rule_code || '';
      if (code.includes('6_1_A') || code.includes('6(1)(a)')) ruleCounts['Rule 6(1)(a) Name & Address']++;
      else if (code.includes('6_1_GENERIC')) ruleCounts['Rule 6(1) Generic Name']++;
      else if (code.includes('6_1_NET') || code.includes('6_1_FONT')) ruleCounts['Rule 6(1) Net Quantity & Font Height']++;
      else if (code.includes('6_1_MRP')) ruleCounts['Rule 6(1) MRP Inclusive of Taxes']++;
      else if (code.includes('6_1_DATE') || code.includes('7')) ruleCounts['Rule 6(1) Month & Year of Mfg/Pkg']++;
      else if (code.includes('18_2')) ruleCounts['Rule 18(2) Dual Pricing Check']++;
    });
  });

  return (
    <div className="analytics-page" style={{ padding: '24px' }}>
      <div className="page-header" style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Legal Metrology Compliance Analytics</h1>
        <p style={{ color: 'var(--text-muted)' }}>Aggregated compliance statistics and rule enforcement metrics</p>
      </div>

      <div className="metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600 }}>COMPLIANCE RATE</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#10B981', marginTop: 8 }}>{complianceRate}%</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Of scanned products pass PCR 2011</div>
        </div>

        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600 }}>TOTAL SCANS EXAMINED</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, marginTop: 8 }}>{total}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Across all enforcement zones</div>
        </div>

        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600 }}>NON-COMPLIANT VIOLATIONS</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#EF4444', marginTop: 8 }}>{nonCompliant}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Flagged for statutory enforcement</div>
        </div>

        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: 20, borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600 }}>FLAGGED FOR MANUAL REVIEW</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#F59E0B', marginTop: 8 }}>{needsReview}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Low OCR confidence or partial text</div>
        </div>
      </div>

      <div style={{ background: 'var(--bg-card)', padding: 24, borderRadius: 12, border: '1px solid var(--border)' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 16 }}>Violations Breakdown by Legal Provision</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {Object.entries(ruleCounts).map(([ruleName, count]) => {
            const percentage = total > 0 ? Math.min(100, (count / Math.max(1, total)) * 100).toFixed(0) : 0;
            return (
              <div key={ruleName}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 14 }}>
                  <span style={{ fontWeight: 600 }}>{ruleName}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{count} violations ({percentage}%)</span>
                </div>
                <div style={{ height: 8, background: 'rgba(255,255,255,0.08)', borderRadius: 4, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.max(percentage, count > 0 ? 5 : 0)}%`,
                      background: count > 0 ? 'linear-gradient(90deg, #F59E0B, #EF4444)' : '#3B82F6',
                      borderRadius: 4,
                      transition: 'width 0.3s ease'
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
