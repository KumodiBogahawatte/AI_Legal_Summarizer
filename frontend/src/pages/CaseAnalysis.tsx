// frontend/src/pages/CaseAnalysis.tsx
import React, { useState } from "react";
import DocumentUploadMUI from "../components/DocumentUploadMUI";
import SummaryView from "../components/SummaryView";
import ConstitutionalRightsHighlighter from "../components/ConstitutionalRightsHighlighter";
import ConstitutionalProvisionsDisplay from "../components/ConstitutionalProvisionsDisplay";
import LegalEntitiesDisplay from "../components/LegalEntitiesDisplay";
// import DocumentStructureDisplay from "../components/DocumentStructureDisplay";
import MultiLevelSummary from "../components/MultiLevelSummary";
import RelatedCases from "../components/RelatedCases";
import ExportButton from "../components/ExportButton";
import axios from "axios";

interface FundamentalRight {
  article: string;
  article_title?: string;
  matched_text: string;
  explanation?: string;
  context?: string;
  method?: string;
  score?: number;
}

interface ConstitutionalProvision {
  article: string;
  matched_text: string;
  method: string;
  score: number;
  constitutional_provision?: string;
  explanation?: string;
  context?: string;
  document?: string;
}

interface StructureAnalysis {
  total_paragraphs: number;
  sections: {
    [key: string]: number;
  };
  classification_methods?: {
    [key: string]: number;
  };
}

interface CaseAnalysisProps {
  lang: string;
}

const CaseAnalysis: React.FC<CaseAnalysisProps> = ({ lang }) => {
  const [summary, setSummary] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [fundamentalRights, setFundamentalRights] = useState<
    FundamentalRight[]
  >([]);
  const [constitutionalProvisions, setConstitutionalProvisions] = useState<
    ConstitutionalProvision[]
  >([]);
  const [structureAnalysis, setStructureAnalysis] =
    useState<StructureAnalysis | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [currentDocumentId, setCurrentDocumentId] = useState<number | null>(
    null
  );

  const handleUploadSuccess = async (doc: any) => {
    setAnalysisError(null);
    setCurrentDocumentId(doc.document_id);

    // Set structure analysis from upload response
    if (doc.structure_analysis) {
      setStructureAnalysis(doc.structure_analysis);
      console.log("Document structure:", doc.structure_analysis);
    }

    try {
      // CORRECT: document_id as query parameter, not request body
      const sum = await axios.post(
        `http://127.0.0.1:8000/api/analysis/summarize/with-local-context?document_id=${doc.document_id}`,
        {}, // Empty request body
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      setSummary(sum.data.summary);
      setKeywords(sum.data.keywords || []);

      // Get fundamental rights (Articles 10-18 only)
      if (sum.data.fundamental_rights) {
        setFundamentalRights(sum.data.fundamental_rights);
        console.log("Fundamental rights:", sum.data.fundamental_rights);
      }

      // NEW: Get constitutional provisions from summary response
      if (sum.data.constitutional_provisions) {
        setConstitutionalProvisions(sum.data.constitutional_provisions);
        console.log(
          "Constitutional provisions:",
          sum.data.constitutional_provisions
        );
      }
    } catch (error: any) {
      console.error("Analysis failed:", error);
      console.error("Error response:", error.response?.data);
      const errorMessage = error.response?.data?.detail || error.message;
      setAnalysisError(errorMessage);
    }
  };

  return (
    <div className="case-analysis-container" id="case-analysis-container">
      <div
        className="card"
        style={{
          background: `linear-gradient(135deg, 
          rgba(var(--primary-blue-rgb), 0.05) 0%, 
          rgba(var(--primary-beige-rgb), 0.05) 100%)`,
          marginBottom: "var(--spacing-lg)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "2.5rem",
              color: "var(--primary-dark)",
              marginBottom: "var(--spacing-sm)",
            }}
          >
            📄 Legal Document Analysis
          </h1>
          <p
            style={{
              fontSize: "1.1rem",
              color: "var(--text-secondary)",
              marginBottom: 0,
            }}
          >
            Upload a legal document to extract entities, analyze structure, and
            generate summaries
          </p>
        </div>
        {currentDocumentId && (
          <ExportButton
            documentId={currentDocumentId}
            documentTitle={`Document_${currentDocumentId}`}
            contentElementId="case-analysis-container"
          />
        )}
      </div>

      <DocumentUploadMUI onUploadSuccess={handleUploadSuccess} />

      {analysisError && (
        <div
          className="card"
          style={{
            backgroundColor: "rgba(244, 67, 54, 0.1)",
            border: "2px solid rgba(244, 67, 54, 0.3)",
            borderRadius: "var(--radius-lg)",
            padding: "var(--spacing-lg)",
          }}
        >
          <strong style={{ color: "#c62828" }}>⚠️ Analysis Error:</strong>
          <p
            style={{
              color: "#c62828",
              marginBottom: 0,
              marginTop: "var(--spacing-sm)",
            }}
          >
            {analysisError}
          </p>
        </div>
      )}

      {/* {structureAnalysis && (
        <DocumentStructureDisplay structure={structureAnalysis} />
      )} */}

      {currentDocumentId && (
        <MultiLevelSummary documentId={currentDocumentId} />
      )}

      {/* <SummaryView summary={summary} keywords={keywords} lang={lang} /> */}

      <ConstitutionalRightsHighlighter rights={fundamentalRights} />

      <ConstitutionalProvisionsDisplay provisions={constitutionalProvisions} />

      {currentDocumentId && (
        <LegalEntitiesDisplay documentId={currentDocumentId} autoLoad={true} />
      )}

      {currentDocumentId && (
        <RelatedCases
          documentId={currentDocumentId}
          topK={5}
          minSimilarity={0.3}
        />
      )}
    </div>
  );
};

export default CaseAnalysis;
