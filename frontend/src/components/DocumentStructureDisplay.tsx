// frontend/src/components/DocumentStructureDisplay.tsx
import React from "react";
import "./DocumentStructureDisplay.css";

interface StructureAnalysis {
  total_paragraphs: number;
  sections: {
    [key: string]: number;
  };
  classification_methods?: {
    [key: string]: number;
  };
}

interface DocumentStructureDisplayProps {
  structure: StructureAnalysis | null;
}

const SECTION_COLORS: { [key: string]: string } = {
  FACTS: "#3498db",
  ISSUES: "#e74c3c",
  LEGAL_ANALYSIS: "#9b59b6",
  REASONING: "#2ecc71",
  JUDGMENT: "#f39c12",
  ORDERS: "#e67e22",
};

const SECTION_LABELS: { [key: string]: string } = {
  FACTS: "Facts",
  ISSUES: "Issues",
  LEGAL_ANALYSIS: "Legal Analysis",
  REASONING: "Reasoning",
  JUDGMENT: "Judgment",
  ORDERS: "Orders",
};

const DocumentStructureDisplay: React.FC<DocumentStructureDisplayProps> = ({
  structure,
}) => {
  if (!structure) {
    return null;
  }

  const { total_paragraphs, sections, classification_methods } = structure;

  // Calculate percentages
  const sectionData = Object.entries(sections).map(([section, count]) => ({
    section,
    count,
    percentage: ((count / total_paragraphs) * 100).toFixed(1),
    color: SECTION_COLORS[section] || "#95a5a6",
    label: SECTION_LABELS[section] || section,
  }));

  // Sort by count descending
  sectionData.sort((a, b) => b.count - a.count);

  return (
    <div className="structure-container">
      <h3>📊 Document Structure Analysis</h3>
      <p className="structure-subtitle">
        AI-powered classification of {total_paragraphs} paragraphs using hybrid
        BERT + rule-based approach
      </p>

      <div className="structure-grid">
        {/* Section Distribution */}
        <div className="structure-card">
          <h4>Section Distribution</h4>
          <div className="section-bars">
            {sectionData.map(({ section, count, percentage, color, label }) => (
              <div key={section} className="section-bar-item">
                <div className="section-bar-label">
                  <span
                    className="section-dot"
                    style={{ backgroundColor: color }}
                  ></span>
                  <span className="section-name">{label}</span>
                  <span className="section-count">
                    {count} ({percentage}%)
                  </span>
                </div>
                <div className="section-bar-track">
                  <div
                    className="section-bar-fill"
                    style={{
                      width: `${percentage}%`,
                      backgroundColor: color,
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pie Chart Visualization */}
        <div className="structure-card">
          <h4>Visual Breakdown</h4>
          <div className="pie-chart-container">
            <svg viewBox="0 0 200 200" className="pie-chart">
              {(() => {
                let cumulativePercent = 0;
                return sectionData.map(
                  ({ section, count, percentage, color }) => {
                    const startAngle = (cumulativePercent / 100) * 360;
                    const angle = (parseFloat(percentage) / 100) * 360;
                    cumulativePercent += parseFloat(percentage);

                    // Calculate arc path
                    const startRad = ((startAngle - 90) * Math.PI) / 180;
                    const endRad = ((startAngle + angle - 90) * Math.PI) / 180;
                    const x1 = 100 + 90 * Math.cos(startRad);
                    const y1 = 100 + 90 * Math.sin(startRad);
                    const x2 = 100 + 90 * Math.cos(endRad);
                    const y2 = 100 + 90 * Math.sin(endRad);
                    const largeArc = angle > 180 ? 1 : 0;

                    return (
                      <path
                        key={section}
                        d={`M 100 100 L ${x1} ${y1} A 90 90 0 ${largeArc} 1 ${x2} ${y2} Z`}
                        fill={color}
                        stroke="#fff"
                        strokeWidth="2"
                      />
                    );
                  }
                );
              })()}
            </svg>
            <div className="pie-chart-center">
              <div className="pie-chart-total">{total_paragraphs}</div>
              <div className="pie-chart-label">paragraphs</div>
            </div>
          </div>
        </div>

        {/* Classification Methods */}
        {classification_methods && (
          <div className="structure-card classification-methods">
            <h4>Classification Methods</h4>
            <div className="methods-list">
              {Object.entries(classification_methods).map(([method, count]) => {
                const percentage = ((count / total_paragraphs) * 100).toFixed(
                  1
                );
                const methodLabels: { [key: string]: string } = {
                  bert: "🤖 BERT Model",
                  rules: "📋 Rule-Based",
                  fallback: "⚙️ Fallback",
                };
                const methodColors: { [key: string]: string } = {
                  bert: "#3498db",
                  rules: "#2ecc71",
                  fallback: "#95a5a6",
                };

                return (
                  <div key={method} className="method-item">
                    <div className="method-header">
                      <span className="method-label">
                        {methodLabels[method] || method}
                      </span>
                      <span className="method-count">
                        {count} ({percentage}%)
                      </span>
                    </div>
                    <div className="method-bar-track">
                      <div
                        className="method-bar-fill"
                        style={{
                          width: `${percentage}%`,
                          backgroundColor: methodColors[method] || "#95a5a6",
                        }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="methods-note">
              Hybrid approach combines BERT for common sections and rules for
              rare sections
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentStructureDisplay;
