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
import { BedManagementPanel } from '../components/BedManagementPanel';
import { AlertCircle, RefreshCw, Send, Loader, Crown, Check } from 'lucide-react';

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

  // VIP Override & Bed Management States
  const [beds, setBeds] = useState<any[]>([]);
  const [overrideData, setOverrideData] = useState<any>(null);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [activeResTab, setActiveResTab] = useState<'map' | 'beds'>('map');
  const [selectedCandidateId, setSelectedCandidateId] = useState('');
  const [selectedDestinationBed, setSelectedDestinationBed] = useState('');
  const [approvingOverride, setApprovingOverride] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const c = await apiService.getCases();
      setCases(c);
      const r = await apiService.getResources();
      setResources(r);
      const h = await apiService.getNegotiationHistory();
      setHistory(h);
      
      const b = await apiService.getBeds();
      setBeds(b);
      const override = await apiService.getVIPOverrideCandidates();
      setOverrideData(override);
      
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

      {/* VIP ICU Full Warning Banner */}
      {overrideData?.icu_full && (
        <div className="card" style={{ background: 'rgba(235, 87, 87, 0.08)', border: '1px solid var(--color-critical)', borderRadius: '8px', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '0 12px 12px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle style={{ color: 'var(--color-critical)' }} size={20} />
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--color-critical)', textTransform: 'uppercase' }}>🚨 ICU Capacity Full — VIP Admission Requirement</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ICU beds are currently 100% occupied. An incoming VIP requires ICU admission. Doctor intervention is required to evaluate stable candidates.</div>
            </div>
          </div>
          <button className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.75rem', display: 'flex', gap: '4px', alignItems: 'center', background: 'linear-gradient(135deg, #ECC94B 0%, #D69E2E 100%)', color: '#1A202C', border: 'none' }} onClick={() => setShowOverrideModal(true)}>
            <Crown size={12} /> Evaluate Candidates
          </button>
        </div>
      )}

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
          {/* Panel 4: Resource Floor Map & Bed Management */}
          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              <div style={{ display: 'flex', gap: '16px' }}>
                <span 
                  style={{ cursor: 'pointer', fontWeight: activeResTab === 'map' ? 700 : 500, color: activeResTab === 'map' ? 'var(--text-primary)' : 'var(--text-muted)', fontSize: '0.85rem' }}
                  onClick={() => setActiveResTab('map')}
                >
                  Floor Map
                </span>
                <span 
                  style={{ cursor: 'pointer', fontWeight: activeResTab === 'beds' ? 700 : 500, color: activeResTab === 'beds' ? 'var(--text-primary)' : 'var(--text-muted)', fontSize: '0.85rem' }}
                  onClick={() => setActiveResTab('beds')}
                >
                  Bed Management
                </span>
              </div>
            </div>
            {activeResTab === 'map' ? (
              <ResourcePanel 
                resources={resources} 
                onOverrideCompleted={() => setRefreshTrigger(p => p + 1)} 
              />
            ) : (
              <BedManagementPanel 
                beds={beds}
                patients={cases}
                onTransferCompleted={() => setRefreshTrigger(p => p + 1)}
              />
            )}
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

      {/* VIP Override Modal */}
      {showOverrideModal && overrideData && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000, background: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div className="panel" style={{ width: '550px', maxHeight: '90vh', overflowY: 'auto', padding: '24px', boxShadow: 'var(--shadow-lg)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '1rem', color: 'var(--color-critical)' }}>
                <Crown size={18} style={{ color: '#D69E2E' }} /> VIP ICU REALLOCATION DECISION SUPPORT
              </div>
              <button className="btn" style={{ padding: '4px 8px' }} onClick={() => setShowOverrideModal(false)}>✕</button>
            </div>

            <div style={{ background: 'rgba(235, 87, 87, 0.05)', border: '1px solid rgba(235, 87, 87, 0.2)', padding: '12px', borderRadius: '8px', fontSize: '0.8rem', lineHeight: '1.4' }}>
              <strong>Status:</strong> ICU Capacity is currently at <strong>{overrideData.occupied_icu_beds}/{overrideData.total_icu_beds} beds</strong>. An incoming VIP requires an ICU bed. Manual doctor authorization is required to step-down a stable patient.
            </div>

            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
                Select Stable Candidate for Downgrade
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {overrideData.candidates.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '16px' }}>
                    No stable ICU candidates found meeting transfer safety profiles.
                  </div>
                ) : (
                  overrideData.candidates.map((c: any) => {
                    const isSelected = selectedCandidateId === c.patient_id;
                    return (
                      <div 
                        key={c.patient_id} 
                        className="card"
                        style={{ 
                          cursor: 'pointer', 
                          borderColor: isSelected ? '#D69E2E' : 'var(--border-color)',
                          borderLeft: `4px solid ${isSelected ? '#D69E2E' : 'var(--color-success)'}`,
                          padding: '12px'
                        }}
                        onClick={() => {
                          setSelectedCandidateId(c.patient_id);
                          setSelectedDestinationBed(c.recommended_destination);
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>{c.name} ({c.patient_id})</span>
                          <span className="badge badge-success">Low Transfer Risk</span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                          <strong>Current ICU Bed:</strong> {c.current_bed} | <strong>Suggested Destination:</strong> {c.recommended_destination}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                          <strong>AI Recommendation Reasoning:</strong> {c.reasoning}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {selectedCandidateId && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Confirm manual relocation of Candidate <strong>{selectedCandidateId}</strong> to Bed <strong>{selectedDestinationBed}</strong> to allocate ICU Bed to the VIP Patient.
                </div>
                <button 
                  className="btn btn-primary" 
                  style={{ background: 'linear-gradient(135deg, #ECC94B 0%, #D69E2E 100%)', color: '#1A202C', border: 'none', display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center' }}
                  disabled={approvingOverride}
                  onClick={async () => {
                    setApprovingOverride(true);
                    try {
                      const candidate = overrideData.candidates.find((x: any) => x.patient_id === selectedCandidateId);
                      const targetIcuBedId = candidate.current_bed;
                      
                      const vipPatient = cases.find(p => p.is_vip === 1 && p.status === 'Pending');
                      if (!vipPatient) {
                        alert('No pending VIP patient found in queue.');
                        return;
                      }

                      await apiService.approveVIPOverride(
                        vipPatient.id,
                        selectedCandidateId,
                        targetIcuBedId,
                        selectedDestinationBed
                      );

                      setShowOverrideModal(false);
                      setSelectedCandidateId('');
                      setSelectedDestinationBed('');
                      setRefreshTrigger(prev => prev + 1);
                      alert('VIP Override approved and executed successfully! Relocation logged to audit logs.');
                    } catch (e: any) {
                      console.error(e);
                      alert(e.response?.data?.detail || 'Approval failed. Verify Doctor role privileges.');
                    } finally {
                      setApprovingOverride(false);
                    }
                  }}
                >
                  {approvingOverride ? <Loader size={14} className="animate-spin" /> : <Check size={14} />} Approve & Reallocate Bed
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
