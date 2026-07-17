import axios from 'axios';

let baseURL = import.meta.env.VITE_API_URL || '';

// Automatically handle GitHub Codespaces & VS Code port forwarding hosts
if (typeof window !== 'undefined' && window.location.host.includes('-3000')) {
  baseURL = `https://${window.location.host.replace('-3000', '-8080')}`;
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
  },

  // VIP ICU Override Workflow
  async getVIPOverrideCandidates() {
    const res = await api.get('/api/nexus/vip-override/candidates');
    return res.data;
  },

  async approveVIPOverride(vipPatientId: string, stablePatientId: string, targetIcuBedId: string, relocationBedId: string) {
    const res = await api.post('/api/nexus/vip-override/approve', {
      vip_patient_id: vipPatientId,
      stable_patient_id: stablePatientId,
      target_icu_bed_id: targetIcuBedId,
      relocation_bed_id: relocationBedId
    });
    return res.data;
  },

  // Bed Reassignment & Floor Management
  async getBeds() {
    const res = await api.get('/api/nexus/beds');
    return res.data;
  },

  async assignBed(patientId: string, bedId: string) {
    const res = await api.post('/api/nexus/beds/assign', {
      patient_id: patientId,
      bed_id: bedId
    });
    return res.data;
  },

  // Role-Specific Notification Engine
  async getNotifications() {
    const res = await api.get('/api/nexus/notifications');
    return res.data;
  },

  async getUnreadNotificationCount() {
    const res = await api.get('/api/nexus/notifications/unread-count');
    return res.data;
  },

  async markNotificationAsRead(id: string) {
    const res = await api.post(`/api/nexus/notifications/${id}/read`);
    return res.data;
  },
  async markAllNotificationsAsRead() {
    const res = await api.post('/api/nexus/notifications/read-all');
    return res.data;
  },

  // Ambulance Fleet & Nearby Hospital Discovery
  async getNearbyHospitals() {
    const res = await api.get('/api/nexus/hospitals/nearby');
    return res.data;
  },

  async getAmbulanceRecommendation(patientId: string, severity: string) {
    const res = await api.post('/api/nexus/ambulance/recommend', {
      patient_id: patientId,
      severity
    });
    return res.data;
  },

  async dispatchAmbulance(hospitalName: string, patientId: string) {
    const res = await api.post('/api/nexus/ambulance/dispatch', {
      hospital_name: hospitalName,
      patient_id: patientId
    });
    return res.data;
  },

  // Patient Record Interoperability & Imports/Exports
  async exportPatientJson(patientId: string) {
    const res = await api.get(`/api/nexus/patients/${patientId}/export-json`);
    return res.data;
  },

  async importPatientJson(data: any) {
    const res = await api.post('/api/nexus/patients/import-json', data);
    return res.data;
  }
};

