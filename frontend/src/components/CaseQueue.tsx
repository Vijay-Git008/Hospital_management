import React from 'react';
import { Patient } from '../types/negotiation';
import { Shield, Clock, AlertTriangle } from 'lucide-react';

interface CaseQueueProps {
  cases: Patient[];
  onSelectCase: (c: Patient) => void;
  selectedCaseId?: string;
}

export function CaseQueue({ cases, onSelectCase, selectedCaseId }: CaseQueueProps) {
  const getTriageBadge = (level: number) => {
    switch (level) {
      case 1: return <span className="badge badge-critical">Triage 1 (Red)</span>;
      case 2: return <span className="badge badge-warning">Triage 2 (Orange)</span>;
      default: return <span className="badge badge-stable">Triage {level}</span>;
    }
  };

  return (
    <div className="panel-content">
      {cases.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 10px', color: 'var(--text-muted)' }}>
          No active cases in EOC queue. Load a simulation scenario to populate.
        </div>
      ) : (
        cases.map((c) => {
          const clinical = JSON.parse(c.clinical_data_json || '{}');
          const isSelected = c.id === selectedCaseId;

          return (
            <div 
              key={c.id} 
              className="card"
              style={{ 
                cursor: 'pointer',
                borderColor: isSelected ? 'var(--color-accent)' : 'var(--border-color)',
                borderLeft: `4px solid ${c.status === 'Allocated' ? 'var(--color-success)' : c.triage_level === 1 ? 'var(--color-critical)' : 'var(--color-warning)'}`
              }}
              onClick={() => onSelectCase(c)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                <span className="card-title" style={{ fontFamily: 'var(--font-mono)' }}>{c.name_encrypted}</span>
                {getTriageBadge(c.triage_level)}
              </div>
              
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: '1.4' }}>
                {clinical.summary || 'Critical operation pending'}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="card-meta" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={12} /> {new Date(c.admission_time).toLocaleTimeString()}
                </span>
                
                {c.status === 'Allocated' ? (
                  <span className="badge badge-success">Allocated</span>
                ) : (
                  <span className="badge badge-warning" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    <AlertTriangle size={10} /> Pending CNP
                  </span>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
