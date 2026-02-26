import { useState } from "react";
import {
  TrendingUp,
  Clock,
  FileText,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Line,
} from "recharts";
import { fetchTrends, fetchHourly, fetchAds } from "../services/api";
import type { DailyMetrics, HourlyMetrics, AdMetrics } from "../types";

interface Props {
  startDate: string;
  endDate: string;
  campaignId?: string;
}

type TrendMetric = "cost" | "clicks" | "conversions" | "ctr" | "avg_cpc";
type SortKey = "cost" | "clicks" | "ctr" | "conversions" | "conversion_rate";

const METRIC_OPTIONS: { key: TrendMetric; label: string; color: string }[] = [
  { key: "cost", label: "Cost (€)", color: "#ef4444" },
  { key: "clicks", label: "Clicks", color: "#3b82f6" },
  { key: "conversions", label: "Conversions", color: "#10b981" },
  { key: "ctr", label: "CTR (%)", color: "#f59e0b" },
  { key: "avg_cpc", label: "Avg. CPC (€)", color: "#8b5cf6" },
];

function TrendDirection({ values }: { values: number[] }) {
  if (values.length < 4) return <Minus size={14} color="#6b7280" />;
  const mid = Math.floor(values.length / 2);
  const first = values.slice(0, mid).reduce((a, b) => a + b, 0) / mid;
  const second = values.slice(mid).reduce((a, b) => a + b, 0) / (values.length - mid);
  const pctChange = first > 0 ? ((second - first) / first) * 100 : 0;
  if (pctChange > 5) return <ArrowUpRight size={14} color="#10b981" />;
  if (pctChange < -5) return <ArrowDownRight size={14} color="#ef4444" />;
  return <Minus size={14} color="#f59e0b" />;
}

