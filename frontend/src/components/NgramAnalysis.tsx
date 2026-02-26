import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Hash, ChevronDown, ChevronUp } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { fetchNgrams } from "../services/api";
import type { NgramMetrics } from "../types";

interface Props {
  startDate: string;
  endDate: string;
  campaignId?: string;
}

const N_LABELS: Record<number, string> = { 1: "Single words", 2: "2-word phrases", 3: "3-word phrases" };
const COLORS = ["#3b82f6", "#8b5cf6", "#06b6d4"];

export default function NgramAnalysis({ startDate, endDate, campaignId }: Props) {
  const [filterN, setFilterN] = useState<number | null>(null);
  const [sortField, setSortField] = useState<keyof NgramMetrics>("cost");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [expandedNgram, setExpandedNgram] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["ngrams", startDate, endDate, campaignId],
    queryFn: () => fetchNgrams(startDate, endDate, campaignId),
  });

  if (isLoading) {
    return (
      <div className="panel loading-state">
        <Loader2 size={32} className="spin" />
        <p>Analyzing search term n-grams...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="panel error-state">
        <p>Failed to load n-gram analysis</p>
      </div>
    );
  }

  const filtered = filterN ? data.ngrams.filter((ng) => ng.n === filterN) : data.ngrams;

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortField] as number;
    const bVal = b[sortField] as number;
    return sortDir === "desc" ? bVal - aVal : aVal - bVal;
  });

  const handleSort = (field: keyof NgramMetrics) => {
    if (sortField === field) {
      setSortDir(sortDir === "desc" ? "asc" : "desc");
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ field }: { field: keyof NgramMetrics }) =>
    sortField === field ? (
      sortDir === "desc" ? <ChevronDown size={14} /> : <ChevronUp size={14} />
    ) : null;

  // Chart data: top 15 by cost
  const chartData = sorted.slice(0, 15).map((ng) => ({
    name: ng.ngram,
    cost: ng.cost,
    conversions: ng.conversions,
    n: ng.n,
  }));

  return (
    <div className="ngram-panel">
      <div className="panel">
        <div className="panel-header">
          <h2><Hash size={20} /> N-Gram Analysis</h2>
          <span className="badge">{data.total_ngrams} patterns found</span>
        </div>

        {/* Filter buttons */}
        <div className="ngram-filters">
          <button
            className={`ngram-filter-btn ${filterN === null ? "active" : ""}`}
            onClick={() => setFilterN(null)}
          >
            All ({data.ngrams.length})
          </button>
          {[1, 2, 3].map((n) => {
            const count = data.ngrams.filter((ng) => ng.n === n).length;
            return (
              <button
                key={n}
                className={`ngram-filter-btn ${filterN === n ? "active" : ""}`}
                onClick={() => setFilterN(filterN === n ? null : n)}
              >
                {N_LABELS[n]} ({count})
              </button>
            );
          })}
        </div>

        {/* Bar chart */}
        {chartData.length > 0 && (
          <div className="ngram-chart">
            <h3>Top N-Grams by Cost</h3>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 120, right: 20, top: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tickFormatter={(v) => `€${v.toFixed(0)}`} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value: number | string | undefined, name: string | undefined) =>
                    name === "cost" ? [`€${Number(value ?? 0).toFixed(2)}`, "Cost"] : [Number(value ?? 0).toFixed(1), "Conversions"]
                  }
                />
                <Bar dataKey="cost" name="cost" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={COLORS[(entry.n - 1) % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Table */}
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>N-Gram</th>
                <th>Type</th>
                <th className="sortable" onClick={() => handleSort("frequency")}>
                  Freq. <SortIcon field="frequency" />
                </th>
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
              {sorted.map((ng) => (
                <>
                  <tr
                    key={ng.ngram}
                    className={`ngram-row ${expandedNgram === ng.ngram ? "expanded" : ""}`}
                    onClick={() => setExpandedNgram(expandedNgram === ng.ngram ? null : ng.ngram)}
                    style={{ cursor: "pointer" }}
                  >
                    <td className="ngram-text">
                      <strong>{ng.ngram}</strong>
                    </td>
                    <td>
                      <span className={`ngram-type-badge n${ng.n}`}>
                        {ng.n}-gram
                      </span>
                    </td>
                    <td>{ng.frequency}</td>
                    <td>{ng.impressions.toLocaleString()}</td>
                    <td>{ng.clicks.toLocaleString()}</td>
                    <td>€{ng.cost.toFixed(2)}</td>
                    <td>{ng.ctr.toFixed(2)}%</td>
                    <td>{ng.conversions.toFixed(1)}</td>
                    <td>{ng.conversion_rate.toFixed(2)}%</td>
                    <td>{ng.cost_per_conversion > 0 ? `€${ng.cost_per_conversion.toFixed(2)}` : "—"}</td>
                  </tr>
                  {expandedNgram === ng.ngram && ng.search_terms.length > 0 && (
                    <tr key={`${ng.ngram}-details`} className="ngram-details-row">
                      <td colSpan={10}>
                        <div className="ngram-search-terms">
                          <strong>Example search terms:</strong>
                          <ul>
                            {ng.search_terms.map((st, i) => (
                              <li key={i}>{st}</li>
                            ))}
                          </ul>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
