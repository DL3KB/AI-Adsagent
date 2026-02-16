import { useState } from "react";
import {
  Play,
  X,
  Check,
  AlertTriangle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Zap,
  Pause,
  DollarSign,
  MinusCircle,
  ArrowRightLeft,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { applyProposals, rejectProposal } from "../services/api";
import type { Proposal, ProposalAction, ApplyProposalsResponse } from "../types";

interface Props {
  proposals: Proposal[];
  onProposalsUpdated: (proposals: Proposal[]) => void;
}

const ACTION_LABELS: Record<ProposalAction, string> = {
  pause_keyword: "Pause Keyword",
  enable_keyword: "Enable Keyword",
  pause_campaign: "Pause Campaign",
  enable_campaign: "Enable Campaign",
  pause_ad_group: "Pause Ad Group",
  enable_ad_group: "Enable Ad Group",
  add_negative_keyword: "Add Negative Keyword",
  change_keyword_bid: "Change Bid",
  change_campaign_budget: "Change Budget",
  change_keyword_match_type: "Change Match Type",
};

function getActionIcon(action: ProposalAction) {
  switch (action) {
    case "pause_keyword":
    case "pause_campaign":
    case "pause_ad_group":
      return <Pause size={16} />;
    case "enable_keyword":
    case "enable_campaign":
    case "enable_ad_group":
      return <Play size={16} />;
    case "change_keyword_bid":
    case "change_campaign_budget":
      return <DollarSign size={16} />;
    case "add_negative_keyword":
      return <MinusCircle size={16} />;
    case "change_keyword_match_type":
      return <ArrowRightLeft size={16} />;
    default:
      return <Zap size={16} />;
  }
}

function PriorityDot({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    high: "#ef4444",
    medium: "#f59e0b",
    low: "#10b981",
  };
  return (
    <span
      className="priority-dot"
      style={{ backgroundColor: colors[priority] || colors.medium }}
      title={`Priority: ${priority}`}
    />
  );
}

function ProposalCard({
  proposal,
  isSelected,
  onToggleSelect,
  onReject,
}: {
  proposal: Proposal;
  isSelected: boolean;
  onToggleSelect: () => void;
  onReject: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isPending = proposal.status === "pending";
  const isApplied = proposal.status === "applied";
  const isFailed = proposal.status === "failed";
  const isRejected = proposal.status === "rejected";

  return (
    <div
      className={`proposal-card ${isApplied ? "applied" : ""} ${isFailed ? "failed" : ""} ${isRejected ? "rejected" : ""}`}
    >
      <div className="proposal-header">
        <div className="proposal-left">
          {isPending && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggleSelect}
              className="proposal-checkbox"
            />
          )}
          {isApplied && <CheckCircle2 size={18} color="#10b981" />}
          {isFailed && <XCircle size={18} color="#ef4444" />}
          {isRejected && <X size={18} color="#6b7280" />}
          <PriorityDot priority={proposal.priority} />
          <span className="proposal-action-badge">
            {getActionIcon(proposal.action)}
            {ACTION_LABELS[proposal.action]}
          </span>
          <span className="proposal-title">{proposal.title}</span>
        </div>
        <div className="proposal-right">
          {isPending && (
            <button
              className="btn-icon-sm reject-btn"
              onClick={onReject}
              title="Dismiss"
            >
              <X size={14} />
            </button>
          )}
          <button
            className="btn-icon-sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="proposal-details">
          <div className="proposal-detail-row">
            <strong>Reason:</strong>
            <span>{proposal.reason}</span>
          </div>
          <div className="proposal-detail-row">
            <strong>Expected Impact:</strong>
            <span>{proposal.expected_impact}</span>
          </div>

          {proposal.campaign_name && (
            <div className="proposal-detail-row">
              <strong>Campaign:</strong>
              <span>{proposal.campaign_name}</span>
            </div>
          )}
          {proposal.ad_group_name && (
            <div className="proposal-detail-row">
              <strong>Ad Group:</strong>
              <span>{proposal.ad_group_name}</span>
            </div>
          )}
          {proposal.keyword_text && (
            <div className="proposal-detail-row">
              <strong>Keyword:</strong>
              <span>"{proposal.keyword_text}"</span>
            </div>
          )}

          {(proposal.current_value || proposal.new_value) && (
            <div className="proposal-change-row">
              {proposal.current_value && (
                <span className="change-old">{proposal.current_value}</span>
              )}
              {proposal.current_value && proposal.new_value && (
                <span className="change-arrow">→</span>
              )}
              {proposal.new_value && (
                <span className="change-new">{proposal.new_value}</span>
              )}
            </div>
          )}

          {isFailed && proposal.error_message && (
            <div className="proposal-error">
              <AlertTriangle size={14} />
              {proposal.error_message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProposalsPanel({ proposals, onProposalsUpdated }: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showConfirm, setShowConfirm] = useState(false);
  const [lastResult, setLastResult] = useState<ApplyProposalsResponse | null>(null);

  const pendingProposals = proposals.filter((p) => p.status === "pending");
  const appliedProposals = proposals.filter((p) => p.status === "applied");
  const failedProposals = proposals.filter((p) => p.status === "failed");

  const applyMutation = useMutation({
    mutationFn: (ids: string[]) => applyProposals(ids),
    onSuccess: (result: ApplyProposalsResponse) => {
      setLastResult(result);
      setShowConfirm(false);
      setSelectedIds(new Set());

      // Update proposal statuses
      const updated = proposals.map((p) => {
        const r = result.results.find((res) => res.proposal_id === p.id);
        if (r) {
          return {
            ...p,
            status: r.success ? ("applied" as const) : ("failed" as const),
            error_message: r.success ? undefined : r.message,
          };
        }
        return p;
      });
      onProposalsUpdated(updated);
    },
  });

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(pendingProposals.map((p) => p.id)));
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  const handleReject = async (proposalId: string) => {
    try {
      await rejectProposal(proposalId);
      const updated = proposals.map((p) =>
        p.id === proposalId ? { ...p, status: "rejected" as const } : p
      );
      onProposalsUpdated(updated);
    } catch {
      // Silently handle - still update UI
      const updated = proposals.map((p) =>
        p.id === proposalId ? { ...p, status: "rejected" as const } : p
      );
      onProposalsUpdated(updated);
    }
  };

  if (proposals.length === 0) {
    return null;
  }

  return (
    <div className="card proposals-panel">
      <div className="proposals-header">
        <h3>
          <Zap size={20} color="#f59e0b" />
                    Change Proposals ({proposals.length})
        </h3>

        {pendingProposals.length > 0 && (
          <div className="proposals-actions">
            <button className="btn-text" onClick={selectAll}>
              Select All
            </button>
            <button className="btn-text" onClick={deselectAll}>
              Deselect All
            </button>
            <button
              className="btn-primary btn-apply"
              disabled={selectedIds.size === 0 || applyMutation.isPending}
              onClick={() => setShowConfirm(true)}
            >
              {applyMutation.isPending ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Applying...
                </>
              ) : (
                <>
                  <Check size={16} />
                  {selectedIds.size} change{selectedIds.size !== 1 ? "s" : ""} to apply
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Status summary */}
      {(appliedProposals.length > 0 || failedProposals.length > 0) && (
        <div className="proposals-status-bar">
          {appliedProposals.length > 0 && (
            <span className="status-success">
              <CheckCircle2 size={14} />
              {appliedProposals.length} applied
            </span>
          )}
          {failedProposals.length > 0 && (
            <span className="status-error">
              <XCircle size={14} />
              {failedProposals.length} failed
            </span>
          )}
        </div>
      )}

      {/* Last result notification */}
      {lastResult && (
        <div className={`proposals-notification ${lastResult.total_failed > 0 ? "has-errors" : "all-success"}`}>
          {lastResult.total_failed === 0 ? (
            <>
              <CheckCircle2 size={16} />
              All {lastResult.total_applied} changes applied successfully!
            </>
          ) : (
            <>
              <AlertTriangle size={16} />
              {lastResult.total_applied} applied, {lastResult.total_failed} failed
            </>
          )}
          <button className="btn-text" onClick={() => setLastResult(null)}>
            ×
          </button>
        </div>
      )}

      {/* Proposals list */}
      <div className="proposals-list">
        {proposals.map((proposal) => (
          <ProposalCard
            key={proposal.id}
            proposal={proposal}
            isSelected={selectedIds.has(proposal.id)}
            onToggleSelect={() => toggleSelect(proposal.id)}
            onReject={() => handleReject(proposal.id)}
          />
        ))}
      </div>

      {/* Confirmation modal */}
      {showConfirm && (
        <div className="confirm-overlay">
          <div className="confirm-dialog">
            <h3>
              <AlertTriangle size={22} color="#f59e0b" />
              Confirm Changes
            </h3>
            <p>
              The following {selectedIds.size} change{selectedIds.size !== 1 ? "s" : ""} will be applied to Google Ads:
            </p>
            <ul className="confirm-list">
              {proposals
                .filter((p) => selectedIds.has(p.id))
                .map((p) => (
                  <li key={p.id}>
                    <span className="confirm-action">
                      {ACTION_LABELS[p.action]}:
                    </span>{" "}
                    {p.title}
                  </li>
                ))}
            </ul>
            <p className="confirm-warning">
              This action cannot be automatically undone.
            </p>
            <div className="confirm-buttons">
              <button
                className="btn-secondary"
                onClick={() => setShowConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="btn-danger"
                onClick={() => applyMutation.mutate(Array.from(selectedIds))}
                disabled={applyMutation.isPending}
              >
                {applyMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="spin" /> Applying...
                  </>
                ) : (
                  <>
                    <Zap size={16} /> Apply Now
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
