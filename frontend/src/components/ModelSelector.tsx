import { ChevronDown, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchModels } from "../services/api";
import type { GeminiModel } from "../types";

interface Props {
  selectedModel: string;
  onChange: (model: string) => void;
}

export default function ModelSelector({ selectedModel, onChange }: Props) {
  const { data: models } = useQuery<GeminiModel[]>({
    queryKey: ["models"],
    queryFn: fetchModels,
    staleTime: Infinity,
  });

  const selected = models?.find((m) => m.id === selectedModel);

  return (
    <div className="model-selector">
      <div className="model-select-wrapper">
        <Sparkles size={14} className="model-select-sparkle" />
        <select
          className="model-select"
          value={selectedModel}
          onChange={(e) => onChange(e.target.value)}
        >
          {models?.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="model-select-icon" />
      </div>
      {selected && (
        <span className="model-description">{selected.description}</span>
      )}
    </div>
  );
}
