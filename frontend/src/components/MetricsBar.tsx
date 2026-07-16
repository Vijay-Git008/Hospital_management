import React, { useEffect, useState } from 'react';
import { apiService } from '../lib/api';
import { Activity, Users, ShieldCheck, Key } from 'lucide-react';

interface MetricsBarProps {
  refreshTrigger: number;
}

export function MetricsBar({ refreshTrigger }: MetricsBarProps) {
  const [metrics, setMetrics] = useState<any>(null);
  const [chainSecure, setChainSecure] = useState<boolean>(true);

  useEffect(() => {
    async function loadMetrics() {
      try {
        const m = await apiService.getDashboardMetrics();
        setMetrics(m);
        
        const chain = await apiService.validateChain();
        setChainSecure(chain.chain_valid);
      } catch (e) {
        console.error(e);
      }
    }
    loadMetrics();
  }, [refreshTrigger]);

  if (!metrics) return null;

  return (
    <div className="metrics-grid">
      <div className="metric-card">
        <div>
          <div className="metric-label">Resource Utilization</div>
          <div className="metric-value">{metrics.resources.utilization_rate}%</div>
        </div>
        <Activity size={24} style={{ color: 'var(--color-accent)' }} />
      </div>

      <div className="metric-card">
        <div>
          <div className="metric-label">Active Critical Cases</div>
          <div className="metric-value">{metrics.patients.total}</div>
        </div>
        <Users size={24} style={{ color: 'var(--color-critical)' }} />
      </div>

      <div className="metric-card">
        <div>
          <div className="metric-label">Allocations Resolved</div>
          <div className="metric-value">{metrics.patients.allocated}</div>
        </div>
        <ShieldCheck size={24} style={{ color: 'var(--color-success)' }} />
      </div>

      <div className="metric-card">
        <div>
          <div className="metric-label">Chain Security Verification</div>
          <div className="metric-value" style={{ fontSize: '1rem', marginTop: '8px' }}>
            {chainSecure ? (
              <span className="badge badge-success" style={{ display: 'inline-flex', gap: '4px', alignItems: 'center' }}>
                <Key size={10} /> Cryptography Verified
              </span>
            ) : (
              <span className="badge badge-critical">Integrity Tampered!</span>
            )}
          </div>
        </div>
        <ShieldCheck size={24} style={{ color: chainSecure ? 'var(--color-success)' : 'var(--color-critical)' }} />
      </div>
    </div>
  );
}
