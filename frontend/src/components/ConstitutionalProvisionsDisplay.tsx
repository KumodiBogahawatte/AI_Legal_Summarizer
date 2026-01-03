import React from "react";
import "./ConstitutionalProvisionsDisplay.css";

interface ConstitutionalProvision {
  article: string;
  matched_text: string;
  method: string;
  score: number;
  article_title?: string;
  constitutional_provision?: string;
  explanation?: string;
  context?: string;
  document?: string;
}

interface ConstitutionalProvisionsDisplayProps {
  provisions: ConstitutionalProvision[];
}

const ConstitutionalProvisionsDisplay: React.FC<
  ConstitutionalProvisionsDisplayProps
> = ({ provisions }) => {
  if (!provisions || provisions.length === 0) {
    return (
      <div className="provisions-container">
        <h2>📚 Constitutional Provisions</h2>
        <p className="no-data">No constitutional provisions detected.</p>
      </div>
    );
  }

  // Deduplicate provisions by article number (keep highest score)
  const deduplicatedProvisions = provisions.reduce((acc, provision) => {
    const article = provision.article || "Unknown";
    if (!acc[article] || provision.score > acc[article].score) {
      acc[article] = provision;
    }
    return acc;
  }, {} as Record<string, ConstitutionalProvision>);

  const uniqueProvisions = Object.values(deduplicatedProvisions);

  return (
    <div className="provisions-container">
      <h2>
        📚 Constitutional Provisions ({uniqueProvisions.length} unique articles
        detected)
      </h2>
      <p className="description">
        References to constitutional articles and provisions found in this case.
      </p>

      {uniqueProvisions.map((provision, idx) => (
        <div key={idx} className={`provision-box ${provision.method}`}>
          <div className="provision-header">
            <h3 className="article-title">
              {provision.article_title || `Article ${provision.article}`}
            </h3>
            <div className="badges">
              <span className="method-badge">
                {provision.method === "explicit_mention"
                  ? "📌 Explicit"
                  : "🔍 Semantic"}
              </span>
              {provision.score && provision.method !== "explicit_mention" && (
                <span className="score-badge">
                  {(provision.score * 100).toFixed(0)}% match
                </span>
              )}
            </div>
          </div>

          <div className="matched-text">
            <strong>Matched Text:</strong>
            <p className="text-snippet">"{provision.matched_text}"</p>
          </div>

          {provision.explanation && (
            <details className="provision-details" open>
              <summary>📖 Explanation</summary>
              <p className="explanation-text">{provision.explanation}</p>
            </details>
          )}

          {provision.constitutional_provision && (
            <details className="provision-details">
              <summary>📜 Constitutional Reference</summary>
              <p className="constitution-text">
                {provision.constitutional_provision}
              </p>
              {provision.document && (
                <p className="source-doc">
                  <small>Source: {provision.document}</small>
                </p>
              )}
            </details>
          )}

          {provision.context &&
            provision.context !== provision.matched_text && (
              <details className="provision-details">
                <summary>🔍 Context</summary>
                <p className="context-text">{provision.context}</p>
              </details>
            )}
        </div>
      ))}
    </div>
  );
};

export default ConstitutionalProvisionsDisplay;
