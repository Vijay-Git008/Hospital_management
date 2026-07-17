export interface Resource {
  id: string;
  hospital_id: string;
  name: string;
  type: string;
  status: 'Available' | 'Occupied' | 'Maintenance';
  metadata_json: string;
  created_at: string;
}

export interface Patient {
  id: string;
  name_encrypted: string;
  triage_level: number;
  admission_time: string;
  status: 'Pending' | 'Allocated' | 'Discharged' | 'CRITICAL' | 'STABLE' | 'MODERATE';
  clinical_data_json: string;
  created_at: string;
  is_vip?: number;
  name?: string;
  age?: number;
  gender?: string;
  diagnosis?: string;
  bedId?: string | null;
  vitals?: string;
  attendingDoctor?: string | null;
  bloodGroup?: string;
}

export interface Incident {
  id: string;
  title: string;
  severity: 'Critical' | 'Major' | 'Minor';
  status: 'Active' | 'Resolved';
  created_at: string;
}

export interface NegotiationStep {
  id: string;
  negotiation_id: string;
  step_type: 'CFP' | 'BID' | 'AWARD' | 'REJECT';
  agent_id: string;
  content_json: string;
  created_at: string;
}

export interface Negotiation {
  id: string;
  incident_id: string;
  patient_id: string;
  status: 'Initiated' | 'Bidding' | 'Awarded' | 'Failed';
  reasoning_tree_json: string;
  created_at: string;
  steps?: NegotiationStep[];
}

export interface Allocation {
  id: string;
  negotiation_id: string | null;
  resource_id: string;
  patient_id: string;
  allocated_at: string;
  expires_at: string | null;
  status: 'Active' | 'Released' | 'Overridden';
  checksum: string;
  created_at: string;
}

export interface AuditRecord {
  id: string;
  user_id: string | null;
  action: string;
  target_id: string | null;
  payload_json: string;
  ip_address: string | null;
  checksum: string;
  created_at: string;
}

export interface AIConfig {
  configured: boolean;
  provider?: string;
  model_name?: string;
  temperature?: number;
  max_tokens?: number;
  updated_at?: string;
}
