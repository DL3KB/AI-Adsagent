import { useState } from "react";
import { Search, AlertTriangle, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchSearchTerms, getExportUrl } from "../services/api";
import type { SearchTermMetrics } from "../types";

interface Props {
  startDate: string;
  endDate: string;
  campaignId?: string;
}

type SortKey = "cost" | "clicks" | "impressions" | "conversions" | "ctr" | "conversion_rate";

export default function SearchTermsPanel({ startDate, endDate, campaignId }: Props) {
  const [sortBy, setSortBy] = useState<SortKey>("cost");
  const [sortAsc, setSortAsc] = useState(false);
  const [filter, setFilter] = useState("");
  const [showOnlyWaste, setShowOnlyWaste] = useState(false);

  const { data: report, isLoading, error } = useQuery({
    queryKey: ["search-terms", startDate, endDate, campaignId],
    queryFn: () => fetchSearchTerms(campaignId, startDate, endDate),
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="card search-terms-panel">
        <div className="loading-state"><p>Loading search terms...</p></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card search-terms-panel">
        <div className="error-state">
          <AlertTriangle size={24} color="#ef4444" />
          <p>{error instanceof Error ? error.message : "Error loading data"}</p>
        </div>
      </div>
    );
  }

  if (!report) return null;

  // Filter & sort
  let terms = report.search_terms;
  if (filter) {
    const lc = filter.toLowerCase();
    terms = terms.filter((t) => t.search_term.toLowerCase().includes(lc));
  }
  if (showOnlyWaste) {
    terms = terms.filter((t) => t.clicks > 0 && t.conversions === 0);
  }

  terms = [...terms].sort((a, b) => {
    const va = a[sortBy] as number;
    const vb = b[sortBy] as number;
    return sortAsc ? va - vb : vb - va;
  });

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortBy(key);
      setSortAsc(false);
    }
  };

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th onClick={() => handleSort(field)} className="sortable-th">
      {label}
      {sortBy === field && (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
    </th>
  );

  const exportUrl = getExportUrl("search-terms", startDate, endDate, campaignId);

  return (
    <div className="card search-terms-panel">
      <div className="st-header">
        <h2>
          <Search size={20} color="#8b5cf6" />
          Search Terms Report
        </h2>
        <div className="st-stats">
          <span>{report.total_search_terms} search terms</span>
          <span className="st-stat-divider">|</span>
          <span className="st-waste">
            <AlertTriangle size={14} />
            €{report.irrelevant_spend.toLocaleString("en-US", { minimumFractionDigits: 2 })} without conversion
          </span>
          <a href={exportUrl} className="btn-icon-sm" title="CSV Export" download>
            <ExternalLink size={16} />
          </a>
        </div>
      </div>

      <div className="st-controls">
        <input
          type="text"
          className="st-filter"
          placeholder="Filter search terms..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <label className="st-waste-toggle">
          <input
            type="checkbox"
            checked={showOnlyWaste}
            onChange={(e) => setShowOnlyWaste(e.target.checked)}
          />
          No conversions only
        </label>
      </div>

      <div className="table-wrapper">
        <table className="data-table st-table">
          <thead>
            <tr>
              <th>Search Term</th>
              <th>Keyword</th>
              <th>Match</th>
              <th>Campaign</th>
              <SortHeader label="Imp." field="impressions" />
              <SortHeader label="Clicks" field="clicks" />
              <SortHeader label="CTR" field="ctr" />
              <SortHeader label="Cost" field="cost" />
              <SortHeader label="Conv." field="conversions" />
              <SortHeader label="Conv.Rate" field="conversion_rate" />
            </tr>
          </thead>
          <tbody>
            {terms.map((st: SearchTermMetrics, i: number) => {
              const isWaste = st.clicks > 0 && st.conversions === 0;
              return (
                <tr key={i} className={isWaste ? "row-waste" : ""}>
                  <td className="st-term">{st.search_term}</td>
                  <td className="st-keyword">"{st.keyword_text}"</td>
                  <td><span className="match-badge">{st.match_type}</span></td>
                  <td className="st-campaign">{st.campaign_name}</td>
                  <td>{st.impressions.toLocaleString("en-US")}</td>
                  <td>{st.clicks}</td>
                  <td>{st.ctr}%</td>
                  <td>€{st.cost.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                  <td className={st.conversions === 0 && st.clicks > 0 ? "text-red" : ""}>
                    {st.conversions}
                  </td>
                  <td>{st.conversion_rate}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {terms.length === 0 && (
        <div className="analysis-empty">
          <Search size={32} color="#555" />
          <p>No search terms found for this filter.</p>
        </div>
      )}
    </div>
  );
}
