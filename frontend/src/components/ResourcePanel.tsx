import React, { useState } from 'react';
import { Resource } from '../types/negotiation';
import { apiService } from '../lib/api';
import { Server, Settings, RefreshCw, Power } from 'lucide-react';

interface ResourcePanelProps {
  resources: Resource[];
  onOverrideCompleted: () => void;
}

export function ResourcePanel({ resources, onOverrideCompleted }: ResourcePanelProps) {
  const [acting, setActing] = useState<string | null>(null);

  const handleOverride = async (resourceId: string, action: 'release' | 'occupy') => {
    setActing(resourceId);
    try {
      await apiService.overrideResource(resourceId, action);
      onOverrideCompleted();
    } catch (e: any) {
      console.error(e);
      alert(e.response?.data?.detail || 'Override failed. Check RBAC clearance levels.');
    } finally {
      setActing(null);
    }
  };

  // Group resources by type
  const types = Array.from(new Set(resources.map((r) => r.type)));

  return (
    <div className="panel-content">
      {types.map((type) => {
        const typeRes = resources.filter((r) => r.type === type);
        return (
          <div key={type} style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
              {type}s
            </div>

            <div className="floor-grid">
              {typeRes.map((r) => {
                const meta = JSON.parse(r.metadata_json || '{}');
                const isOccupied = r.status === 'Occupied';
                const isMaint = r.status === 'Maintenance';

                return (
                  <div key={r.id} className={`floor-cell ${r.status}`}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.8rem' }}>{r.name}</span>
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                        {type === 'ICU Bed' ? (meta.ventilator_attached ? 'Ventilated' : 'Standard') : meta.specialty || r.status}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '4px', marginTop: '6px' }}>
                      {(isOccupied || isMaint) && (
                        <button
                          className="btn"
                          style={{ padding: '2px 6px', fontSize: '0.65rem', display: 'flex', alignItems: 'center', gap: '3px', color: 'var(--color-success)' }}
                          disabled={acting === r.id}
                          onClick={() => handleOverride(r.id, 'release')}
                        >
                          <Power size={10} /> Reset
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
