import React, { useEffect, useState } from "react";
import axios from "axios";
import "./RelatedCases.css";

interface SimilarCase {
  document_id: number;
  file_name: string;
  title: string;
  court: string;
  year: number;
  similarity_score: number;
  weighted_score: number;
  is_binding: boolean;
  court_weight: number;
  recency_factor: number;
}

interface RelatedCasesProps {
  documentId: number;
  topK?: number;
  minSimilarity?: number;
}

const RelatedCases: React.FC<RelatedCasesProps> = ({
  documentId,
  topK = 5,
  minSimilarity = 0.3,
}) => {
  const [similarCases, setSimilarCases] = useState<SimilarCase[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sourceDocument, setSourceDocument] = useState<any>(null);

  useEffect(() => {
    fetchSimilarCases();
  }, [documentId, topK, minSimilarity]);

  const fetchSimilarCases = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get(
        `http://localhost:8000/api/analysis/similar-cases/${documentId}`,
        {
          params: {
            top_k: topK,
            min_similarity: minSimilarity,
          },
        }
      );

      setSimilarCases(response.data.similar_cases || []);
      setSourceDocument(response.data.source_document);
    } catch (err: any) {
      console.error("Error fetching similar cases:", err);
      setError(err.response?.data?.detail || "Failed to load similar cases");
    } finally {
      setLoading(false);
    }
  };

  const getCourtColor = (court: string): string => {
    const courtLower = court.toLowerCase();
    if (courtLower.includes("supreme")) return "#8B0000"; // Dark red
    if (courtLower.includes("appeal")) return "#FF6B6B"; // Red
    if (courtLower.includes("high")) return "#4ECDC4"; // Teal
    if (courtLower.includes("district")) return "#95E1D3"; // Light teal
    if (courtLower.includes("magistrate")) return "#A8E6CF"; // Light green
    return "#6C757D"; // Gray for unknown
  };

  const getAuthorityBadge = (isBinding: boolean) => {
    return isBinding ? (
      <span className="authority-badge binding">⚖️ Binding</span>
    ) : (
      <span className="authority-badge persuasive">📚 Persuasive</span>
    );
  };

  const getSimilarityColor = (score: number): string => {
    if (score >= 0.8) return "#2ECC71"; // Green
    if (score >= 0.6) return "#F39C12"; // Orange
    if (score >= 0.4) return "#E67E22"; // Dark orange
    return "#95A5A6"; // Gray
  };

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className="related-cases-container">
        <h3 className="related-cases-title">🔗 Related Cases</h3>
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Finding similar cases...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="related-cases-container">
        <h3 className="related-cases-title">🔗 Related Cases</h3>
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (similarCases.length === 0) {
    return (
      <div className="related-cases-container">
        <h3 className="related-cases-title">🔗 Related Cases</h3>
        <div className="no-cases-message">
          <span className="info-icon">ℹ️</span>
          <p>
            No similar cases found. This might be a unique case or embeddings
            need to be generated.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="related-cases-container">
      <div className="related-cases-header">
        <h3 className="related-cases-title">🔗 Related Cases</h3>
        {sourceDocument && (
          <div className="source-document-info">
            <span className="source-label">Source:</span>
            <span className="source-title">{sourceDocument.title}</span>
          </div>
        )}
      </div>

      <div className="similar-cases-count">
        Found <strong>{similarCases.length}</strong> similar case
        {similarCases.length !== 1 ? "s" : ""}
      </div>

      <div className="similar-cases-list">
        {similarCases.map((similarCase, index) => (
          <div key={similarCase.document_id} className="similar-case-card">
            <div className="case-rank">#{index + 1}</div>

            <div className="case-content">
              <div className="case-header">
                <h4 className="case-title">{similarCase.title}</h4>
                {getAuthorityBadge(similarCase.is_binding)}
              </div>

              <div className="case-metadata">
                <span
                  className="case-court"
                  style={{
                    backgroundColor: getCourtColor(similarCase.court),
                    color: "white",
                  }}
                >
                  {similarCase.court}
                </span>
                <span className="case-year">📅 {similarCase.year}</span>
              </div>

              <div className="similarity-metrics">
                <div className="metric">
                  <span className="metric-label">Similarity:</span>
                  <div className="metric-bar">
                    <div
                      className="metric-fill"
                      style={{
                        width: formatPercentage(similarCase.similarity_score),
                        backgroundColor: getSimilarityColor(
                          similarCase.similarity_score
                        ),
                      }}
                    ></div>
                  </div>
                  <span className="metric-value">
                    {formatPercentage(similarCase.similarity_score)}
                  </span>
                </div>

                <div className="metric">
                  <span className="metric-label">Weighted Score:</span>
                  <div className="metric-bar">
                    <div
                      className="metric-fill"
                      style={{
                        width: formatPercentage(similarCase.weighted_score),
                        backgroundColor: getSimilarityColor(
                          similarCase.weighted_score
                        ),
                      }}
                    ></div>
                  </div>
                  <span className="metric-value">
                    {formatPercentage(similarCase.weighted_score)}
                  </span>
                </div>
              </div>

              <div className="case-weights">
                <span className="weight-badge" title="Court hierarchy weight">
                  Court: {formatPercentage(similarCase.court_weight)}
                </span>
                <span className="weight-badge" title="Recency adjustment">
                  Recency: {formatPercentage(similarCase.recency_factor)}
                </span>
              </div>

              <div className="case-actions">
                <button
                  className="view-case-btn"
                  onClick={() =>
                    (window.location.href = `/case/${similarCase.document_id}`)
                  }
                >
                  View Case →
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="related-cases-footer">
        <p className="footer-note">
          💡 <strong>Note:</strong> Cases are ranked by weighted similarity
          considering court hierarchy and recency. Binding precedents have
          higher authority than persuasive ones.
        </p>
      </div>
    </div>
  );
};

export default RelatedCases;
