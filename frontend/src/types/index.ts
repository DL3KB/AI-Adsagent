export interface DateRange {
  start_date: string;
  end_date: string;
}

export interface CampaignMetrics {
  campaign_id: string;
  campaign_name: string;
  status: string;
  impressions: number;
  clicks: number;
  cost_micros: number;
  conversions: number;
  conversion_value: number;
  ctr: number;
  avg_cpc_micros: number;
  cost: number;
  avg_cpc: number;
  conversion_rate: number;
  cost_per_conversion: number;
}

export interface CampaignOverview {
  campaigns: CampaignMetrics[];
  total_cost: number;
  total_clicks: number;
  total_impressions: number;
  total_conversions: number;
  avg_ctr: number;
  avg_cpc: number;
  date_range: DateRange;
}

export interface AdGroupMetrics {
  ad_group_id: string;
  ad_group_name: string;
  campaign_id: string;
  campaign_name: string;
  status: string;
  impressions: number;
  clicks: number;
  cost_micros: number;
  conversions: number;
  ctr: number;
  avg_cpc_micros: number;
  cost: number;
  avg_cpc: number;
}

export interface KeywordMetrics {
  keyword_id: string;
  keyword_text: string;
  match_type: string;
  ad_group_id: string;
  ad_group_name: string;
  campaign_id: string;
  campaign_name: string;
  status: string;
  quality_score: number | null;
  impressions: number;
  clicks: number;
  cost_micros: number;
  conversions: number;
  ctr: number;
  avg_cpc_micros: number;
  cost: number;
  avg_cpc: number;
}

export interface Recommendation {
  priority: "high" | "medium" | "low";
  category: string;
  title: string;
  description: string;
  expected_impact: string;
  action_items: string[];
}

export interface Insight {
  type: "positive" | "negative" | "neutral";
  metric: string;
  title: string;
  description: string;
}

export interface AnalysisResponse {
  summary: string;
  recommendations: Recommendation[];
  insights: Insight[];
  raw_data_summary: Record<string, unknown>;
  proposals: Proposal[];
}

export type ProposalAction =
  | "pause_keyword"
  | "enable_keyword"
  | "pause_campaign"
  | "enable_campaign"
  | "pause_ad_group"
  | "enable_ad_group"
  | "add_negative_keyword"
  | "change_keyword_bid"
  | "change_campaign_budget"
  | "change_keyword_match_type";

export type ProposalStatus =
  | "pending"
  | "accepted"
  | "rejected"
  | "applied"
  | "failed";

export interface Proposal {
  id: string;
  action: ProposalAction;
  priority: "high" | "medium" | "low";
  title: string;
  reason: string;
  expected_impact: string;
  status: ProposalStatus;
  campaign_id?: string;
  campaign_name?: string;
  ad_group_id?: string;
  ad_group_name?: string;
  keyword_id?: string;
  keyword_text?: string;
  current_value?: string;
  new_value?: string;
  applied_at?: string;
  error_message?: string;
}

export interface ApplyProposalResult {
  proposal_id: string;
  success: boolean;
  message: string;
  action: ProposalAction;
}

export interface ApplyProposalsResponse {
  results: ApplyProposalResult[];
  total_applied: number;
  total_failed: number;
}

export interface AnalysisRequest {
  campaign_ids?: string[];
  date_range?: DateRange;
  focus_areas?: string[];
}

export interface ChatResponse {
  answer: string;
}

// ============================================================
// SEARCH TERMS
// ============================================================

export interface SearchTermMetrics {
  search_term: string;
  keyword_text: string;
  match_type: string;
  campaign_name: string;
  campaign_id: string;
  ad_group_name: string;
  impressions: number;
  clicks: number;
  cost: number;
  conversions: number;
  ctr: number;
  avg_cpc: number;
  conversion_rate: number;
  cost_per_conversion: number;
}

export interface SearchTermReport {
  search_terms: SearchTermMetrics[];
  total_search_terms: number;
  total_cost: number;
  total_clicks: number;
  total_impressions: number;
  total_conversions: number;
  irrelevant_spend: number;
  date_range: DateRange;
}

// ============================================================
// DEVICE / LOCATION SEGMENTATION
// ============================================================

export interface DeviceMetrics {
  device: string;
  impressions: number;
  clicks: number;
  cost: number;
  conversions: number;
  ctr: number;
  avg_cpc: number;
  conversion_rate: number;
  cost_per_conversion: number;
  impression_share: number;
  cost_share: number;
}

export interface LocationMetrics {
  location_name: string;
  location_type: string;
  location_id: string;
  impressions: number;
  clicks: number;
  cost: number;
  conversions: number;
  ctr: number;
  avg_cpc: number;
  conversion_rate: number;
  cost_per_conversion: number;
}

export interface DeviceLocationReport {
  devices: DeviceMetrics[];
  locations: LocationMetrics[];
  date_range: DateRange;
}

// ============================================================
// PERIOD COMPARISON
// ============================================================

export interface MetricChange {
  current: number;
  previous: number;
  change: number;
  change_pct: number;
  improved: boolean;
}

export interface ComparisonOverview {
  current_period: DateRange;
  previous_period: DateRange;
  cost: MetricChange;
  clicks: MetricChange;
  impressions: MetricChange;
  conversions: MetricChange;
  ctr: MetricChange;
  avg_cpc: MetricChange;
  conversion_rate: MetricChange;
  cost_per_conversion: MetricChange;
}

// ============================================================
// AUDIT LOG
// ============================================================

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  action: string;
  proposal_id?: string;
  campaign_id?: string;
  campaign_name?: string;
  ad_group_id?: string;
  keyword_id?: string;
  keyword_text?: string;
  old_value?: string;
  new_value?: string;
  success: boolean;
  error_message?: string;
}
