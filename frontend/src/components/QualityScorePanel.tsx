import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Award, ChevronDown, ChevronUp } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { fetchKeywords } from "../services/api";
import type { KeywordMetrics } from "../types";

interface Props {
  startDate: string;
  endDate: string;
  campaignId?: string;
}

const QS_COLORS: Record<string, string> = {
  ABOVE_AVERAGE: "#22c55e",
  AVERAGE: "#f59e0b",
  BELOW_AVERAGE: "#ef4444",
};

const QS_LABELS: Record<string, string> = {
  ABOVE_AVERAGE: "Above Average",
  AVERAGE: "Average",
  BELOW_AVERAGE: "Below Average",
};

function QsBadge({ value }: { value: string | null }) {
  if (!value) return <span className="qs-badge qs-unknown">N/A</span>;
  const color = value === "ABOVE_AVERAGE" ? "qs-good" : value === "AVERAGE" ? "qs-ok" : "qs-bad";
  return <span className={`qs-badge ${color}`}>{QS_LABELS[value] || value}</span>;
}

function QsScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="qs-badge qs-unknown">—</span>;
  const cls = score >= 7 ? "qs-good" : score >= 5 ? "qs-ok" : "qs-bad";
  return <span className={`qs-score-badge ${cls}`}>{score}/10</span>;
}

