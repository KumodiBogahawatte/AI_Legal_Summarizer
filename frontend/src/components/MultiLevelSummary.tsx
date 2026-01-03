import React, { useState } from "react";
import "./MultiLevelSummary.css";

interface SectionSummary {
  summary: string;
  word_count: number;
  sentence_count?: number;
  original_word_count?: number;
  citations?: string[];
}

interface SummaryData {
  summary: string;
  type: string;
  word_count: number;
  target_range: string;
  citations?: string[];
  section_summaries?: { [key: string]: SectionSummary };
}

interface PlainLanguageData {
  plain_summary: string;
  terms_simplified: number;
}

interface MultiLevelSummaryProps {
  documentId: number;
  documentName?: string;
}

type SummaryLevel = "executive" | "detailed" | "sections";

const MultiLevelSummary: React.FC<MultiLevelSummaryProps> = ({
  documentId,
  documentName,
}) => {
  const [selectedLevel, setSelectedLevel] = useState<SummaryLevel>("executive");
  const [plainLanguage, setPlainLanguage] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [executiveSummary, setExecutiveSummary] = useState<SummaryData | null>(
    null
  );
  const [detailedSummary, setDetailedSummary] = useState<SummaryData | null>(
    null
  );
  const [sectionSummaries, setSectionSummaries] = useState<{
    [key: string]: SectionSummary;
  } | null>(null);

  const [plainExecutive, setPlainExecutive] =
    useState<PlainLanguageData | null>(null);
  const [plainDetailed, setPlainDetailed] = useState<PlainLanguageData | null>(
    null
  );
  const [glossary, setGlossary] = useState<
    Array<{ term: string; definition: string; occurrences: number }>
  >([]);

  const fetchSummaries = async (includePlain: boolean = false) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/analysis/summarize/multi-level/${documentId}?include_plain_language=${includePlain}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch summaries: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.summaries) {
        setExecutiveSummary(data.summaries.executive);
        setDetailedSummary(data.summaries.detailed);
        setSectionSummaries(data.summaries.section_specific);

        if (includePlain && data.summaries.plain_language) {
          setPlainExecutive(data.summaries.plain_language.executive);
          setPlainDetailed(data.summaries.plain_language.detailed);
          setGlossary(data.summaries.plain_language.glossary || []);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load summaries");
      console.error("Summary fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchSummaries(plainLanguage);
  }, [documentId, plainLanguage]);

  const handleLevelChange = (level: SummaryLevel) => {
    setSelectedLevel(level);
  };

  const handlePlainLanguageToggle = () => {
    setPlainLanguage(!plainLanguage);
  };

  const renderExecutiveSummary = () => {
    if (!executiveSummary) return <p>No executive summary available</p>;

    const summary =
      plainLanguage && plainExecutive
        ? plainExecutive.plain_summary
        : executiveSummary.summary;

    return (
      <div className="summary-content">
        <div className="summary-header">
          <h3>📋 Executive Summary</h3>
          <div className="summary-meta">
            <span className="word-count">
              {executiveSummary.word_count} words
            </span>
            <span className="target-range">
              {executiveSummary.target_range}
            </span>
            {plainLanguage && plainExecutive && (
              <span className="terms-simplified">
                ✓ {plainExecutive.terms_simplified} terms simplified
              </span>
            )}
          </div>
        </div>
        <div className="summary-text">{summary || "No summary available"}</div>
        {executiveSummary.citations &&
          executiveSummary.citations.length > 0 && (
            <div className="citations">
              <strong>Citations:</strong>{" "}
              {executiveSummary.citations.join(", ")}
            </div>
          )}
      </div>
    );
  };

  const renderDetailedSummary = () => {
    if (!detailedSummary) return <p>No detailed summary available</p>;

    const summary =
      plainLanguage && plainDetailed
        ? plainDetailed.plain_summary
        : detailedSummary.summary;

    return (
      <div className="summary-content">
        <div className="summary-header">
          <h3>📝 Detailed Summary</h3>
          <div className="summary-meta">
            <span className="word-count">
              {detailedSummary.word_count} words
            </span>
            <span className="target-range">{detailedSummary.target_range}</span>
            {plainLanguage && plainDetailed && (
              <span className="terms-simplified">
                ✓ {plainDetailed.terms_simplified} terms simplified
              </span>
            )}
          </div>
        </div>
        <div className="summary-text detailed">
          {summary || "No summary available"}
        </div>
        {detailedSummary.citations && detailedSummary.citations.length > 0 && (
          <div className="citations">
            <strong>Citations:</strong> {detailedSummary.citations.join(", ")}
          </div>
        )}
      </div>
    );
  };

  const renderSectionSummaries = () => {
    if (!sectionSummaries || Object.keys(sectionSummaries).length === 0) {
      return <p>No section summaries available</p>;
    }

    const sectionOrder = [
      "FACTS",
      "ISSUES",
      "LEGAL_ANALYSIS",
      "REASONING",
      "JUDGMENT",
      "ORDERS",
    ];
    const sortedSections = Object.keys(sectionSummaries).sort((a, b) => {
      const indexA = sectionOrder.indexOf(a);
      const indexB = sectionOrder.indexOf(b);
      return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB);
    });

    return (
      <div className="summary-content sections">
        <div className="summary-header">
          <h3>📂 Section-Specific Summaries</h3>
        </div>
        <div className="section-summaries-grid">
          {sortedSections.map((section) => {
            const sectionData = sectionSummaries[section];
            return (
              <div key={section} className="section-summary-card">
                <div className="section-header">
                  <h4>{section.replace(/_/g, " ")}</h4>
                  <span className="section-word-count">
                    {sectionData.word_count} words
                  </span>
                </div>
                <div className="section-text">
                  {sectionData.summary || "No summary available"}
                </div>
                {sectionData.citations && sectionData.citations.length > 0 && (
                  <div className="section-citations">
                    <strong>Citations:</strong>{" "}
                    {sectionData.citations.join(", ")}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderGlossary = () => {
    if (!plainLanguage || glossary.length === 0) return null;

    return (
      <div className="glossary-panel">
        <h4>📚 Legal Terms Glossary</h4>
        <div className="glossary-list">
          {glossary.slice(0, 10).map((entry, index) => (
            <div key={index} className="glossary-item">
              <span className="glossary-term">{entry.term}</span>
              <span className="glossary-arrow">→</span>
              <span className="glossary-definition">{entry.definition}</span>
              <span className="glossary-count">({entry.occurrences}x)</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="multi-level-summary">
      <div className="summary-controls">
        <div className="level-selector">
          <button
            className={`level-btn ${
              selectedLevel === "executive" ? "active" : ""
            }`}
            onClick={() => handleLevelChange("executive")}
          >
            📋 Executive
          </button>
          <button
            className={`level-btn ${
              selectedLevel === "detailed" ? "active" : ""
            }`}
            onClick={() => handleLevelChange("detailed")}
          >
            📝 Detailed
          </button>
          <button
            className={`level-btn ${
              selectedLevel === "sections" ? "active" : ""
            }`}
            onClick={() => handleLevelChange("sections")}
          >
            📂 Sections
          </button>
        </div>

        <div className="plain-language-toggle">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={plainLanguage}
              onChange={handlePlainLanguageToggle}
            />
            <span className="toggle-text">🗣️ Plain Language</span>
          </label>
        </div>
      </div>

      {loading && (
        <div className="summary-loading">
          <div className="spinner"></div>
          <p>Generating summaries...</p>
        </div>
      )}

      {error && (
        <div className="summary-error">
          <p>❌ {error}</p>
          <button onClick={() => fetchSummaries(plainLanguage)}>Retry</button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="summary-display">
            {selectedLevel === "executive" && renderExecutiveSummary()}
            {selectedLevel === "detailed" && renderDetailedSummary()}
            {selectedLevel === "sections" && renderSectionSummaries()}
          </div>

          {renderGlossary()}
        </>
      )}
    </div>
  );
};

export default MultiLevelSummary;
