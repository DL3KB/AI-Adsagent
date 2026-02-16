import type { CampaignMetrics } from "../types";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

interface Props {
  campaigns: CampaignMetrics[];
  onSelect: (campaignId: string) => void;
  selectedId?: string;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ENABLED: "#10b981",
    PAUSED: "#f59e0b",
    REMOVED: "#ef4444",
  };
  return (
    <span
      className="status-badge"
      style={{ backgroundColor: colors[status] || "#6b7280" }}
    >
      {status}
    </span>
  );
}

function CtrIndicator({ ctr }: { ctr: number }) {
  if (ctr >= 5)
    return <ArrowUpRight size={14} color="#10b981" />;
  if (ctr >= 3)
    return <Minus size={14} color="#f59e0b" />;
  return <ArrowDownRight size={14} color="#ef4444" />;
}

export default function CampaignTable({ campaigns, onSelect, selectedId }: Props) {
  return (
    <div className="card">
      <h2>Campaigns</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Status</th>
              <th>Impressions</th>
              <th>Clicks</th>
              <th>CTR</th>
              <th>CPC</th>
              <th>Cost</th>
              <th>Conv.</th>
              <th>Conv. Rate</th>
              <th>Cost/Conv.</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr
                key={c.campaign_id}
                className={`table-row ${selectedId === c.campaign_id ? "selected" : ""}`}
                onClick={() => onSelect(c.campaign_id)}
              >
                <td className="campaign-name">{c.campaign_name}</td>
                <td><StatusBadge status={c.status} /></td>
                <td>{c.impressions.toLocaleString("en-US")}</td>
                <td>{c.clicks.toLocaleString("en-US")}</td>
                <td>
                  <span className="ctr-cell">
                    <CtrIndicator ctr={c.ctr} />
                    {c.ctr}%
                  </span>
                </td>
                <td>€{c.avg_cpc.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                <td>€{c.cost.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                <td>{c.conversions.toLocaleString("en-US", { minimumFractionDigits: 1 })}</td>
                <td>{c.conversion_rate}%</td>
                <td>€{c.cost_per_conversion.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
