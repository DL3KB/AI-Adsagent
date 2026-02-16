import {
  TrendingUp,
  MousePointerClick,
  Eye,
  Target,
  DollarSign,
  BarChart3,
} from "lucide-react";
import type { CampaignOverview } from "../types";

interface Props {
  data: CampaignOverview;
}

export default function MetricsCards({ data }: Props) {
  const cards = [
    {
      title: "Total Cost",
      value: `€${data.total_cost.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      icon: DollarSign,
      color: "#ef4444",
    },
    {
      title: "Clicks",
      value: data.total_clicks.toLocaleString("en-US"),
      icon: MousePointerClick,
      color: "#3b82f6",
    },
    {
      title: "Impressions",
      value: data.total_impressions.toLocaleString("en-US"),
      icon: Eye,
      color: "#8b5cf6",
    },
    {
      title: "Conversions",
      value: data.total_conversions.toLocaleString("en-US", { minimumFractionDigits: 1 }),
      icon: Target,
      color: "#10b981",
    },
    {
      title: "Avg. CTR",
      value: `${data.avg_ctr}%`,
      icon: TrendingUp,
      color: "#f59e0b",
    },
    {
      title: "Avg. CPC",
      value: `€${data.avg_cpc.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      icon: BarChart3,
      color: "#06b6d4",
    },
  ];

  return (
    <div className="metrics-grid">
      {cards.map((card) => (
        <div key={card.title} className="metric-card">
          <div className="metric-header">
            <span className="metric-title">{card.title}</span>
            <card.icon size={20} color={card.color} />
          </div>
          <div className="metric-value">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
