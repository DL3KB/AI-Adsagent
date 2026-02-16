import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Smartphone,
  Monitor,
  Tablet,
  HelpCircle,
  MapPin,
  ArrowUpDown,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { fetchSegmentation } from "../services/api";
import type { DeviceMetrics, LocationMetrics } from "../types";

interface Props {
  startDate: string;
  endDate: string;
}

const DEVICE_ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  MOBILE: Smartphone,
  DESKTOP: Monitor,
  TABLET: Tablet,
  OTHER: HelpCircle,
  CONNECTED_TV: Monitor,
};

const DEVICE_LABELS: Record<string, string> = {
  MOBILE: "Mobile",
  DESKTOP: "Desktop",
  TABLET: "Tablet",
  OTHER: "Other",
  CONNECTED_TV: "Connected TV",
};

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

type SortKey = "cost" | "clicks" | "impressions" | "conversions" | "ctr" | "conversion_rate" | "cost_per_conversion";

function SortableHeader({
  label,
  sortKey,
  currentSort,
  sortAsc,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  currentSort: SortKey;
  sortAsc: boolean;
  onSort: (k: SortKey) => void;
}) {
  return (
    <th className="sortable-th" onClick={() => onSort(sortKey)}>
      {label}
      {currentSort === sortKey && (
        <ArrowUpDown size={12} style={{ marginLeft: 4, opacity: 0.7 }} />
      )}
    </th>
  );
}

function DeviceCards({ devices }: { devices: DeviceMetrics[] }) {
  const pieData = devices.map((d) => ({
    name: DEVICE_LABELS[d.device] ?? d.device,
    value: d.cost,
  }));

  const convData = devices.map((d) => ({
    name: DEVICE_LABELS[d.device] ?? d.device,
    ctr: d.ctr,
    conv_rate: d.conversion_rate,
    cpc: d.avg_cpc,
  }));

  return (
    <div className="device-section">
      <h3>
        <Monitor size={18} /> Device Segmentation
      </h3>

      <div className="device-grid">
        {devices.map((d) => {
          const Icon = DEVICE_ICONS[d.device] ?? HelpCircle;
          const label = DEVICE_LABELS[d.device] ?? d.device;
          return (
            <div key={d.device} className="device-card">
              <div className="device-card-header">
                <Icon size={22} />
                <span className="device-label">{label}</span>
                <span className="device-share">{d.cost_share}% Budget</span>
              </div>
              <div className="device-kpis">
                <div className="device-kpi">
                  <span className="kpi-value">
                    €{d.cost.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                  <span className="kpi-label">Cost</span>
                </div>
                <div className="device-kpi">
                  <span className="kpi-value">{d.clicks.toLocaleString("en-US")}</span>
                  <span className="kpi-label">Clicks</span>
                </div>
                <div className="device-kpi">
                  <span className="kpi-value">{d.ctr}%</span>
                  <span className="kpi-label">CTR</span>
                </div>
                <div className="device-kpi">
                  <span className="kpi-value">{d.conversion_rate}%</span>
                  <span className="kpi-label">Conv. Rate</span>
                </div>
                <div className="device-kpi">
                  <span className="kpi-value">
                    €{d.avg_cpc.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                  <span className="kpi-label">Avg. CPC</span>
                </div>
                <div className="device-kpi">
                  <span className="kpi-value">
                    {d.conversions.toLocaleString("en-US", { minimumFractionDigits: 1 })}
                  </span>
                  <span className="kpi-label">Conversions</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="device-charts">
        <div className="device-chart-box">
          <h4>Cost Distribution</h4>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
              >
                {pieData.map((_entry, idx) => (
                  <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) =>
                  `€${value.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
                }
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="device-chart-box">
          <h4>Performance Comparison</h4>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={convData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: 8,
                }}
              />
              <Legend />
              <Bar dataKey="ctr" name="CTR %" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar
                dataKey="conv_rate"
                name="Conv. Rate %"
                fill="#10b981"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function LocationTable({ locations }: { locations: LocationMetrics[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("cost");
  const [sortAsc, setSortAsc] = useState(false);
  const [filter, setFilter] = useState("");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const filtered = locations.filter((loc) =>
    loc.location_name.toLowerCase().includes(filter.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const diff = (a[sortKey] as number) - (b[sortKey] as number);
    return sortAsc ? diff : -diff;
  });

  return (
    <div className="location-section">
      <div className="location-header">
        <h3>
          <MapPin size={18} /> Location Performance
        </h3>
        <input
          className="st-filter"
          placeholder="Search location…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="table-scroll">
        <table className="st-table">
          <thead>
            <tr>
              <th>Location</th>
              <th>Type</th>
              <SortableHeader
                label="Cost"
                sortKey="cost"
                currentSort={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortableHeader
                label="Clicks"
                sortKey="clicks"
                currentSort={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortableHeader
                label="Impr."
                sortKey="impressions"
                currentSort={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortableHeader
                label="CTR"
                sortKey="ctr"
                currentSort={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortableHeader
                label="Conv."
                sortKey="conversions"
                currentSort={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortableHeader
                label="Conv. Rate"
                sortKey="conversion_rate"
                currentSort={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortableHeader
                label="Cost/Conv."
                sortKey="cost_per_conversion"
                currentSort={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
            </tr>
          </thead>
          <tbody>
            {sorted.map((loc, idx) => (
              <tr key={`${loc.location_id}-${idx}`}>
                <td className="loc-name">{loc.location_name}</td>
                <td>
                  <span className="match-badge">{loc.location_type || "–"}</span>
                </td>
                <td>
                  €{loc.cost.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </td>
                <td>{loc.clicks.toLocaleString("en-US")}</td>
                <td>{loc.impressions.toLocaleString("en-US")}</td>
                <td>{loc.ctr}%</td>
                <td>{loc.conversions.toLocaleString("en-US", { minimumFractionDigits: 1 })}</td>
                <td>{loc.conversion_rate}%</td>
                <td>
                  {loc.cost_per_conversion > 0
                    ? `€${loc.cost_per_conversion.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
                    : "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sorted.length === 0 && (
        <p className="text-muted" style={{ textAlign: "center", padding: 20 }}>
          No location data available.
        </p>
      )}
    </div>
  );
}

export default function DeviceLocationPanel({ startDate, endDate }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["segmentation", startDate, endDate],
    queryFn: () => fetchSegmentation(startDate, endDate),
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="segmentation-panel loading-state">
        <Monitor size={24} className="spin" />
        <span>Loading segmentation data…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="segmentation-panel error-state">
        <p className="text-red">
          Error loading: {error instanceof Error ? error.message : "Unknown"}
        </p>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="segmentation-panel">
      {data.devices.length > 0 && <DeviceCards devices={data.devices} />}
      {data.locations.length > 0 && <LocationTable locations={data.locations} />}
    </div>
  );
}
