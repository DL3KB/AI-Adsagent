import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";
import { fetchAuditLog } from "../services/api";
import type { AuditLogEntry } from "../types";

const PAGE_SIZE = 20;

const ACTION_LABELS: Record<string, string> = {
  PAUSE_CAMPAIGN: "Campaign Paused",
  ENABLE_CAMPAIGN: "Campaign Enabled",
  ADJUST_BUDGET: "Budget Adjusted",
  ADJUST_BID: "Bid Adjusted",
  PAUSE_KEYWORD: "Keyword Paused",
  ENABLE_KEYWORD: "Keyword Enabled",
  ADD_NEGATIVE_KEYWORD: "Negative Keyword Added",
  CHANGE_BID_STRATEGY: "Bid Strategy Changed",
  ADJUST_TARGET_CPA: "Target CPA Adjusted",
  ADJUST_TARGET_ROAS: "Target ROAS Adjusted",
};

function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString("en-US", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function EntryRow({ entry }: { entry: AuditLogEntry }) {
  const actionLabel =
    ACTION_LABELS[entry.action] || entry.action.replace(/_/g, " ");

  return (
    <tr className={entry.success ? "" : "audit-row-failed"}>
      <td className="audit-time">
        <Clock size={14} />
        {formatTimestamp(entry.timestamp)}
      </td>
      <td>
        <span className="audit-action-badge">{actionLabel}</span>
      </td>
      <td className="audit-target">
        {entry.campaign_name && (
          <span className="audit-campaign">{entry.campaign_name}</span>
        )}
        {entry.keyword_text && (
          <span className="audit-keyword">
            <em>{entry.keyword_text}</em>
          </span>
        )}
      </td>
      <td className="audit-values">
        {entry.old_value != null && (
          <span className="audit-old">{entry.old_value}</span>
        )}
        {entry.old_value != null && entry.new_value != null && (
          <span className="audit-arrow">→</span>
        )}
        {entry.new_value != null && (
          <span className="audit-new">{entry.new_value}</span>
        )}
      </td>
      <td>
        {entry.success ? (
          <CheckCircle size={16} className="text-green" />
        ) : (
          <span className="audit-error-cell">
            <XCircle size={16} className="text-red" />
            {entry.error_message && (
              <span className="audit-error-msg">{entry.error_message}</span>
            )}
          </span>
        )}
      </td>
    </tr>
  );
}

export default function AuditLogPanel() {
  const [page, setPage] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["audit-log", page],
    queryFn: () => fetchAuditLog(PAGE_SIZE, page * PAGE_SIZE),
  });

  if (isLoading) {
    return (
      <div className="audit-log-panel loading-state">
        <Activity size={24} className="spin" />
        <span>Loading change log…</span>
      </div>
    );
  }

  const entries = data?.entries ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  if (entries.length === 0 && page === 0) {
    return (
      <div className="audit-log-panel empty-state">
        <Activity size={32} />
        <p>No changes logged yet.</p>
        <p className="text-sm text-muted">
          Once proposals are applied, they will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="audit-log-panel">
      <div className="audit-log-header">
        <h3>
          <Activity size={18} /> Change Log
        </h3>
        <span className="audit-total">{total} entries total</span>
      </div>

      <div className="table-scroll">
        <table className="audit-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Target</th>
              <th>Values</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry: AuditLogEntry) => (
              <EntryRow key={entry.id} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="audit-pagination">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft size={16} /> Back
          </button>
          <span>
            Page {page + 1} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
