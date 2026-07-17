import React, { useEffect, useState } from 'react';
import { apiService } from '../lib/api';
import { NegotiationStep } from '../types/negotiation';
import { Play, ArrowRight, CheckCircle2, XCircle } from 'lucide-react';

interface NegotiationTimelineProps {
  negotiationId?: string;
  refreshTrigger: number;
}

export function NegotiationTimeline({ negotiationId, refreshTrigger }: NegotiationTimelineProps) {
  const [steps, setSteps] = useState<NegotiationStep[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    async function loadSteps() {
      if (!negotiationId) {
        setSteps([]);
        return;
      }
      setLoading(true);
      try {
        const data = await apiService.getNegotiationSteps(negotiationId);
        setSteps(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadSteps();
  }, [negotiationId, refreshTrigger]);

  if (!negotiationId) {
    return (
      <div className="panel-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        Select a patient case to view live negotiation agent timelines.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="panel-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        Fetching agent timeline...
      </div>
    );
  }

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'CFP': return <Play size={14} style={{ color: 'var(--color-stable)' }} />;
      case 'BID': return <ArrowRight size={14} style={{ color: 'var(--color-accent)' }} />;
      case 'AWARD': return <CheckCircle2 size={14} style={{ color: 'var(--color-success)' }} />;
      case 'REJECT': return <XCircle size={14} style={{ color: 'var(--color-critical)' }} />;
      default: return null;
    }
  };

  return (
    <div className="panel-content" style={{ gap: '8px', fontFamily: 'var(--font-mono)' }}>
      {steps.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '20px' }}>
          No agent activity logged.
        </div>
      ) : (
        steps.map((s) => {
          let payload: any = {};
          try {
            payload = JSON.parse(s.content_json || '{}');
          } catch (err) {
            console.error('Failed to parse s.content_json:', err);
          }
          let text = '';

          if (s.step_type === 'CFP') {
            text = `[Patient Agent] Ingested Case ${payload.patient_name || 'Patient'} - Broadcasting Call For Proposals (CFP) for: [${(payload.required_resource_types || []).join(', ')}]`;
          } else if (s.step_type === 'BID') {
            text = `[Resource Agent ${s.agent_id.substring(0, 8)}] Submitted BID score: ${payload.bid_score || 0} (Suitability: ${payload.suitability || 0}, Cascading Impact nodes: ${payload.impact_count || 0})`;
          } else if (s.step_type === 'AWARD') {
            text = `[Negotiation Engine] AWARDED resource [${payload.resource_name || 'Resource'}] with score: ${payload.total_score || 0}`;
          } else if (s.step_type === 'REJECT') {
            text = `[Negotiation Engine] REJECTED resource [${s.agent_id.substring(0, 8)}] - ${payload.reason || 'Resource not allocated'}`;
          }

          return (
            <div 
              key={s.id} 
              style={{ 
                display: 'flex', 
                gap: '10px', 
                alignItems: 'flex-start', 
                fontSize: '0.75rem', 
                borderBottom: '1px solid rgba(255,255,255,0.02)',
                paddingBottom: '6px'
              }}
            >
              <div style={{ marginTop: '2px' }}>{getStepIcon(s.step_type)}</div>
              <div>
                <span style={{ color: 'var(--text-muted)', marginRight: '8px' }}>
                  {new Date(s.created_at).toLocaleTimeString()}
                </span>
                <span style={{ color: 'var(--text-primary)' }}>{text}</span>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
