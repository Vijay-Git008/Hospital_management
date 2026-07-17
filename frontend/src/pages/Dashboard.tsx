import React, { useEffect, useState, useCallback } from 'react';
import { apiService } from '../lib/api';
import { Patient, Resource, Negotiation } from '../types/negotiation';
import { useNegotiationSocket } from '../hooks/useNegotiationSocket';
import { ScenarioPicker } from '../components/ScenarioPicker';
import { MetricsBar } from '../components/MetricsBar';
import { CaseQueue } from '../components/CaseQueue';
import { ResourcePanel } from '../components/ResourcePanel';
import { NegotiationTimeline } from '../components/NegotiationTimeline';
import { ExplainabilityPanel } from '../components/ExplainabilityPanel';
import { DependencyGraph } from '../components/DependencyGraph';
import { AlertCircle, RefreshCw, Send, Loader } from 'lucide-react';

export function Dashboard() {
  const [cases, setCases] = useState<Patient[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [history, setHistory] = useState<Negotiation[]>([]);
  const [graphData, setGraphData] = useState<any>(null);
  
  const [selectedCase, setSelectedCase] = useState<Patient | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null);

  // Manual Ingest State
  const [ingestName, setIngestName] = useState('');
  const [ingestTriage, setIngestTriage] = useState(1);
  const [ingestSummary, setIngestSummary] = useState('');
  const [ingestResources, setIngestResources] = useState<string[]>(['Operating Room', 'Doctor']);
  const [ingesting, setIngesting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const c = await apiService.getCases();
      setCases(c);
      const r = await apiService.getResources();
      setResources(r);
      const h = await apiService.getNegotiationHistory();
      setHistory(h);
      
      // Calculate a local SVG graph fallback if backend graph is not received yet
      // (This will be overwritten by direct websocket state pushes)
      const nodes = [
        ...c.map(pt => ({ id: pt.id, data: { label: pt.name_encrypted, type: 'patient' as const, status: pt.status } })),
        ...r.map(res => ({ id: res.id, data: { label: res.name, type: 'resource' as const, res_type: res.type, status: res.status } }))
      ];
      
      const edges: any[] = [];
      c.forEach(pt => {
        const clin = JSON.parse(pt.clinical_data_json || '{}');
        const reqs = clin.required_resources || [];
        reqs.forEach((req: string) => {
          r.filter(res => res.type === req).forEach(res => {
            edges.push({
              id: `edge-${pt.id}-${res.id}`,
              source: pt.id,
              target: res.id,
              label: 'requires',
              animated: false
            });
          });
        });
      });

      // Add solid active allocations
      h.filter(neg => neg.status === 'Awarded').forEach(neg => {
        const tree = JSON.parse(neg.reasoning_tree_json || '{}');
        const bundle = tree.allocated_bundle || [];
        bundle.forEach((b: any) => {
          edges.push({
            id: `edge-${b.resource_id}-${neg.patient_id}`,
            source: b.resource_id,
            target: neg.patient_id,
            label: 'allocated',
            animated: true
          });
        });
      });

      setGraphData({ nodes, edges });
    } catch (e) {
      console.error('Error loading dashboard data:', e);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData, refreshTrigger]);

  // WebSocket Live Push state update
  const handleWsMessage = useCallback((data: any) => {
    console.log('WS Message Received in Dashboard:', data);
    if (data.event === 'negotiation_complete') {
      setRefreshTrigger(prev => prev + 1);
      if (data.graph) {
        setGraphData(data.graph);
      }
    }
  }, []);

  const { connected } = useNegotiationSocket(handleWsMessage);

  const handleScenarioLoaded = (incidentId: string) => {
    setActiveIncidentId(incidentId);
    setRefreshTrigger(prev => prev + 1);
  };

  const handleManualIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestName || !ingestSummary) return;
    setIngesting(true);
    try {
      await apiService.ingestCase(ingestName, ingestTriage, {
        summary: ingestSummary,
        required_resources: ingestResources
      });
      setIngestName('');
      setIngestSummary('');
      setRefreshTrigger(prev => prev + 1);
      
      // If there is an active incident, immediately run negotiation for this case
      if (activeIncidentId) {
        await apiService.triggerNegotiation(activeIncidentId);
      }
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Manual Ingest failed. Verify coordinator RBAC role.');
    } finally {
      setIngesting(false);
    }
  };

  const selectedNegotiation = history.find(n => n.patient_id === selectedCase?.id);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Metrics Header */}
      <div style={{ padding: '12px 12px 0 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>SIMULATION SCENARIOS:</span>
            <ScenarioPicker onScenarioLoaded={handleScenarioLoaded} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              WebSocket Feed: {connected ? (
                <span className="badge badge-success">Connected</span>
              ) : (
                <span className="badge badge-critical">Disconnected</span>
              )}
            </span>
            <button className="btn" style={{ padding: '6px' }} onClick={() => setRefreshTrigger(p => p + 1)}>
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
        <MetricsBar refreshTrigger={refreshTrigger} />
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Panel 1: Case Queue */}
        <div className="panel">
          <div className="panel-header">
            <span>Critical Queue</span>
            <span className="badge badge-critical">{cases.filter(c => c.status === 'Pending').length} Pending</span>
          </div>
          <CaseQueue 
            cases={cases} 
            onSelectCase={setSelectedCase} 
            selectedCaseId={selectedCase?.id} 
          />
        </div>

        {/* Center Section: Graph & Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Panel 2: Dependency Graph */}
          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-header">
              <span>CRO Engine Resource Allocation Graph</span>
            </div>
            <DependencyGraph graphData={graphData} />
          </div>

          {/* Panel 3: Negotiation Timeline */}
          <div className="panel" style={{ height: '220px' }}>
            <div className="panel-header">
              <span>CRO Engine Process Log Stream</span>
            </div>
            <NegotiationTimeline 
              negotiationId={selectedNegotiation?.id} 
              refreshTrigger={refreshTrigger} 
            />
          </div>
        </div>

        {/* Right Section: Resources & Explainability */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Panel 4: Resource Floor Map */}
          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-header">
              <span>Resource Status</span>
            </div>
            <ResourcePanel 
              resources={resources} 
              onOverrideCompleted={() => setRefreshTrigger(p => p + 1)} 
            />
          </div>

          {/* Panel 5: AI Explanation Panel */}
          <div className="panel" style={{ height: '320px' }}>
            <div className="panel-header">
              <span>CRO Engine Decision Reasoning</span>
            </div>
            <ExplainabilityPanel negotiation={selectedNegotiation} />
          </div>
        </div>
      </div>

      {/* Bottom Panel: Coordinator Manual Ingest form */}
      <div 
        style={{ 
          borderTop: '1px solid var(--border-color)', 
          background: 'var(--bg-surface)', 
          padding: '12px 24px', 
          display: 'flex', 
          gap: '20px', 
          alignItems: 'center' 
        }}
      >
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', width: '120px' }}>
          Manual Ingest Case
        </span>
        <form onSubmit={handleManualIngest} style={{ flex: 1, display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input 
            type="text" 
            className="input-field" 
            style={{ width: '180px' }} 
            placeholder="Patient Name" 
            value={ingestName}
            onChange={(e) => setIngestName(e.target.value)}
          />
          <select 
            className="input-field" 
            style={{ width: '130px' }}
            value={ingestTriage}
            onChange={(e) => setIngestTriage(parseInt(e.target.value))}
          >
            <option value={1}>Triage 1 (Red)</option>
            <option value={2}>Triage 2 (Orange)</option>
            <option value={3}>Triage 3 (Yellow)</option>
          </select>
          <input 
            type="text" 
            className="input-field" 
            placeholder="Clinical symptoms summary" 
            value={ingestSummary}
            onChange={(e) => setIngestSummary(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" style={{ display: 'flex', gap: '6px', alignItems: 'center' }} disabled={ingesting}>
            {ingesting ? <Loader size={14} className="animate-spin" /> : <Send size={14} />} Ingest
          </button>
        </form>
      </div>
    </div>
  );
}
