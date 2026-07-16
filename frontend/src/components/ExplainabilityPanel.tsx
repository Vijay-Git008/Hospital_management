import React from 'react';
import { Negotiation } from '../types/negotiation';
import { Bot, HelpCircle, ShieldAlert } from 'lucide-react';

interface ExplainabilityPanelProps {
  negotiation?: Negotiation;
}

export function ExplainabilityPanel({ negotiation }: ExplainabilityPanelProps) {
  if (!negotiation) {
    return (
      <div className="panel-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        Select an allocated case to inspect the AI Priority Explanation.
      </div>
    );
  }

  const tree = JSON.parse(negotiation.reasoning_tree_json || '{}');
  const aiNarrative = tree.ai_narrative || 'AI explanation unavailable – Configure a valid API key in Settings.';
  const bundle = tree.allocated_bundle || [];

  return (
    <div className="panel-content" style={{ gap: '16px' }}>
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

                {/* Score bars */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span>Triage Priority ({b.scoring.triage_score})</span>
                      <span>Weight: 45%</span>
                    </div>
                    <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px' }}>
                      <div style={{ height: '100%', background: 'var(--color-critical)', width: `${b.scoring.triage_score}%`, borderRadius: '2px' }}></div>
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span>Wait Duration ({b.scoring.wait_score})</span>
                      <span>Weight: 20%</span>
                    </div>
                    <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px' }}>
                      <div style={{ height: '100%', background: 'var(--color-warning)', width: `${b.scoring.wait_score}%`, borderRadius: '2px' }}></div>
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span>Suitability ({b.scoring.suitability_score})</span>
                      <span>Weight: 25%</span>
                    </div>
                    <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px' }}>
                      <div style={{ height: '100%', background: 'var(--color-stable)', width: `${b.scoring.suitability_score}%`, borderRadius: '2px' }}></div>
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                      <span>Cascade Penalty (-{b.scoring.impact_penalty})</span>
                      <span>Weight: 10%</span>
                    </div>
                    <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px' }}>
                      <div style={{ height: '100%', background: 'var(--color-critical)', width: `${b.scoring.impact_penalty}%`, borderRadius: '2px' }}></div>
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
