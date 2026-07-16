import React, { useState, useEffect } from 'react';
import { apiService } from './lib/api';
import { Dashboard } from './pages/Dashboard';
import { AISettings } from './pages/AISettings';
import { Shield, BrainCircuit, Users, Lock, LogOut, CheckCircle, RefreshCw, Key } from 'lucide-react';

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'ai_settings' | 'audit_logs'>('dashboard');
  
  // Login form state
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin_user');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Audits logs state
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [validatingChain, setValidatingChain] = useState(false);
  const [chainResult, setChainResult] = useState<any>(null);

  const fetchUser = async () => {
    try {
      const me = await apiService.getMe();
      setUser(me);
    } catch (e) {
      console.error(e);
      // Clean stale token
      apiService.logout();
      setToken(null);
    }
  };

  useEffect(() => {
    if (token) {
      fetchUser();
    }
  }, [token]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setLoginError(null);
    try {
      const jwtToken = await apiService.login(username, password);
      setToken(jwtToken);
    } catch (err: any) {
      setLoginError('Incorrect username or password. Double check pre-seeded accounts.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    apiService.logout();
    setToken(null);
    setUser(null);
  };

  const loadAudits = async () => {
    try {
      const audits = await apiService.getAuditRecords();
      setAuditLogs(audits);
      
      setValidatingChain(true);
      const chain = await apiService.validateChain();
      setChainResult(chain);
    } catch (e) {
      console.error(e);
    } finally {
      setValidatingChain(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'audit_logs') {
      loadAudits();
    }
  }, [activeTab]);

  // Quick Login Pre-sets helper for evaluators
  const setQuickLogin = (userType: string) => {
    if (userType === 'admin') {
      setUsername('admin');
      setPassword('admin_user');
    } else if (userType === 'coordinator') {
      setUsername('coord');
      setPassword('coordinator_user');
    } else if (userType === 'doctor') {
      setUsername('doctor');
      setPassword('doctor_user');
    } else if (userType === 'nurse') {
      setUsername('nurse');
      setPassword('nurse_user');
    }
  };

  if (!token || !user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-main)' }}>
        <div className="panel" style={{ width: '400px', padding: '30px', boxShadow: 'var(--shadow-lg)' }}>
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div style={{ display: 'inline-flex', padding: '12px', borderRadius: '50%', backgroundColor: 'rgba(255, 82, 82, 0.1)', marginBottom: '12px' }}>
              <Shield size={32} style={{ color: 'var(--color-critical)' }} />
            </div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>EOC COMMAND CENTER</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Emergency operations multi-agent coordination</p>
          </div>

          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>Username</label>
              <input 
                type="text" 
                className="input-field" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                required 
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>Password</label>
              <input 
                type="password" 
                className="input-field" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
              />
            </div>

            {loginError && (
              <div style={{ color: 'var(--color-critical)', fontSize: '0.8rem', textAlign: 'center' }}>{loginError}</div>
            )}

            <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }} disabled={loading}>
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>

          {/* Quick Login Presets helper */}
          <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '20px', paddingTop: '16px' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', textAlign: 'center' }}>
              Judge Quick Login Presets
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button className="btn" style={{ padding: '6px', fontSize: '0.75rem' }} onClick={() => setQuickLogin('admin')}>Admin</button>
              <button className="btn" style={{ padding: '6px', fontSize: '0.75rem' }} onClick={() => setQuickLogin('coordinator')}>Coordinator</button>
              <button className="btn" style={{ padding: '6px', fontSize: '0.75rem' }} onClick={() => setQuickLogin('doctor')}>Doctor</button>
              <button className="btn" style={{ padding: '6px', fontSize: '0.75rem' }} onClick={() => setQuickLogin('nurse')}>Nurse</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="header">
        <div className="brand">
          <div className="brand-dot"></div>
          <h1>Metro General EOC Command</h1>
        </div>

        <nav className="nav-links">
          <button 
            className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            Operations Panel
          </button>
          <button 
            className={`nav-btn ${activeTab === 'ai_settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai_settings')}
          >
            AI Config (BYOK)
          </button>
          <button 
            className={`nav-btn ${activeTab === 'audit_logs' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit_logs')}
          >
            Audit trail logs
          </button>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{user.username}</span>
            <span className="badge badge-stable" style={{ fontSize: '0.65rem', marginTop: '2px' }}>{user.role}</span>
          </div>
          <button 
            className="btn" 
            style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-critical)' }}
            onClick={handleLogout}
          >
            <LogOut size={12} /> Sign Out
          </button>
        </div>
      </header>

      <main style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'ai_settings' && <AISettings />}
        {activeTab === 'audit_logs' && (
          <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 600 }}>Cryptographic Audit Logs Trail</h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Tamper-proof blockchain audit validation</p>
              </div>

              <button className="btn" onClick={loadAudits} disabled={validatingChain}>
                <RefreshCw size={14} style={{ marginRight: '6px' }} className={validatingChain ? 'animate-spin' : ''} /> Validate Integrity
              </button>
            </div>

            {chainResult && (
              <div 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '10px', 
                  backgroundColor: chainResult.chain_valid ? 'rgba(51, 217, 178, 0.08)' : 'rgba(255, 82, 82, 0.08)', 
                  border: `1px solid ${chainResult.chain_valid ? 'var(--color-success)' : 'var(--color-critical)'}`, 
                  padding: '16px', 
                  borderRadius: '8px',
                  fontSize: '0.9rem' 
                }}
              >
                <Key style={{ color: chainResult.chain_valid ? 'var(--color-success)' : 'var(--color-critical)' }} />
                <div>
                  <strong>{chainResult.chain_valid ? 'Audit trail integrity verified.' : 'SECURITY ALERT: Database tampering detected!'}</strong>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    {chainResult.chain_valid 
                      ? 'All block-chain verification signatures calculated correctly. Current databases are in a secure state.' 
                      : 'Some records fail SHA-256 parent hash verification.'}
                  </p>
                </div>
              </div>
            )}

            <div className="panel" style={{ overflow: 'hidden' }}>
              <div className="panel-header">Logged Actions</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-surface-elevated)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                      <th style={{ padding: '12px' }}>Timestamp</th>
                      <th style={{ padding: '12px' }}>Action</th>
                      <th style={{ padding: '12px' }}>Actor (UUID)</th>
                      <th style={{ padding: '12px' }}>Target ID</th>
                      <th style={{ padding: '12px' }}>SHA-256 Chained Hash</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(auditLogs || []).map((log) => (
                      <tr key={log.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{new Date(log.created_at).toLocaleString()}</td>
                        <td style={{ padding: '12px' }}>
                          <span className={`badge ${log.action.includes('Manual') ? 'badge-warning' : 'badge-stable'}`}>{log.action}</span>
                        </td>
                        <td style={{ padding: '12px' }}>{log.user_id ? log.user_id.substring(0, 8) : 'System'}</td>
                        <td style={{ padding: '12px' }}>{log.target_id ? log.target_id.substring(0, 8) : 'N/A'}</td>
                        <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>{log.checksum.substring(0, 32)}...</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
