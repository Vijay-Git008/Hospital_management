import React, { useState, useEffect } from 'react';
import { apiService } from '../lib/api';
import { Shield, BrainCircuit, CheckCircle, AlertTriangle, Play, HelpCircle } from 'lucide-react';

export function AISettings() {
  const [provider, setProvider] = useState('gemini');
  const [modelName, setModelName] = useState('gemini-1.5-flash');
  const [apiKey, setApiKey] = useState('');
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(1000);
  
  const [savedConfig, setSavedConfig] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const me = await apiService.getMe();
        setRole(me.role);
      } catch (e) {
        console.error(e);
      }

      try {
        const config = await apiService.getAIConfig();
        if (config?.configured) {
          setSavedConfig(config);
          setProvider(config.provider);
          setModelName(config.model_name);
          setTemperature(config.temperature);
          setMaxTokens(config.max_tokens);
          setApiKey('********************************'); // Masked API key
        }
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  const handleProviderChange = (p: string) => {
    setProvider(p);
    if (p === 'openai') setModelName('gpt-4o-mini');
    else if (p === 'gemini') setModelName('gemini-1.5-flash');
    else if (p === 'anthropic') setModelName('claude-3-5-sonnet-20241022');
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await apiService.testAIConnection(provider, modelName, apiKey, temperature);
      setTestResult({ success: true, message: 'API connection verification succeeded. Key is valid.' });
    } catch (e: any) {
      setTestResult({ 
        success: false, 
        message: e.response?.data?.detail || 'Connection failed. Verify API Key and Model permissions.' 
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await apiService.saveAIConfig(provider, modelName, apiKey, temperature, maxTokens);
      setSavedConfig(res);
      alert('AI Configuration saved securely in the decrypted SQLite storage.');
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Save failed. Verify Administrator (RBAC) privileges.');
    } finally {
      setSaving(false);
    }
  };

  const isAdmin = role === 'Administrator';

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <BrainCircuit size={28} style={{ color: 'var(--color-accent)' }} />
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 600 }}>Bring Your Own Key (BYOK) Configuration</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Configure emergency operation assistant capabilities</p>
        </div>
      </div>

      <div style={{ backgroundColor: 'rgba(112, 111, 211, 0.04)', border: '1px dashed rgba(112, 111, 211, 0.2)', padding: '16px', borderRadius: '8px', fontSize: '0.85rem', lineHeight: '1.5' }}>
        <h4 style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
          <HelpCircle size={14} /> System Boundaries Note
        </h4>
        The core multi-agent resource negotiation engine is <strong>completely deterministic</strong> and runs independently of LLM availability. 
        API keys configured below are utilized strictly for narrative explainability, clinical logs synthesis, and incident summaries.
      </div>

      {!isAdmin && role && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: 'rgba(255, 82, 82, 0.08)', border: '1px solid rgba(255, 82, 82, 0.2)', padding: '12px', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--color-critical)' }}>
          <AlertTriangle size={16} />
          <span>RBAC Clearance Warning: You are logged in as {role}. Only the <strong>Administrator</strong> role has write-access to update system API settings.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="panel" style={{ padding: '20px', gap: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>AI Provider</label>
            <select 
              className="input-field" 
              value={provider} 
              onChange={(e) => handleProviderChange(e.target.value)}
              disabled={!isAdmin}
            >
              <option value="gemini">Google Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic Claude</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>Model Name</label>
            <input 
              type="text" 
              className="input-field" 
              value={modelName} 
              onChange={(e) => setModelName(e.target.value)}
              placeholder="e.g. gemini-1.5-flash"
              disabled={!isAdmin}
            />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>Secret API Key</label>
          <input 
            type="password" 
            className="input-field" 
            value={apiKey} 
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={savedConfig ? "Stored (Enter new key to overwrite)" : "Enter API Key"}
            disabled={!isAdmin}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>Temperature ({temperature})</label>
            <input 
              type="range" 
              min="0" 
              max="1.5" 
              step="0.1" 
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              disabled={!isAdmin}
              style={{ width: '100%', accentColor: 'var(--color-accent)' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>Max Tokens</label>
            <input 
              type="number" 
              className="input-field" 
              value={maxTokens} 
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              disabled={!isAdmin}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
          <button 
            type="button" 
            className="btn" 
            onClick={handleTestConnection}
            disabled={testing || !apiKey}
          >
            {testing ? 'Testing...' : 'Verify Connection'}
          </button>
          
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={saving || !isAdmin || !apiKey}
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>

        {testResult && (
          <div 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px', 
              fontSize: '0.85rem', 
              marginTop: '10px', 
              color: testResult.success ? 'var(--color-success)' : 'var(--color-critical)' 
            }}
          >
            {testResult.success ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
            <span>{testResult.message}</span>
          </div>
        )}
      </form>

      {savedConfig && (
        <div className="panel" style={{ padding: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>Active Runtime Parameters:</div>
          <div>Provider: <span style={{ fontFamily: 'var(--font-mono)' }}>{savedConfig.provider}</span></div>
          <div>Model: <span style={{ fontFamily: 'var(--font-mono)' }}>{savedConfig.model_name}</span></div>
          <div>Temperature: <span style={{ fontFamily: 'var(--font-mono)' }}>{savedConfig.temperature}</span></div>
          <div>Last Configured: {new Date(savedConfig.updated_at).toLocaleString()}</div>
        </div>
      )}
    </div>
  );
}
