import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import type { CampaignMetrics } from "../types";

interface Props {
  campaigns: CampaignMetrics[];
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"];

export default function CampaignCharts({ campaigns }: Props) {
  const barData = campaigns.map((c) => ({
    name: c.campaign_name.length > 20 ? c.campaign_name.slice(0, 20) + "…" : c.campaign_name,
    Cost: c.cost,
    Clicks: c.clicks,
    Conversions: c.conversions,
  }));

  const pieData = campaigns.map((c) => ({
    name: c.campaign_name.length > 25 ? c.campaign_name.slice(0, 25) + "…" : c.campaign_name,
    value: c.cost,
  }));

  return (
    <div className="charts-grid">
      <div className="card">
        <h3>Cost by Campaign</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
            <YAxis tick={{ fill: "#9ca3af" }} />
            <Tooltip
              contentStyle={{ background: "#1e1e2e", border: "1px solid #333", borderRadius: 8 }}
              labelStyle={{ color: "#fff" }}
            />
            <Bar dataKey="Cost" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3>Budget Distribution</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={3}
              dataKey="value"
              label={({ name, percent }) => `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`}
            >
              {pieData.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "#1e1e2e", border: "1px solid #333", borderRadius: 8 }}
              formatter={(value) => `€${Number(value ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="card full-width">
        <h3>Clicks & Conversions</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
            <YAxis yAxisId="left" tick={{ fill: "#9ca3af" }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fill: "#9ca3af" }} />
            <Tooltip
              contentStyle={{ background: "#1e1e2e", border: "1px solid #333", borderRadius: 8 }}
              labelStyle={{ color: "#fff" }}
            />
            <Legend />
            <Bar yAxisId="left" dataKey="Clicks" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            <Bar yAxisId="right" dataKey="Conversions" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
