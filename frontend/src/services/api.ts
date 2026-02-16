import axios from "axios";
import type {
  CampaignOverview,
  AdGroupMetrics,
  KeywordMetrics,
  AnalysisRequest,
  AnalysisResponse,
  ChatResponse,
  ApplyProposalsResponse,
  SearchTermReport,
  ComparisonOverview,
  AuditLogEntry,
  DeviceLocationReport,
} from "../types";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
});

export async function fetchCampaigns(
  startDate?: string,
  endDate?: string
): Promise<CampaignOverview> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get<CampaignOverview>("/campaigns", { params });
  return data;
}

export async function fetchAdGroups(
  campaignId: string,
  startDate?: string,
  endDate?: string
): Promise<AdGroupMetrics[]> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get<AdGroupMetrics[]>(
    `/campaigns/${campaignId}/ad-groups`,
    { params }
  );
  return data;
}

export async function fetchKeywords(
  campaignId?: string,
  adGroupId?: string,
  startDate?: string,
  endDate?: string
): Promise<KeywordMetrics[]> {
  const params: Record<string, string> = {};
  if (campaignId) params.campaign_id = campaignId;
  if (adGroupId) params.ad_group_id = adGroupId;
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get<KeywordMetrics[]>("/keywords", { params });
  return data;
}

export async function runAnalysis(
  request: AnalysisRequest
): Promise<AnalysisResponse> {
  const { data } = await api.post<AnalysisResponse>("/analyze", request);
  return data;
}

export async function chatAboutCampaigns(
  question: string,
  startDate?: string,
  endDate?: string
): Promise<ChatResponse> {
  const params: Record<string, string> = { question };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.post<ChatResponse>("/chat", null, { params });
  return data;
}

export async function applyProposals(
  proposalIds: string[]
): Promise<ApplyProposalsResponse> {
  const { data } = await api.post<ApplyProposalsResponse>("/proposals/apply", {
    proposal_ids: proposalIds,
  });
  return data;
}

export async function rejectProposal(
  proposalId: string
): Promise<void> {
  await api.post(`/proposals/${proposalId}/reject`);
}

// ============================================================
// SEARCH TERMS
// ============================================================

export async function fetchSearchTerms(
  campaignId?: string,
  startDate?: string,
  endDate?: string,
  limit: number = 200
): Promise<SearchTermReport> {
  const params: Record<string, string | number> = { limit };
  if (campaignId) params.campaign_id = campaignId;
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get<SearchTermReport>("/search-terms", { params });
  return data;
}

// ============================================================
// DEVICE / LOCATION SEGMENTATION
// ============================================================

export async function fetchSegmentation(
  startDate?: string,
  endDate?: string,
  campaignId?: string,
  locationLimit: number = 50
): Promise<DeviceLocationReport> {
  const params: Record<string, string | number> = { location_limit: locationLimit };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  if (campaignId) params.campaign_id = campaignId;
  const { data } = await api.get<DeviceLocationReport>("/segmentation", { params });
  return data;
}

// ============================================================
// PERIOD COMPARISON
// ============================================================

export async function fetchComparison(
  startDate?: string,
  endDate?: string
): Promise<ComparisonOverview> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get<ComparisonOverview>("/comparison", { params });
  return data;
}

// ============================================================
// AUDIT LOG
// ============================================================

export async function fetchAuditLog(
  limit: number = 100,
  offset: number = 0
): Promise<{ entries: AuditLogEntry[]; total: number }> {
  const [entriesRes, countRes] = await Promise.all([
    api.get<AuditLogEntry[]>("/audit-log", { params: { limit, offset } }),
    api.get<{ count: number }>("/audit-log/count"),
  ]);
  return { entries: entriesRes.data, total: countRes.data.count };
}

// ============================================================
// EXPORT
// ============================================================

export function getExportUrl(
  type: "campaigns" | "search-terms" | "analysis",
  startDate?: string,
  endDate?: string,
  campaignId?: string
): string {
  const base = `http://localhost:8000/api/export/${type}/csv`;
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (campaignId) params.set("campaign_id", campaignId);
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

// ============================================================
// CACHE
// ============================================================

export async function clearCache(): Promise<void> {
  await api.post("/cache/clear");
}
