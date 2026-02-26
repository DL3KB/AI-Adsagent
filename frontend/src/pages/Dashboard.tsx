import { useState } from "react";
import { BarChart3, Loader2, AlertCircle, RefreshCw, Download, Trash2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchCampaigns, runAnalysis, getExportUrl, clearCache } from "../services/api";
import MetricsCards from "../components/MetricsCards";
import CampaignTable from "../components/CampaignTable";
import CampaignCharts from "../components/CampaignCharts";
import ComparisonCards from "../components/ComparisonCards";
import AnalysisPanel from "../components/AnalysisPanel";
import ProposalsPanel from "../components/ProposalsPanel";
import SearchTermsPanel from "../components/SearchTermsPanel";
import AuditLogPanel from "../components/AuditLogPanel";
import DeviceLocationPanel from "../components/DeviceLocationPanel";
import ChatPanel from "../components/ChatPanel";
import DateRangePicker from "../components/DateRangePicker";
import CampaignSelector from "../components/CampaignSelector";
import ModelSelector from "../components/ModelSelector";
import PerformanceDeepDive from "../components/PerformanceDeepDive";
import NgramAnalysis from "../components/NgramAnalysis";
import QualityScorePanel from "../components/QualityScorePanel";
import LandingPagePanel from "../components/LandingPagePanel";
import type { AnalysisResponse, Proposal } from "../types";

