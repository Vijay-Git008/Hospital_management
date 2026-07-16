import axios from 'axios';

let baseURL = import.meta.env.VITE_API_URL || '';

// Automatically handle GitHub Codespaces port forwarding hosts
if (typeof window !== 'undefined' && window.location.hostname.includes('.github.dev')) {
  baseURL = `https://${window.location.hostname.replace('-3000', '-8080')}`;
}

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Inject JWT token into headers on request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const apiService = {
  // Authentication
  async login(username: string, password: string): Promise<string> {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const res = await api.post('/api/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    const token = res.data.access_token;
    localStorage.setItem('token', token);
    return token;
  },

  async getMe() {
    const res = await api.get('/api/auth/me');
    return res.data;
  },

  logout() {
    localStorage.removeItem('token');
  },

  // Resources
  async getResources() {
    const res = await api.get('/api/resources');
    return res.data;
  },

  async overrideResource(resourceId: string, action: 'release' | 'occupy', patientId?: string) {
    const res = await api.post(`/api/resources/${resourceId}/override`, null, {
      params: { action, patient_id: patientId }
    });
    return res.data;
  },

  // Cases
  async getCases() {
    const res = await api.get('/api/cases');
    return res.data;
  },

  async ingestCase(name: string, triageLevel: number, clinicalData: any) {
    const res = await api.post('/api/cases/ingest', {
      name,
      triage_level: triageLevel,
      clinical_data: clinicalData
    });
    return res.data;
  },

  async triggerNegotiation(incidentId: string) {
    const res = await api.post('/api/cases/trigger-negotiation', null, {
      params: { incident_id: incidentId }
    });
    return res.data;
  },

  async loadScenario(scenarioName: string) {
    const res = await api.post('/api/cases/scenario', null, {
      params: { scenario_name: scenarioName }
    });
    return res.data;
  },

  // Negotiations
  async getNegotiationHistory() {
    const res = await api.get('/api/negotiation/history');
    return res.data;
  },

  async getNegotiationSteps(negotiationId: string) {
    const res = await api.get(`/api/negotiation/${negotiationId}/steps`);
    return res.data;
  },

  // Analytics & Audits
  async getDashboardMetrics() {
    const res = await api.get('/api/analytics/dashboard');
    return res.data;
  },

  async getAuditRecords() {
    const res = await api.get('/api/analytics/audit-records');
    return res.data;
  },

  async validateChain() {
    const res = await api.get('/api/analytics/validate-chain');
    return res.data;
  },

  // AI Configuration (BYOK)
  async saveAIConfig(provider: string, modelName: string, apiKey: string, temperature: number, maxTokens: number) {
    const res = await api.post('/api/ai/config', {
      provider,
      model_name: modelName,
      api_key: apiKey,
      temperature,
      max_tokens: maxTokens
    });
    return res.data;
  },

  async getAIConfig() {
    const res = await api.get('/api/ai/config');
    return res.data;
  },

  async testAIConnection(provider: string, modelName: string, apiKey: string, temperature: number) {
    const res = await api.post('/api/ai/test', {
      provider,
      model_name: modelName,
      api_key: apiKey,
      temperature
    });
    return res.data;
  }
};
