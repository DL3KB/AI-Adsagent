import {
  TrendingUp,
  TrendingDown,
  Minus,
  MousePointerClick,
  Eye,
  Target,
  DollarSign,
  BarChart3,
  Percent,
  ShoppingCart,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchComparison } from "../services/api";
import type { MetricChange, ComparisonOverview } from "../types";

interface Props {
  startDate: string;
  endDate: string;
}

interface CardConfig {
  title: string;
  key: keyof ComparisonOverview;
  icon: React.ComponentType<{ size?: number; color?: string }>;
  color: string;
  format: (v: number) => string;
  suffix?: string;
}

const CARDS: CardConfig[] = [
  {
    title: "Cost",
    key: "cost",
    icon: DollarSign,
    color: "#ef4444",
    format: (v) => `€${v.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
  },
  {
    title: "Clicks",
    key: "clicks",
    icon: MousePointerClick,
    color: "#3b82f6",
    format: (v) => v.toLocaleString("en-US"),
  },
  {
    title: "Impressions",
    key: "impressions",
    icon: Eye,
    color: "#8b5cf6",
    format: (v) => v.toLocaleString("en-US"),
  },
  {
    title: "Conversions",
    key: "conversions",
    icon: Target,
    color: "#10b981",
    format: (v) => v.toLocaleString("en-US", { minimumFractionDigits: 1 }),
  },
  {
    title: "Avg. CTR",
    key: "ctr",
    icon: TrendingUp,
    color: "#f59e0b",
    format: (v) => `${v}%`,
  },
  {
    title: "Avg. CPC",
    key: "avg_cpc",
    icon: BarChart3,
    color: "#06b6d4",
    format: (v) => `€${v.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
  },
  {
    title: "Conv. Rate",
    key: "conversion_rate",
    icon: Percent,
    color: "#a78bfa",
    format: (v) => `${v}%`,
  },
  {
    title: "Cost/Conv.",
    key: "cost_per_conversion",
    icon: ShoppingCart,
    color: "#fb923c",
    format: (v) => `€${v.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
  },
];

function TrendArrow({ change }: { change: MetricChange }) {
  if (Math.abs(change.change_pct) < 0.5) {
    return (
      <div className="trend-indicator trend-neutral">
        <Minus size={14} />
        <span>0%</span>
      </div>
    );
  }

  const isUp = change.change > 0;
  const Icon = isUp ? TrendingUp : TrendingDown;
  const className = change.improved ? "trend-positive" : "trend-negative";

  return (
    <div className={`trend-indicator ${className}`}>
      <Icon size={14} />
      <span>{isUp ? "+" : ""}{change.change_pct.toFixed(1)}%</span>
    </div>
  );
}

export default function ComparisonCards({ startDate, endDate }: Props) {
  const { data: comparison, isLoading } = useQuery({
    queryKey: ["comparison", startDate, endDate],
    queryFn: () => fetchComparison(startDate, endDate),
    retry: 1,
  });

  if (isLoading || !comparison) return null;

  const days = Math.ceil(
    (new Date(comparison.current_period.end_date).getTime() -
      new Date(comparison.current_period.start_date).getTime()) /
      (1000 * 60 * 60 * 24)
  );

  return (
    <div className="comparison-section">
      <div className="comparison-header">
        <h3>
          Period vs. Previous Period
          <span className="comparison-period">
            ({days} days vs. previous {days} days)
          </span>
        </h3>
      </div>
      <div className="metrics-grid comparison-grid">
        {CARDS.map((card) => {
          const change = comparison[card.key] as MetricChange;
          return (
            <div key={card.title} className="metric-card">
              <div className="metric-header">
                <span className="metric-title">{card.title}</span>
                <card.icon size={20} color={card.color} />
              </div>
              <div className="metric-value">{card.format(change.current)}</div>
              <div className="metric-comparison">
                <TrendArrow change={change} />
                <span className="metric-previous">
                  Previous: {card.format(change.previous)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
