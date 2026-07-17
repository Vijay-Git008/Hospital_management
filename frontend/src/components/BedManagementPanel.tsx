import React, { useState } from 'react';
import { Patient, Resource } from '../types/negotiation';
import { apiService } from '../lib/api';
import { ArrowRightLeft, ShieldAlert, Loader } from 'lucide-react';

interface BedManagementPanelProps {
  beds: any[];
  patients: Patient[];
  onTransferCompleted: () => void;
}

export function BedManagementPanel({ beds, patients, onTransferCompleted }: BedManagementPanelProps) {
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [targetBedId, setTargetBedId] = useState('');
  const [transferring, setTransferring] = useState(false);

  // Filter occupied beds
  const occupiedBeds = beds.filter(b => b.patientId !== null);
  const availableBeds = beds.filter(b => b.status === 'AVAILABLE');

  const getPatientDetails = (id: string) => {
    return patients.find(p => p.id === id);
  };

  const calculateTransferDetails = (patient?: Patient) => {
    if (!patient) return { risk: 'Unknown', reason: 'Select a patient to generate reasoning.' };
    
    let vitals: any = {};
    try {
      vitals = JSON.parse(patient.vitals || '{}');
    } catch (e) {
      vitals = {};
    }

    const isCritical = patient.status === 'CRITICAL';
    const gcs = vitals.gcs || 15;
    const spo2 = vitals.spo2 || 98;

    if (gcs < 13 || spo2 < 90 || isCritical) {
      return {
        risk: 'High',
        reason: `Patient exhibits unstable telemetry metrics (SPO2: ${spo2}%, GCS: ${gcs}). Moving to lower-acuity units requires continuous critical nursing surveillance.`
      };
    } else if (patient.status === 'STABLE') {
      return {
        risk: 'Low',
        reason: 'Patient vitals are stable on room air. Step-down transfer to General Ward is clinically indicated.'
      };
    } else {
      return {
        risk: 'Moderate',
        reason: 'Patient is stable but requires continuous telemetry updates. Suitable for telemetry general wards.'
      };
    }
  };

  const handleTransfer = async () => {
    if (!selectedPatientId || !targetBedId) return;
    setTransferring(true);
    try {
      const patient = getPatientDetails(selectedPatientId);
      const oldBed = patient?.bedId;
      const targetBed = beds.find(b => b.id === targetBedId);

      // Execute transfer
      await apiService.assignBed(selectedPatientId, targetBedId);

      // Log manual transfer
      const actionText = `Manual Bed Assignment: Transferred ${patient?.name || selectedPatientId} from ${oldBed || 'unknown'} to ${targetBedId} (${targetBed?.zone || 'GW'}).`;
      await api.post('/api/nexus/logs', { text: actionText });

      onTransferCompleted();
      setSelectedPatientId('');
      setTargetBedId('');
      alert('Transfer completed successfully!');
    } catch (e: any) {
      console.error(e);
      alert(e.response?.data?.detail || 'Bed reassignment failed. Check RBAC permissions.');
    } finally {
      setTransferring(false);
    }
  };

  const selectedPatient = getPatientDetails(selectedPatientId);
  const { risk, reason } = calculateTransferDetails(selectedPatient);

  return (
    <div className="panel-content" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
          Execute Patient Bed Relocation
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>SELECT OCCUPIED BED / PATIENT</label>
            <select 
              className="input-field" 
              value={selectedPatientId} 
              onChange={(e) => setSelectedPatientId(e.target.value)}
              style={{ width: '100%', padding: '6px' }}
            >
              <option value="">-- Choose Patient --</option>
              {occupiedBeds.map(b => {
                const pt = getPatientDetails(b.patientId);
                return (
                  <option key={b.id} value={b.patientId}>
                    {b.id} - {pt ? pt.name : 'Unknown'} ({pt ? pt.status : ''})
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>SELECT TARGET AVAILABLE BED</label>
            <select 
              className="input-field" 
              value={targetBedId} 
              onChange={(e) => setTargetBedId(e.target.value)}
              style={{ width: '100%', padding: '6px' }}
              disabled={!selectedPatientId}
            >
              <option value="">-- Choose Target Bed --</option>
              {availableBeds.map(b => (
                <option key={b.id} value={b.id}>
                  {b.id} - {b.zone} (Available)
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {selectedPatient && (
        <div className="card" style={{ padding: '12px', borderLeft: `3px solid ${risk === 'High' ? 'var(--color-critical)' : risk === 'Moderate' ? 'var(--color-warning)' : 'var(--color-success)'}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>CLINICAL REASSIGNMENT DECISION RISK</span>
            <span className={`badge ${risk === 'High' ? 'badge-critical' : risk === 'Moderate' ? 'badge-warning' : 'badge-success'}`}>
              {risk} Risk
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
            {reason}
          </p>
        </div>
      )}

      <button 
        className="btn btn-primary" 
        style={{ width: '100%', display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center' }}
        disabled={!selectedPatientId || !targetBedId || transferring}
        onClick={handleTransfer}
      >
        {transferring ? (
          <Loader size={14} className="animate-spin" />
        ) : (
          <ArrowRightLeft size={14} />
        )}
        Approve Bed Transfer
      </button>
    </div>
  );
}

// Internal helper for logs compatibility
const api = {
  post: async (url: string, data: any) => {
    const token = localStorage.getItem('token');
    const headers: any = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const baseURL = import.meta.env.VITE_API_URL || '';
    let rewrittenURL = baseURL + url;
    if (typeof window !== 'undefined' && window.location.hostname.includes('.github.dev')) {
      rewrittenURL = `https://${window.location.hostname.replace('-3000', '-8080')}${url}`;
    }
    const res = await fetch(rewrittenURL, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('API request failed');
    return res.json();
  }
};