function DailyTrendChart({ daily, metric }: { daily: DailyMetrics[]; metric: TrendMetric }) {
  const config = METRIC_OPTIONS.find((m) => m.key === metric)!;
  const chartData = daily.map((d) => ({
    date: d.date.slice(5), // MM-DD
    [config.label]: d[metric],
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} />
        <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: "#1e1e2e", border: "1px solid #333", borderRadius: 8 }}
          labelStyle={{ color: "#fff" }}
        />
        <Area
          type="monotone"
          dataKey={config.label}
          stroke={config.color}
          fill={config.color}
          fillOpacity={0.15}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function HourlyChart({ hours }: { hours: HourlyMetrics[] }) {
  const chartData = hours.map((h) => ({
    hour: `${h.hour}:00`,
    Clicks: h.clicks,
    Conversions: h.conversions,
    "Conv. Rate": h.conversion_rate,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="hour" tick={{ fill: "#9ca3af", fontSize: 10 }} interval={1} />
        <YAxis yAxisId="left" tick={{ fill: "#9ca3af" }} />
        <YAxis yAxisId="right" orientation="right" tick={{ fill: "#9ca3af" }} />
        <Tooltip
          contentStyle={{ background: "#1e1e2e", border: "1px solid #333", borderRadius: 8 }}
          labelStyle={{ color: "#fff" }}
        />
        <Legend />
        <Bar yAxisId="left" dataKey="Clicks" fill="#3b82f6" radius={[2, 2, 0, 0]} />
        <Line yAxisId="right" type="monotone" dataKey="Conv. Rate" stroke="#10b981" strokeWidth={2} dot={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function AdTable({ ads, sortBy, onSort }: { ads: AdMetrics[]; sortBy: SortKey; onSort: (k: SortKey) => void }) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Ad / Headlines</th>
            <th>Campaign</th>
            <th className="sortable-th" onClick={() => onSort("clicks")}>
              Clicks {sortBy === "clicks" && "↕"}
            </th>
            <th className="sortable-th" onClick={() => onSort("ctr")}>
              CTR {sortBy === "ctr" && "↕"}
            </th>
            <th className="sortable-th" onClick={() => onSort("cost")}>
              Cost {sortBy === "cost" && "↕"}
            </th>
            <th className="sortable-th" onClick={() => onSort("conversions")}>
              Conv. {sortBy === "conversions" && "↕"}
            </th>
            <th className="sortable-th" onClick={() => onSort("conversion_rate")}>
              Conv. Rate {sortBy === "conversion_rate" && "↕"}
            </th>
          </tr>
        </thead>
        <tbody>
          {ads.map((ad) => (
            <tr key={ad.ad_id} className="table-row">
              <td>
                <div style={{ maxWidth: 320 }}>
                  <strong style={{ fontSize: "0.85rem" }}>
                    {ad.headlines.slice(0, 3).join(" | ") || `Ad ${ad.ad_id}`}
                  </strong>
                  {ad.descriptions.length > 0 && (
                    <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginTop: 2 }}>
                      {ad.descriptions[0].slice(0, 80)}{ad.descriptions[0].length > 80 ? "…" : ""}
                    </div>
                  )}
                  {ad.final_url && (
                    <div style={{ fontSize: "0.7rem", color: "var(--accent-blue)", marginTop: 2 }}>
                      {ad.final_url.replace(/^https?:\/\//, "").slice(0, 40)}
                    </div>
                  )}
                </div>
              </td>
              <td style={{ fontSize: "0.8rem" }}>{ad.campaign_name}</td>
              <td>{ad.clicks.toLocaleString()}</td>
              <td>{ad.ctr}%</td>
              <td>€{ad.cost.toFixed(2)}</td>
              <td>{ad.conversions > 0 ? ad.conversions.toFixed(1) : "–"}</td>
              <td>{ad.clicks > 0 ? `${ad.conversion_rate.toFixed(1)}%` : "–"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PerformanceDeepDive({ startDate, endDate, campaignId }: Props) {
  const [trendMetric, setTrendMetric] = useState<TrendMetric>("cost");
  const [adSortBy, setAdSortBy] = useState<SortKey>("cost");
  const [adSortAsc, setAdSortAsc] = useState(false);

  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ["trends", startDate, endDate, campaignId],
    queryFn: () => fetchTrends(startDate, endDate, campaignId),
    retry: 1,
  });

  const { data: hourlyData, isLoading: hourlyLoading } = useQuery({
    queryKey: ["hourly", startDate, endDate, campaignId],
    queryFn: () => fetchHourly(startDate, endDate, campaignId),
    retry: 1,
  });

  const { data: adData, isLoading: adsLoading } = useQuery({
    queryKey: ["ads", startDate, endDate, campaignId],
    queryFn: () => fetchAds(startDate, endDate, campaignId),
    retry: 1,
  });

  const handleAdSort = (key: SortKey) => {
    if (key === adSortBy) {
      setAdSortAsc(!adSortAsc);
    } else {
      setAdSortBy(key);
      setAdSortAsc(false);
    }
  };

  const sortedAds = adData
    ? [...adData.ads].sort((a, b) => {
        const diff = (a[adSortBy] as number) - (b[adSortBy] as number);
        return adSortAsc ? diff : -diff;
      })
    : [];

  return (
    <div className="deep-dive-panel">
      {/* Daily Trends */}
      <div className="card">
        <div className="card-header-row">
          <h3><TrendingUp size={18} style={{ marginRight: 8 }} />Daily Performance Trend</h3>
          <div className="metric-toggle">
            {METRIC_OPTIONS.map((m) => (
              <button
                key={m.key}
                className={`metric-toggle-btn ${trendMetric === m.key ? "active" : ""}`}
                style={trendMetric === m.key ? { borderColor: m.color, color: m.color } : {}}
                onClick={() => setTrendMetric(m.key)}
              >
                {m.label}
                {trendData && (
                  <TrendDirection values={trendData.daily.map((d) => d[m.key] as number)} />
                )}
              </button>
            ))}
          </div>
        </div>
        {trendLoading ? (
          <div className="loading-state"><p>Loading trends...</p></div>
        ) : trendData ? (
          <DailyTrendChart daily={trendData.daily} metric={trendMetric} />
        ) : null}
      </div>

      {/* Hourly Heatmap */}
      <div className="card">
        <h3><Clock size={18} style={{ marginRight: 8 }} />Performance by Hour of Day</h3>
        {hourlyLoading ? (
          <div className="loading-state"><p>Loading hourly data...</p></div>
        ) : hourlyData ? (
          <>
            <HourlyChart hours={hourlyData.hours} />
            <div className="hourly-summary">
              {(() => {
                const bestHour = [...hourlyData.hours]
                  .filter((h) => h.clicks > 3)
                  .sort((a, b) => b.conversion_rate - a.conversion_rate)[0];
                const worstHour = [...hourlyData.hours]
                  .filter((h) => h.clicks > 3)
                  .sort((a, b) => a.conversion_rate - b.conversion_rate)[0];
                const peakClickHour = [...hourlyData.hours].sort((a, b) => b.clicks - a.clicks)[0];
                return (
                  <div className="hourly-insights">
                    {peakClickHour && (
                      <div className="hourly-insight">
                        <strong>Peak Traffic:</strong> {peakClickHour.hour}:00 ({peakClickHour.clicks} clicks)
                      </div>
                    )}
                    {bestHour && (
                      <div className="hourly-insight positive">
                        <strong>Best Conv. Rate:</strong> {bestHour.hour}:00 ({bestHour.conversion_rate.toFixed(1)}%)
                      </div>
                    )}
                    {worstHour && (
                      <div className="hourly-insight negative">
                        <strong>Lowest Conv. Rate:</strong> {worstHour.hour}:00 ({worstHour.conversion_rate.toFixed(1)}%)
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </>
        ) : null}
      </div>

      {/* Ad Copy Performance */}
      <div className="card">
        <h3><FileText size={18} style={{ marginRight: 8 }} />Ad Copy Performance ({adData?.total_ads ?? 0} ads)</h3>
        {adsLoading ? (
          <div className="loading-state"><p>Loading ad data...</p></div>
        ) : adData && adData.ads.length > 0 ? (
          <AdTable ads={sortedAds} sortBy={adSortBy} onSort={handleAdSort} />
        ) : (
          <p style={{ color: "var(--text-muted)", padding: 16 }}>No ad data available.</p>
        )}
      </div>
    </div>
  );
}
