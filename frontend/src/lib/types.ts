export interface CurrentUser {
  id: number;
  email: string;
  roles: string[];
}

export interface CustomerListItem {
  canonical_customer_id: string;
  first_name: string | null;
  last_name: string | null;
  full_name_display: string | null;
  primary_email: string | null;
  primary_phone: string | null;
  country_code: string | null;
  account_status: string;
  total_spend: number | null;
  order_count: number | null;
  churn_risk_band: string | null;
  last_order_at: string | null;
}

export interface CustomerMetrics {
  canonical_customer_id: string;
  order_count: number;
  total_spend: number;
  refunded_amount: number;
  aov: number | null;
  first_order_at: string | null;
  last_order_at: string | null;
  days_since_last_order: number | null;
  historical_clv: number;
  r_score: number | null;
  f_score: number | null;
  m_score: number | null;
  rfm_segment: string | null;
  churn_risk_band: string;
  engagement_score: number | null;
}

export interface CustomerProfile {
  identity: { canonical_customer_id: string; identities: IdentityRecord[] };
  profile: Record<string, unknown>;
  metrics: CustomerMetrics | null;
  orders: OrderSummary[];
  segments: { segment_id: string; name: string; entered_on: string }[];
  quality: Record<string, unknown>[];
}

export interface IdentityRecord {
  identity_id: number;
  source_system: string;
  source_record_id: string;
  identity_namespace: string;
  confidence: number | null;
  first_seen_at: string;
}

export interface OrderSummary {
  order_id: string;
  order_ts: string;
  order_status: string;
  order_type: string;
  currency: string;
  net_amount: number;
  revenue_amount: number;
  channel: string | null;
  payment_method: string | null;
}

export interface SegmentSummary {
  segment_id: string;
  name: string;
  description: string;
  current_version: number;
  is_active: boolean;
  member_count: number;
  last_computed_at: string | null;
}

export interface AnalyticsSummary {
  total_customers: number;
  active_customers: number;
  at_risk_customers: number;
  total_revenue: number;
  total_orders: number;
  avg_aov: number;
  dq_score: number;
  last_run_id: number | null;
}

export interface PipelineRun {
  run_id: number;
  dataset_size: string;
  status: string;
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
}

export interface DatasetQualityScore {
  dataset: string;
  records_ingested: number;
  records_accepted: number;
  records_warned: number;
  records_quarantined: number;
  records_rejected: number;
  score_overall: number;
  score_completeness: number | null;
  score_validity: number | null;
  score_uniqueness: number | null;
  score_consistency: number | null;
  score_integrity: number | null;
  score_timeliness: number | null;
}

export interface AiSourceRef {
  source: string;
  section: string;
  score: number;
}

export interface AiAskResponse {
  answer: string;
  tools_called: string[];
  tool_denied: string[];
  sources: AiSourceRef[];
  provider: string;
  model: string | null;
  configured: boolean;
}

export interface AiStatus {
  configured: boolean;
  provider: string;
  knowledge_chunks: number;
}