export default function QualityScorePanel({ startDate, endDate, campaignId }: Props) {
  const [sortField, setSortField] = useState<keyof KeywordMetrics>("cost");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filterQs, setFilterQs] = useState<string | null>(null);

  const { data: keywords, isLoading, error } = useQuery({
    queryKey: ["keywords", campaignId, startDate, endDate],
    queryFn: () => fetchKeywords(campaignId, undefined, startDate, endDate),
  });

  if (isLoading) {
    return (
      <div className="panel loading-state">
        <Loader2 size={32} className="spin" />
        <p>Loading Quality Score data...</p>
      </div>
    );
  }

  if (error || !keywords) {
    return (
      <div className="panel error-state">
        <p>Failed to load keyword data</p>
      </div>
    );
  }

  // Keywords with QS data
  const withQs = keywords.filter((k) => k.quality_score !== null);

  // Distribution data for pie charts
  const buildDistribution = (field: "expected_ctr" | "ad_relevance" | "landing_page_experience") => {
    const counts: Record<string, number> = { ABOVE_AVERAGE: 0, AVERAGE: 0, BELOW_AVERAGE: 0 };
    withQs.forEach((k) => {
      const val = k[field];
      if (val && counts[val] !== undefined) counts[val]++;
    });
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ name: QS_LABELS[k] || k, value: v, key: k }));
  };

  const ctrDist = buildDistribution("expected_ctr");
  const relDist = buildDistribution("ad_relevance");
  const lpeDist = buildDistribution("landing_page_experience");

  // QS summary stats
  const avgQs = withQs.length > 0 ? (withQs.reduce((s, k) => s + (k.quality_score || 0), 0) / withQs.length) : 0;
  const lowQs = withQs.filter((k) => (k.quality_score || 0) < 5);
  const highQs = withQs.filter((k) => (k.quality_score || 0) >= 7);

  // Filter and sort
  let filtered = filterQs
    ? keywords.filter((k) => {
        if (filterQs === "low") return k.quality_score !== null && k.quality_score < 5;
        if (filterQs === "mid") return k.quality_score !== null && k.quality_score >= 5 && k.quality_score < 7;
        if (filterQs === "high") return k.quality_score !== null && k.quality_score >= 7;
        return true;
      })
    : keywords;

  const sorted = [...filtered].sort((a, b) => {
    const aVal = (a[sortField] ?? 0) as number;
    const bVal = (b[sortField] ?? 0) as number;
    return sortDir === "desc" ? bVal - aVal : aVal - bVal;
  });

  const handleSort = (field: keyof KeywordMetrics) => {
    if (sortField === field) setSortDir(sortDir === "desc" ? "asc" : "desc");
    else { setSortField(field); setSortDir("desc"); }
  };

  const SortIcon = ({ field }: { field: keyof KeywordMetrics }) =>
    sortField === field
      ? sortDir === "desc" ? <ChevronDown size={14} /> : <ChevronUp size={14} />
      : null;

  return (
    <div className="qs-panel">
      <div className="panel">
        <div className="panel-header">
          <h2><Award size={20} /> Quality Score Breakdown</h2>
          <span className="badge">{withQs.length} keywords with QS</span>
        </div>

        {/* Summary cards */}
        <div className="qs-summary-cards">
          <div className="qs-summary-card">
            <span className="qs-summary-label">Avg Quality Score</span>
            <span className={`qs-summary-value ${avgQs >= 7 ? "good" : avgQs >= 5 ? "ok" : "bad"}`}>
              {avgQs.toFixed(1)}/10
            </span>
          </div>
          <div className="qs-summary-card">
            <span className="qs-summary-label">High QS (7+)</span>
            <span className="qs-summary-value good">{highQs.length}</span>
          </div>
          <div className="qs-summary-card">
            <span className="qs-summary-label">Low QS (&lt;5)</span>
            <span className="qs-summary-value bad">{lowQs.length}</span>
          </div>
          <div className="qs-summary-card">
            <span className="qs-summary-label">No QS Data</span>
            <span className="qs-summary-value">{keywords.length - withQs.length}</span>
          </div>
        </div>

        {/* Pie charts for sub-components */}
        {(ctrDist.length > 0 || relDist.length > 0 || lpeDist.length > 0) && (
          <div className="qs-pie-row">
            <div className="qs-pie-card">
              <h4>Expected CTR</h4>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={ctrDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} label={({ name, value }) => `${name}: ${value}`}>
                    {ctrDist.map((entry) => (
                      <Cell key={entry.key} fill={QS_COLORS[entry.key]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="qs-pie-card">
              <h4>Ad Relevance</h4>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={relDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} label={({ name, value }) => `${name}: ${value}`}>
                    {relDist.map((entry) => (
                      <Cell key={entry.key} fill={QS_COLORS[entry.key]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="qs-pie-card">
              <h4>Landing Page Exp.</h4>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={lpeDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} label={({ name, value }) => `${name}: ${value}`}>
                    {lpeDist.map((entry) => (
                      <Cell key={entry.key} fill={QS_COLORS[entry.key]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Filter buttons */}
        <div className="qs-filters">
          <button className={`qs-filter-btn ${filterQs === null ? "active" : ""}`} onClick={() => setFilterQs(null)}>
            All ({keywords.length})
          </button>
          <button className={`qs-filter-btn qs-good ${filterQs === "high" ? "active" : ""}`} onClick={() => setFilterQs(filterQs === "high" ? null : "high")}>
            High QS 7+ ({highQs.length})
          </button>
          <button className={`qs-filter-btn qs-ok ${filterQs === "mid" ? "active" : ""}`} onClick={() => setFilterQs(filterQs === "mid" ? null : "mid")}>
            Mid QS 5-6 ({withQs.filter((k) => (k.quality_score || 0) >= 5 && (k.quality_score || 0) < 7).length})
          </button>
          <button className={`qs-filter-btn qs-bad ${filterQs === "low" ? "active" : ""}`} onClick={() => setFilterQs(filterQs === "low" ? null : "low")}>
            Low QS &lt;5 ({lowQs.length})
          </button>
        </div>

        {/* Keywords table w/ sub-components */}
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Keyword</th>
                <th>Match</th>
                <th className="sortable" onClick={() => handleSort("quality_score")}>
                  QS <SortIcon field="quality_score" />
                </th>
                <th>Exp. CTR</th>
                <th>Ad Relevance</th>
                <th>LP Exp.</th>
                <th className="sortable" onClick={() => handleSort("impressions")}>
                  Impr. <SortIcon field="impressions" />
                </th>
                <th className="sortable" onClick={() => handleSort("clicks")}>
                  Clicks <SortIcon field="clicks" />
                </th>
                <th className="sortable" onClick={() => handleSort("cost")}>
                  Cost <SortIcon field="cost" />
                </th>
                <th className="sortable" onClick={() => handleSort("conversions")}>
                  Conv. <SortIcon field="conversions" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((kw) => (
                <tr key={kw.keyword_id}>
                  <td className="keyword-text" title={`${kw.campaign_name} > ${kw.ad_group_name}`}>
                    {kw.keyword_text}
                  </td>
                  <td><span className="match-badge">{kw.match_type}</span></td>
                  <td><QsScoreBadge score={kw.quality_score} /></td>
                  <td><QsBadge value={kw.expected_ctr} /></td>
                  <td><QsBadge value={kw.ad_relevance} /></td>
                  <td><QsBadge value={kw.landing_page_experience} /></td>
                  <td>{kw.impressions.toLocaleString()}</td>
                  <td>{kw.clicks.toLocaleString()}</td>
                  <td>€{kw.cost.toFixed(2)}</td>
                  <td>{kw.conversions.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