export default function Dashboard() {
  const today = new Date();
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(today.getDate() - 30);

  const [startDate, setStartDate] = useState(thirtyDaysAgo.toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(today.toISOString().split("T")[0]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | undefined>();
  const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "analysis" | "chat" | "search-terms" | "segmentation" | "deep-dive" | "quality-score" | "landing-pages" | "audit-log"
  >("dashboard");

  const queryClient = useQueryClient();

  const cacheClearMutation = useMutation({
    mutationFn: clearCache,
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const {
    data: campaignData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["campaigns", startDate, endDate],
    queryFn: () => fetchCampaigns(startDate, endDate),
    retry: 1,
  });

  // Derive filtered view when a single campaign is selected
  const filteredData = campaignData
    ? selectedCampaignId
      ? (() => {
          const filtered = campaignData.campaigns.filter(
            (c) => c.campaign_id === selectedCampaignId
          );
          return {
            ...campaignData,
            campaigns: filtered,
            total_cost: filtered.reduce((s, c) => s + c.cost, 0),
            total_clicks: filtered.reduce((s, c) => s + c.clicks, 0),
            total_impressions: filtered.reduce((s, c) => s + c.impressions, 0),
            total_conversions: filtered.reduce((s, c) => s + c.conversions, 0),
            avg_ctr:
              filtered.length > 0
                ? filtered.reduce((s, c) => s + c.ctr, 0) / filtered.length
                : 0,
            avg_cpc:
              filtered.length > 0
                ? filtered.reduce((s, c) => s + c.avg_cpc, 0) / filtered.length
                : 0,
          };
        })()
      : campaignData
    : undefined;

  const analysisMutation = useMutation({
    mutationFn: () =>
      runAnalysis({
        date_range: { start_date: startDate, end_date: endDate },
        campaign_ids: selectedCampaignId ? [selectedCampaignId] : undefined,
        model: selectedModel,
      }),
    onSuccess: (data) => setAnalysis(data),
  });

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <BarChart3 size={28} color="#3b82f6" />
          <h1>AdsAgent</h1>
          <span className="header-subtitle">Google Ads AI Analysis</span>
        </div>
        <div className="header-right">
          {campaignData && (
            <CampaignSelector
              campaigns={campaignData.campaigns}
              selectedId={selectedCampaignId}
              onChange={setSelectedCampaignId}
            />
          )}
          <ModelSelector
            selectedModel={selectedModel}
            onChange={setSelectedModel}
          />
          <DateRangePicker
            startDate={startDate}
            endDate={endDate}
            onStartChange={setStartDate}
            onEndChange={setEndDate}
          />
          <a
            className="btn-icon"
            href={getExportUrl("campaigns", startDate, endDate, selectedCampaignId)}
            title="CSV Export"
            download
          >
            <Download size={18} />
          </a>
          <button
            className="btn-icon"
            onClick={() => cacheClearMutation.mutate()}
            title="Clear cache"
            disabled={cacheClearMutation.isPending}
          >
            <Trash2 size={18} />
          </button>
          <button className="btn-icon" onClick={() => refetch()} title="Refresh data">
            <RefreshCw size={18} />
          </button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="tabs">
        <button
          className={`tab ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          Dashboard
        </button>
        <button
          className={`tab ${activeTab === "search-terms" ? "active" : ""}`}
          onClick={() => setActiveTab("search-terms")}
        >
          Search Terms
        </button>
        <button
          className={`tab ${activeTab === "segmentation" ? "active" : ""}`}
          onClick={() => setActiveTab("segmentation")}
        >
          Devices & Locations
        </button>
        <button
          className={`tab ${activeTab === "deep-dive" ? "active" : ""}`}
          onClick={() => setActiveTab("deep-dive")}
        >
          Deep Dive
        </button>
        <button
          className={`tab ${activeTab === "quality-score" ? "active" : ""}`}
          onClick={() => setActiveTab("quality-score")}
        >
          Quality Score
        </button>
        <button
          className={`tab ${activeTab === "landing-pages" ? "active" : ""}`}
          onClick={() => setActiveTab("landing-pages")}
        >
          Landing Pages
        </button>
        <button
          className={`tab ${activeTab === "analysis" ? "active" : ""}`}
          onClick={() => setActiveTab("analysis")}
        >
          AI Analysis
        </button>
        <button
          className={`tab ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          AI Chat
        </button>
        <button
          className={`tab ${activeTab === "audit-log" ? "active" : ""}`}
          onClick={() => setActiveTab("audit-log")}
        >
          Change Log
        </button>
      </nav>

      {/* Content */}
      <main className="main-content">
        {isLoading && (
          <div className="loading-state">
            <Loader2 size={40} className="spin" />
            <p>Loading campaign data...</p>
          </div>
        )}

        {error && (
          <div className="error-state">
            <AlertCircle size={40} color="#ef4444" />
            <h3>Error loading data</h3>
            <p>{error instanceof Error ? error.message : "Connection error"}</p>
            <p className="error-hint">
              Make sure the backend is running (<code>uvicorn app.main:app</code>) and the API credentials in <code>.env</code> are correct.
            </p>
            <button className="btn-primary" onClick={() => refetch()}>
              Try again
            </button>
          </div>
        )}

        {filteredData && activeTab === "dashboard" && (
          <>
            <MetricsCards data={filteredData} />
            <ComparisonCards startDate={startDate} endDate={endDate} />
            <CampaignCharts campaigns={filteredData.campaigns} />
            <CampaignTable
              campaigns={filteredData.campaigns}
              onSelect={setSelectedCampaignId}
              selectedId={selectedCampaignId}
            />
          </>
        )}

        {activeTab === "search-terms" && (
          <>
            <SearchTermsPanel startDate={startDate} endDate={endDate} campaignId={selectedCampaignId} />
            <NgramAnalysis startDate={startDate} endDate={endDate} campaignId={selectedCampaignId} />
          </>
        )}

        {activeTab === "segmentation" && (
          <DeviceLocationPanel startDate={startDate} endDate={endDate} campaignId={selectedCampaignId} />
        )}

        {activeTab === "deep-dive" && (
          <PerformanceDeepDive startDate={startDate} endDate={endDate} campaignId={selectedCampaignId} />
        )}

        {activeTab === "quality-score" && (
          <QualityScorePanel startDate={startDate} endDate={endDate} campaignId={selectedCampaignId} />
        )}

        {activeTab === "landing-pages" && (
          <LandingPagePanel startDate={startDate} endDate={endDate} campaignId={selectedCampaignId} />
        )}

        {activeTab === "analysis" && (
          <>
            <AnalysisPanel
              analysis={analysis}
              isLoading={analysisMutation.isPending}
              onRunAnalysis={() => analysisMutation.mutate()}
            />
            {analysis && analysis.proposals && analysis.proposals.length > 0 && (
              <ProposalsPanel
                proposals={analysis.proposals}
                onProposalsUpdated={(updated: Proposal[]) =>
                  setAnalysis((prev) =>
                    prev ? { ...prev, proposals: updated } : prev
                  )
                }
              />
            )}
          </>
        )}

        {activeTab === "chat" && (
          <ChatPanel startDate={startDate} endDate={endDate} model={selectedModel} campaignId={selectedCampaignId} />
        )}

        {activeTab === "audit-log" && <AuditLogPanel />}
      </main>
    </div>
  );
}
