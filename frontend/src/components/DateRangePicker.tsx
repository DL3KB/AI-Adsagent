import { Calendar } from "lucide-react";

interface Props {
  startDate: string;
  endDate: string;
  onStartChange: (date: string) => void;
  onEndChange: (date: string) => void;
}

export default function DateRangePicker({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
}: Props) {
  const presets = [
    { label: "7 Days", days: 7 },
    { label: "14 Days", days: 14 },
    { label: "30 Days", days: 30 },
    { label: "90 Days", days: 90 },
  ];

  const setPreset = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    onStartChange(start.toISOString().split("T")[0]);
    onEndChange(end.toISOString().split("T")[0]);
  };

  return (
    <div className="date-range-picker">
      <Calendar size={18} color="#9ca3af" />
      <input type="date" value={startDate} onChange={(e) => onStartChange(e.target.value)} />
      <span className="date-separator">–</span>
      <input type="date" value={endDate} onChange={(e) => onEndChange(e.target.value)} />
      <div className="date-presets">
        {presets.map((p) => (
          <button key={p.days} className="date-preset" onClick={() => setPreset(p.days)}>
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
