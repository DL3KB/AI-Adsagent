import { ChevronDown, X } from "lucide-react";
import type { CampaignMetrics } from "../types";

interface Props {
  campaigns: CampaignMetrics[];
  selectedId?: string;
  onChange: (campaignId: string | undefined) => void;
}

export default function CampaignSelector({ campaigns, selectedId, onChange }: Props) {
  const selected = campaigns.find((c) => c.campaign_id === selectedId);

  return (
    <div className="campaign-selector">
      <div className="campaign-select-wrapper">
        <select
          className="campaign-select"
          value={selectedId ?? ""}
          onChange={(e) => onChange(e.target.value || undefined)}
        >
          <option value="">All Campaigns</option>
          {campaigns.map((c) => (
            <option key={c.campaign_id} value={c.campaign_id}>
              {c.campaign_name}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="campaign-select-icon" />
      </div>
      {selected && (
        <button
          className="campaign-clear-btn"
          onClick={() => onChange(undefined)}
          title="Show all campaigns"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
