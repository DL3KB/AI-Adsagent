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
import type { AnalysisResponse, Proposal } from "../types";

export default function Dashboard() {
  const today = new Date();
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(today.getDate() - 30);

  const [startDate, setStartDate] = useState(thirtyDaysAgo.toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(today.toISOString().split("T")[0]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | undefined>();
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "analysis" | "chat" | "search-terms" | "segmentation" | "audit-log"
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

  const analysisMutation = useMutation({
    mutationFn: () =>
      runAnalysis({
        date_range: { start_date: startDate, end_date: endDate },
        campaign_ids: selectedCampaignId ? [selectedCampaignId] : undefined,
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

        {campaignData && activeTab === "dashboard" && (
          <>
            <MetricsCards data={campaignData} />
            <ComparisonCards startDate={startDate} endDate={endDate} />
            <CampaignCharts campaigns={campaignData.campaigns} />
            <CampaignTable
              campaigns={campaignData.campaigns}
              onSelect={setSelectedCampaignId}
              selectedId={selectedCampaignId}
            />
          </>
        )}

        {activeTab === "search-terms" && (
          <SearchTermsPanel startDate={startDate} endDate={endDate} />
        )}

        {activeTab === "segmentation" && (
          <DeviceLocationPanel startDate={startDate} endDate={endDate} />
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
          <ChatPanel startDate={startDate} endDate={endDate} />
        )}

        {activeTab === "audit-log" && <AuditLogPanel />}
      </main>
    </div>
  );
}
