import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Info,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import type { AnalysisResponse, Recommendation, Insight } from "../types";

interface Props {
  analysis: AnalysisResponse | null;
  isLoading: boolean;
  onRunAnalysis: () => void;
}

function PriorityBadge({ priority }: { priority: string }) {
  const styles: Record<string, { bg: string; text: string }> = {
    high: { bg: "#fecaca", text: "#991b1b" },
    medium: { bg: "#fef08a", text: "#854d0e" },
    low: { bg: "#bbf7d0", text: "#166534" },
  };
  const s = styles[priority] || styles.medium;
  return (
    <span className="priority-badge" style={{ backgroundColor: s.bg, color: s.text }}>
      {priority.toUpperCase()}
    </span>
  );
}

function InsightIcon({ type }: { type: string }) {
  switch (type) {
    case "positive":
      return <CheckCircle size={18} color="#10b981" />;
    case "negative":
      return <AlertTriangle size={18} color="#ef4444" />;
    default:
      return <Info size={18} color="#3b82f6" />;
  }
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="recommendation-card">
      <div className="rec-header" onClick={() => setExpanded(!expanded)}>
        <div className="rec-title-row">
          <PriorityBadge priority={rec.priority} />
          <span className="rec-category">{rec.category}</span>
          <span className="rec-title">{rec.title}</span>
        </div>
        {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </div>
      {expanded && (
        <div className="rec-body">
          <p>{rec.description}</p>
          <div className="rec-impact">
            <strong>Expected Impact:</strong> {rec.expected_impact}
          </div>
          {rec.action_items.length > 0 && (
            <div className="rec-actions">
              <strong>Next Steps:</strong>
              <ul>
                {rec.action_items.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AnalysisPanel({ analysis, isLoading, onRunAnalysis }: Props) {
  return (
    <div className="card analysis-panel">
      <div className="analysis-header">
        <h2>
          <Sparkles size={22} color="#f59e0b" />
          AI Analysis
        </h2>
        <button className="btn-primary" onClick={onRunAnalysis} disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 size={16} className="spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Run Analysis
            </>
          )}
        </button>
      </div>

      {isLoading && (
        <div className="analysis-loading">
          <Loader2 size={32} className="spin" />
          <p>Gemini is analyzing your campaign data...</p>
        </div>
      )}

      {analysis && !isLoading && (
        <div className="analysis-content">
          {/* Summary */}
          <div className="analysis-summary">
            <h3>Summary</h3>
            <p>{analysis.summary}</p>
          </div>

          {/* Insights */}
          {analysis.insights.length > 0 && (
            <div className="analysis-insights">
              <h3>Insights</h3>
              <div className="insights-grid">
                {analysis.insights.map((insight: Insight, i: number) => (
                  <div key={i} className={`insight-card insight-${insight.type}`}>
                    <div className="insight-header">
                      <InsightIcon type={insight.type} />
                      <span className="insight-metric">{insight.metric}</span>
                    </div>
                    <h4>{insight.title}</h4>
                    <p>{insight.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {analysis.recommendations.length > 0 && (
            <div className="analysis-recommendations">
              <h3>
                Recommendations ({analysis.recommendations.length})
              </h3>
              {analysis.recommendations.map((rec: Recommendation, i: number) => (
                <RecommendationCard key={i} rec={rec} />
              ))}
            </div>
          )}
        </div>
      )}

      {!analysis && !isLoading && (
        <div className="analysis-empty">
          <Sparkles size={48} color="#333" />
          <p>Click "Run Analysis" to analyze your campaign data with Gemini AI.</p>
        </div>
      )}
    </div>
  );
}
