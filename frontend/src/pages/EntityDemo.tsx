import React, { useState } from "react";
import LegalEntitiesDisplay from "../components/LegalEntitiesDisplay";
import "./EntityDemo.css";

const SAMPLE_TEXTS = [
  {
    title: "Supreme Court Case Example",
    text: `In the landmark case of Silva vs. Fernando decided by the Supreme Court on 15th March 2006, Justice S.N. Silva held that Section 175(1) of the Civil Procedure Code requires filing witness lists 15 days before trial. The Court cited precedent from [2005] 2 SRI L.R. 123 establishing the burden of proof principle. This case also references Article 138 of the Constitution and the Maintenance Act No. 37 of 1999.`,
  },
  {
    title: "Court of Appeal Judgment",
    text: `The Court of Appeal in Perera and Another vs. Bank of Ceylon (CA 450/2003) examined Article 138 of the Constitution and the Maintenance Act No. 37 of 1999. Hon. Andrew Somawansa, J. delivered the judgment on 21.02.2005, establishing important precedents regarding natural justice and procedural fairness.`,
  },
  {
    title: "High Court Decision",
    text: `The High Court considered the Evidence Ordinance and fundamental rights under Article 154P(3)(b). The learned District Judge applied the doctrine of res judicata as per the ruling in DC Colombo 17090/L. The judgment was delivered on 10.08.2023 by Justice Priyantha Jayawardena.`,
  },
];

const EntityDemo: React.FC = () => {
  const [customText, setCustomText] = useState("");
  const [showDemo, setShowDemo] = useState(false);
  const [selectedSample, setSelectedSample] = useState(0);
  const [useCustomText, setUseCustomText] = useState(false);

  const handleLoadSample = (index: number) => {
    setSelectedSample(index);
    setUseCustomText(false);
    setShowDemo(true);
  };

  const handleAnalyzeCustomText = () => {
    if (customText.trim().length === 0) {
      alert("Please enter some text to analyze");
      return;
    }
    setUseCustomText(true);
    setShowDemo(true);
  };

  return (
    <div className="entity-demo-container">
      <div className="demo-header">
        <h1>🏷️ Legal Entity Recognition Demo</h1>
        <p className="demo-subtitle">
          Extract case names, courts, judges, statutes, articles, legal
          principles, dates, and citations from Sri Lankan legal documents
        </p>
      </div>

      <div className="demo-controls">
        {/* Sample Text Selection */}
        <div className="sample-selection">
          <h2>📚 Try Sample Texts</h2>
          <div className="sample-buttons">
            {SAMPLE_TEXTS.map((sample, index) => (
              <button
                key={index}
                className={`sample-btn ${
                  selectedSample === index && !useCustomText ? "active" : ""
                }`}
                onClick={() => handleLoadSample(index)}
              >
                {sample.title}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Text Input */}
        <div className="custom-text-section">
          <h2>✍️ Or Enter Your Own Text</h2>
          <textarea
            className="custom-text-input"
            placeholder="Paste your legal text here... (e.g., court judgment, legal document excerpt)"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            rows={8}
          />
          <button className="analyze-btn" onClick={handleAnalyzeCustomText}>
            🔍 Analyze Custom Text
          </button>
        </div>
      </div>

      {/* Entity Extraction Results */}
      {showDemo && (
        <div className="demo-results">
          <LegalEntitiesDisplay
            text={
              useCustomText ? customText : SAMPLE_TEXTS[selectedSample].text
            }
            autoLoad={true}
          />
        </div>
      )}

      {/* Information Section */}
      <div className="demo-info">
        <h2>ℹ️ About Legal Entity Recognition</h2>
        <div className="info-grid">
          <div className="info-card">
            <h3>🎯 What It Does</h3>
            <p>
              Our custom-trained NER model automatically identifies and extracts
              8 types of legal entities from Sri Lankan legal documents with 87%
              accuracy.
            </p>
          </div>

          <div className="info-card">
            <h3>🏷️ Entity Types</h3>
            <ul>
              <li>
                <strong>CASE_NAME:</strong> Case titles and party names
              </li>
              <li>
                <strong>COURT:</strong> Court names and jurisdictions
              </li>
              <li>
                <strong>JUDGE:</strong> Judge names and titles
              </li>
              <li>
                <strong>STATUTE:</strong> Laws, acts, and ordinances
              </li>
              <li>
                <strong>ARTICLE:</strong> Articles and sections
              </li>
              <li>
                <strong>LEGAL_PRINCIPLE:</strong> Legal doctrines
              </li>
              <li>
                <strong>DATE:</strong> Decision dates and timelines
              </li>
              <li>
                <strong>CITATION:</strong> Case citations and references
              </li>
            </ul>
          </div>

          <div className="info-card">
            <h3>📊 Model Performance</h3>
            <ul>
              <li>
                <strong>F1 Score:</strong> 87.28%
              </li>
              <li>
                <strong>Training Data:</strong> 1,078 legal texts
              </li>
              <li>
                <strong>Entities Labeled:</strong> 8,402
              </li>
              <li>
                <strong>Framework:</strong> spaCy 3.8.11
              </li>
            </ul>
          </div>

          <div className="info-card">
            <h3>🚀 Use Cases</h3>
            <ul>
              <li>Legal research and case analysis</li>
              <li>Document indexing and search</li>
              <li>Precedent identification</li>
              <li>Knowledge graph construction</li>
              <li>Automated citation extraction</li>
              <li>Legal database population</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Technical Details */}
      <div className="demo-technical">
        <h2>🔧 Technical Implementation</h2>
        <div className="tech-details">
          <div className="tech-section">
            <h3>Training Process</h3>
            <p>
              The model was trained using automated regex-based annotation on
              1,078 legal passages extracted from 72 Sri Lankan court cases. We
              used 44 carefully crafted patterns across 8 entity types,
              achieving high precision without manual annotation.
            </p>
          </div>

          <div className="tech-section">
            <h3>Architecture</h3>
            <p>
              Built on spaCy's blank English model with custom NER pipeline.
              Trained for 30 iterations with 80/10/10 train/dev/test split. The
              model uses token-based entity recognition with context-aware
              boundary detection.
            </p>
          </div>

          <div className="tech-section">
            <h3>Integration</h3>
            <p>
              Fully integrated into the backend API with RESTful endpoints.
              Supports both document-based extraction (from stored documents)
              and text-based extraction (from arbitrary text input). Results are
              returned in structured JSON format.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EntityDemo;
