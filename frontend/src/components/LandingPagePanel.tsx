import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Globe, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { fetchLandingPages } from "../services/api";
import type { LandingPageMetrics } from "../types";

interface Props {
  startDate: string;
  endDate: string;
  campaignId?: string;
}

function shortenUrl(url: string, maxLength = 50): string {
  try {
    const u = new URL(url);
    const path = u.pathname === "/" ? "" : u.pathname;
    const full = u.hostname + path;
    return full.length > maxLength ? full.slice(0, maxLength) + "…" : full;
  } catch {
    return url.length > maxLength ? url.slice(0, maxLength) + "…" : url;
  }
}

export default function LandingPagePanel({ startDate, endDate, campaignId }: Props) {
  const [sortField, setSortField] = useState<keyof LandingPageMetrics>("cost");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const { data, isLoading, error } = useQuery({
    queryKey: ["landing-pages", startDate, endDate, campaignId],
    queryFn: () => fetchLandingPages(startDate, endDate, campaignId),
  });

  if (isLoading) {
    return (
      <div className="panel loading-state">
        <Loader2 size={32} className="spin" />
        <p>Loading landing page performance...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="panel error-state">
        <p>Failed to load landing page data</p>
      </div>
    );
  }

  const sorted = [...data.pages].sort((a, b) => {
    const aVal = a[sortField] as number;
    const bVal = b[sortField] as number;
    return sortDir === "desc" ? bVal - aVal : aVal - bVal;
  });

  const handleSort = (field: keyof LandingPageMetrics) => {
    if (sortField === field) setSortDir(sortDir === "desc" ? "asc" : "desc");
    else { setSortField(field); setSortDir("desc"); }
  };

  const SortIcon = ({ field }: { field: keyof LandingPageMetrics }) =>
    sortField === field
      ? sortDir === "desc" ? <ChevronDown size={14} /> : <ChevronUp size={14} />
      : null;

  // Summary stats
  const totalCost = data.pages.reduce((s, p) => s + p.cost, 0);
  const totalClicks = data.pages.reduce((s, p) => s + p.clicks, 0);
  const totalConversions = data.pages.reduce((s, p) => s + p.conversions, 0);
  const avgConvRate = totalClicks > 0 ? (totalConversions / totalClicks * 100) : 0;

  // Chart: top 10 by cost
  const chartData = sorted.slice(0, 10).map((p) => ({
    name: shortenUrl(p.url, 30),
    cost: p.cost,
    conversions: p.conversions,
    conversion_rate: p.conversion_rate,
  }));

  return (
    <div className="lp-panel">
      <div className="panel">
        <div className="panel-header">
          <h2><Globe size={20} /> Landing Page Performance</h2>
          <span className="badge">{data.total_pages} pages</span>
        </div>

        {/* Summary */}
        <div className="lp-summary-cards">
          <div className="lp-summary-card">
            <span className="lp-summary-label">Total Pages</span>
            <span className="lp-summary-value">{data.total_pages}</span>
          </div>
          <div className="lp-summary-card">
            <span className="lp-summary-label">Total Cost</span>
            <span className="lp-summary-value">€{totalCost.toFixed(2)}</span>
          </div>
          <div className="lp-summary-card">
            <span className="lp-summary-label">Total Conversions</span>
            <span className="lp-summary-value">{totalConversions.toFixed(1)}</span>
          </div>
          <div className="lp-summary-card">
            <span className="lp-summary-label">Avg Conv. Rate</span>
            <span className="lp-summary-value">{avgConvRate.toFixed(2)}%</span>
          </div>
        </div>

        {/* Chart */}
        {chartData.length > 0 && (
          <div className="lp-chart">
            <h3>Top 10 Landing Pages by Cost</h3>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 160, right: 20, top: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tickFormatter={(v) => `€${v.toFixed(0)}`} />
                <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: number | string | undefined, name: string | undefined) => {
                    const v = Number(value ?? 0);
                    if (name === "cost") return [`€${v.toFixed(2)}`, "Cost"];
                    if (name === "conversions") return [v.toFixed(1), "Conversions"];
                    return [`${v.toFixed(2)}%`, "Conv. Rate"];
                  }}
                />
                <Bar dataKey="cost" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Table */}
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Landing Page URL</th>
                <th className="sortable" onClick={() => handleSort("impressions")}>
                  Impr. <SortIcon field="impressions" />
                </th>
                <th className="sortable" onClick={() => handleSort("clicks")}>
                  Clicks <SortIcon field="clicks" />
                </th>
                <th className="sortable" onClick={() => handleSort("cost")}>
                  Cost <SortIcon field="cost" />
                </th>
                <th className="sortable" onClick={() => handleSort("ctr")}>
                  CTR <SortIcon field="ctr" />
                </th>
                <th className="sortable" onClick={() => handleSort("avg_cpc")}>
                  Avg CPC <SortIcon field="avg_cpc" />
                </th>
                <th className="sortable" onClick={() => handleSort("conversions")}>
                  Conv. <SortIcon field="conversions" />
                </th>
                <th className="sortable" onClick={() => handleSort("conversion_rate")}>
                  Conv. Rate <SortIcon field="conversion_rate" />
                </th>
                <th className="sortable" onClick={() => handleSort("cost_per_conversion")}>
                  CPA <SortIcon field="cost_per_conversion" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((page, i) => (
                <tr key={i}>
                  <td className="lp-url-cell">
                    <a href={page.url} target="_blank" rel="noopener noreferrer" title={page.url}>
                      {shortenUrl(page.url)}
                      <ExternalLink size={12} style={{ marginLeft: 4, opacity: 0.5 }} />
                    </a>
                  </td>
                  <td>{page.impressions.toLocaleString()}</td>
                  <td>{page.clicks.toLocaleString()}</td>
                  <td>€{page.cost.toFixed(2)}</td>
                  <td>{page.ctr.toFixed(2)}%</td>
                  <td>€{page.avg_cpc.toFixed(2)}</td>
                  <td>{page.conversions.toFixed(1)}</td>
                  <td>{page.conversion_rate.toFixed(2)}%</td>
                  <td>{page.cost_per_conversion > 0 ? `€${page.cost_per_conversion.toFixed(2)}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
