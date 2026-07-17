import React from 'react';
import { Negotiation, Patient } from '../types/negotiation';
import { Bot, FileText, Download } from 'lucide-react';
import { apiService } from '../lib/api';

interface ExplainabilityPanelProps {
  patient?: Patient | null;
  negotiation?: Negotiation;
}

export function ExplainabilityPanel({ patient, negotiation }: ExplainabilityPanelProps) {
  if (!patient) {
    return (
      <div className="panel-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        Select an active patient case to view clinical details and download reports.
      </div>
    );
  }

  const handleExportJson = async () => {
    try {
      const data = await apiService.exportPatientJson(patient.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Patient_${patient.id}_Record.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Export failed: ' + err.message);
    }
  };

  const tree = negotiation ? JSON.parse(negotiation.reasoning_tree_json || '{}') : null;
  const aiNarrative = tree?.ai_narrative || 'AI explanation justification pending CRO Engine allocation.';
  const bundle = tree?.allocated_bundle || [];

  return (
    <div className="panel-content" style={{ gap: '14px', overflowY: 'auto', maxHeight: '100%' }}>
      
      {/* Patient Information & Clinical Actions */}
      <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Patient Profile
            </span>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
              {patient.name_encrypted}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Age: {patient.age} · Gender: {patient.gender} · Group: {patient.bloodGroup || 'O+'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button 
              className="btn btn-primary" 
              style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              onClick={() => window.open(`/api/nexus/patients/${patient.id}/pdf-report`, '_blank')}
            >
              <FileText size={12} /> PDF
            </button>
            <button 
              className="btn" 
              style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              onClick={() => window.open(`/api/nexus/patients/${patient.id}/csv-report`, '_blank')}
            >
              <Download size={12} /> CSV
            </button>
            <button 
              className="btn" 
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              onClick={handleExportJson}
            >
              JSON
            </button>
          </div>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '10px' }}>
          <div><strong>Diagnosis:</strong> {patient.diagnosis}</div>
          <div style={{ marginTop: '4px' }}><strong>Status:</strong> {patient.status} · <strong>Bed:</strong> {patient.bedId || 'Unallocated (EM Bay)'}</div>
        </div>
      </div>

      {/* Scoring tree breakdown */}
      <div>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
          Negotiation Scoring Tree
        </div>
        
        {bundle.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {bundle.map((b: any, idx: number) => (
              <div 
                key={idx} 
                style={{ 
                  backgroundColor: 'var(--bg-surface-elevated)', 
                  border: '1px solid var(--border-color)', 
                  padding: '10px', 
                  borderRadius: '6px' 
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, marginBottom: '6px' }}>
                  <span>{b.resource_name} ({b.resource_type})</span>
                  <span style={{ color: 'var(--color-success)', fontFamily: 'var(--font-mono)' }}>Score: {b.total_score}</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span>Triage Priority ({b.scoring.triage_score})</span>
                    </div>
                    <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px' }}>
                      <div style={{ height: '100%', background: 'var(--color-critical)', width: `${b.scoring.triage_score}%`, borderRadius: '2px' }}></div>
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span>Wait Duration ({b.scoring.wait_score})</span>
                    </div>
                    <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px' }}>
                      <div style={{ height: '100%', background: 'var(--color-warning)', width: `${b.scoring.wait_score}%`, borderRadius: '2px' }}></div>
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span>Suitability ({b.scoring.suitability_score})</span>
                    </div>
                    <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px' }}>
                      <div style={{ height: '100%', background: 'var(--color-success)', width: `${b.scoring.suitability_score}%`, borderRadius: '2px' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            No priority score breakdown recorded for this state.
          </div>
        )}
      </div>

      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
          <Bot size={14} style={{ color: 'var(--color-accent)' }} /> AI Decision Justification
        </div>

        <div 
          style={{ 
            fontSize: '0.85rem', 
            lineHeight: '1.5', 
            color: 'var(--text-primary)', 
            backgroundColor: 'rgba(112, 111, 211, 0.04)', 
            border: '1px dashed rgba(112, 111, 211, 0.2)',
            padding: '12px',
            borderRadius: '6px',
            whiteSpace: 'pre-wrap'
          }}
        >
          {aiNarrative}
        </div>
      </div>
    </div>
  );
}
