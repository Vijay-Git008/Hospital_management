import React, { useState } from 'react';
import { apiService } from '../lib/api';
import { ShieldAlert, Activity, PowerOff, Loader } from 'lucide-react';

interface ScenarioPickerProps {
  onScenarioLoaded: (incidentId: string) => void;
}

export function ScenarioPicker({ onScenarioLoaded }: ScenarioPickerProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const handleLoad = async (name: string) => {
    setLoading(name);
    try {
      const res = await apiService.loadScenario(name);
      onScenarioLoaded(res.incident_id);
    } catch (e) {
      console.error(e);
      alert('Failed to load scenario. Verify backend connection.');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
      <button 
        className="btn" 
        style={{ display: 'flex', alignItems: 'center', gap: '8px', borderLeft: '3px solid var(--color-critical)' }}
        disabled={loading !== null}
        onClick={() => handleLoad('mass_casualty')}
      >
        {loading === 'mass_casualty' ? <Loader className="animate-spin" size={14} /> : <ShieldAlert size={14} style={{ color: 'var(--color-critical)' }} />}
        MCI Pileup
      </button>

      <button 
        className="btn" 
        style={{ display: 'flex', alignItems: 'center', gap: '8px', borderLeft: '3px solid var(--color-warning)' }}
        disabled={loading !== null}
        onClick={() => handleLoad('pandemic')}
      >
        {loading === 'pandemic' ? <Loader className="animate-spin" size={14} /> : <Activity size={14} style={{ color: 'var(--color-warning)' }} />}
        Pandemic Surge
      </button>

      <button 
        className="btn" 
        style={{ display: 'flex', alignItems: 'center', gap: '8px', borderLeft: '3px solid var(--color-stable)' }}
        disabled={loading !== null}
        onClick={() => handleLoad('cyber_attack')}
      >
        {loading === 'cyber_attack' ? <Loader className="animate-spin" size={14} /> : <PowerOff size={14} style={{ color: 'var(--color-stable)' }} />}
        Grid Failover
      </button>
    </div>
  );
}
