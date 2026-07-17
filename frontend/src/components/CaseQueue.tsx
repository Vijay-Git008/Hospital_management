import React, { useState, useEffect } from 'react';
import { Patient } from '../types/negotiation';
import { Shield, Clock, AlertTriangle } from 'lucide-react';

interface CaseQueueProps {
  cases: Patient[];
  onSelectCase: (c: Patient) => void;
  selectedCaseId?: string;
}

function DynamicWaitTimer({ time }: { time: string }) {
  const [elapsed, setElapsed] = useState('');

  useEffect(() => {
    const calc = () => {
      const diff = Date.now() - new Date(time).getTime();
      const sec = Math.max(0, Math.floor(diff / 1000));
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      const s = sec % 60;
      if (h > 0) {
        setElapsed(`${h}h ${m}m ${s}s`);
      } else {
        setElapsed(`${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
      }
    };
    calc();
    const interval = setInterval(calc, 1000);
    return () => clearInterval(interval);
  }, [time]);

  return <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{elapsed}</span>;
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
                  <Clock size={12} /> <DynamicWaitTimer time={c.admission_time} />
                </span>
                
                {c.status === 'Allocated' ? (
                  <span className="badge badge-success">Allocated</span>
                ) : (
                  <span className="badge badge-warning" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    <AlertTriangle size={10} /> Pending CRO
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
