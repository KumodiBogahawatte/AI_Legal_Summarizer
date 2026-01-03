import React, { useState, useEffect } from "react";
import "./LegalEntitiesDisplay.css";

interface Entity {
  text: string;
  start: number;
  end: number;
  label: string;
}

interface EntitiesByType {
  [key: string]: Entity[];
}

interface LegalEntitiesDisplayProps {
  documentId?: number;
  text?: string;
  autoLoad?: boolean;
}

const ENTITY_COLORS: { [key: string]: string } = {
  CASE_NAME: "#FF6B6B",
  COURT: "#4ECDC4",
  JUDGE: "#45B7D1",
  STATUTE: "#96CEB4",
  ARTICLE: "#FFEAA7",
  LEGAL_PRINCIPLE: "#DFE6E9",
  DATE: "#74B9FF",
  CITATION: "#A29BFE",
};

const ENTITY_LABELS: { [key: string]: string } = {
  CASE_NAME: "Case Names",
  COURT: "Courts",
  JUDGE: "Judges",
  STATUTE: "Statutes & Laws",
  ARTICLE: "Articles & Sections",
  LEGAL_PRINCIPLE: "Legal Principles",
  DATE: "Dates",
  CITATION: "Citations",
};

const LegalEntitiesDisplay: React.FC<LegalEntitiesDisplayProps> = ({
  documentId,
  text,
  autoLoad = false,
}) => {
  const [entities, setEntities] = useState<EntitiesByType>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [totalEntities, setTotalEntities] = useState<number>(0);
  const [highlightedText, setHighlightedText] = useState<string>("");
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(
    new Set(Object.keys(ENTITY_COLORS))
  );

  useEffect(() => {
    if (autoLoad) {
      extractEntities();
    }
  }, [documentId, text, autoLoad]);

  const extractEntities = async () => {
    setLoading(true);
    setError(null);

    try {
      const baseUrl = "http://127.0.0.1:8000";
      let response;

      if (documentId) {
        // Extract from stored document
        response = await fetch(
          `${baseUrl}/api/analysis/extract-entities/${documentId}`
        );
      } else if (text) {
        // Extract from provided text
        response = await fetch(
          `${baseUrl}/api/analysis/extract-entities?text=${encodeURIComponent(
            text
          )}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );
      } else {
        throw new Error("Either documentId or text must be provided");
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Failed to extract entities: ${response.statusText} - ${errorText}`
        );
      }

      const data = await response.json();
      setEntities(data.entities_by_type || {});
      setTotalEntities(data.total_entities || 0);

      // Generate highlighted text
      if (text) {
        generateHighlightedText(text, data.entities_by_type || {});
      }
    } catch (err: any) {
      setError(err.message);
      console.error("Entity extraction error:", err);
    } finally {
      setLoading(false);
    }
  };

  const generateHighlightedText = (
    originalText: string,
    entitiesByType: EntitiesByType
  ) => {
    // Flatten all entities and sort by start position
    const allEntities: (Entity & { type: string })[] = [];
    Object.entries(entitiesByType).forEach(([type, ents]) => {
      ents.forEach((ent) => allEntities.push({ ...ent, type }));
    });
    allEntities.sort((a, b) => a.start - b.start);

    // Build highlighted HTML
    let result = "";
    let lastIndex = 0;

    allEntities.forEach((entity) => {
      if (selectedTypes.has(entity.label)) {
        // Add text before entity
        result += escapeHtml(originalText.substring(lastIndex, entity.start));

        // Add highlighted entity
        const color = ENTITY_COLORS[entity.label] || "#ccc";
        result += `<mark style="background-color: ${color}; padding: 2px 4px; border-radius: 3px; font-weight: 500;" title="${
          entity.label
        }">${escapeHtml(entity.text)}</mark>`;

        lastIndex = entity.end;
      }
    });

    // Add remaining text
    result += escapeHtml(originalText.substring(lastIndex));
    setHighlightedText(result);
  };

  const escapeHtml = (text: string): string => {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  };

  const toggleEntityType = (type: string) => {
    const newSelected = new Set(selectedTypes);
    if (newSelected.has(type)) {
      newSelected.delete(type);
    } else {
      newSelected.add(type);
    }
    setSelectedTypes(newSelected);

    // Regenerate highlighted text with new filters
    if (text) {
      generateHighlightedText(text, entities);
    }
  };

  const getEntityCount = (type: string): number => {
    return entities[type]?.length || 0;
  };

  if (loading) {
    return (
      <div className="legal-entities-loading">
        <div className="spinner"></div>
        <p>Extracting legal entities...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="legal-entities-error">
        <h3>⚠️ Error</h3>
        <p>{error}</p>
        <button onClick={extractEntities}>Try Again</button>
      </div>
    );
  }

  if (totalEntities === 0 && !loading) {
    return (
      <div className="legal-entities-empty">
        <p>No legal entities detected.</p>
        {!autoLoad && (
          <button onClick={extractEntities}>Extract Entities</button>
        )}
      </div>
    );
  }

  return (
    <div className="legal-entities-container">
      <div className="entities-header">
        <h2>🏷️ Legal Entities</h2>
        <span className="entity-count-badge">
          {totalEntities} entities found
        </span>
      </div>

      {/* Entity Type Filter */}
      <div className="entity-type-filters">
        {Object.entries(ENTITY_LABELS).map(([type, label]) => {
          const count = getEntityCount(type);
          if (count === 0) return null;

          return (
            <button
              key={type}
              className={`entity-filter-btn ${
                selectedTypes.has(type) ? "active" : ""
              }`}
              style={{
                backgroundColor: selectedTypes.has(type)
                  ? ENTITY_COLORS[type]
                  : "#f5f5f5",
                color: selectedTypes.has(type) ? "#000" : "#666",
              }}
              onClick={() => toggleEntityType(type)}
            >
              {label} ({count})
            </button>
          );
        })}
      </div>

      {/* Highlighted Text View */}
      {highlightedText && (
        <div className="highlighted-text-container">
          <h3>📄 Highlighted Document</h3>
          <div
            className="highlighted-text"
            dangerouslySetInnerHTML={{ __html: highlightedText }}
          />
        </div>
      )}

      {/* Entity Lists by Type */}
      <div className="entities-by-type">
        {Object.entries(entities).map(([type, entList]) => {
          if (entList.length === 0 || !selectedTypes.has(type)) return null;

          return (
            <div key={type} className="entity-type-section">
              <h3 style={{ color: ENTITY_COLORS[type] }}>
                {ENTITY_LABELS[type] || type} ({entList.length})
              </h3>
              <div className="entity-list">
                {entList.map((entity, idx) => (
                  <span
                    key={idx}
                    className="entity-tag"
                    style={{ backgroundColor: ENTITY_COLORS[type] }}
                    title={`Position: ${entity.start}-${entity.end}`}
                  >
                    {entity.text}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Statistics */}
      <div className="entity-statistics">
        <h3>📊 Statistics</h3>
        <div className="stats-grid">
          {Object.entries(entities).map(([type, entList]) => (
            <div key={type} className="stat-item">
              <span className="stat-label">{ENTITY_LABELS[type] || type}:</span>
              <span className="stat-value">{entList.length}</span>
            </div>
          ))}
        </div>
      </div>

      {!autoLoad && (
        <button className="refresh-btn" onClick={extractEntities}>
          🔄 Refresh Entities
        </button>
      )}
    </div>
  );
};

export default LegalEntitiesDisplay;
