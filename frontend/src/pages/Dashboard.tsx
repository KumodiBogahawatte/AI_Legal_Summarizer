import React from "react";
import { Link } from "react-router-dom";

interface DashboardProps {
  lang: string;
}

const Dashboard: React.FC<DashboardProps> = ({ lang }) => {
  let title = "AI Legal Summarizer – Sri Lankan Edition";
  let subtitle =
    "Advanced Legal Document Analysis with Constitutional Rights Detection";
  let description =
    "Upload your NLR / SLR court judgments and get instant AI summaries with constitutional rights detection, legal entity extraction, and multi-level analysis.";
  let uploadBtn = "Start Analysis";
  let features = {
    title: "Key Features",
    items: [
      {
        icon: "🤖",
        title: "AI-Powered Summarization",
        desc: "Multi-level summaries: Executive, Detailed, and Section-specific",
      },
      {
        icon: "⚖️",
        title: "Legal Entity Recognition",
        desc: "Extract cases, courts, judges, statutes, and legal principles",
      },
      {
        icon: "📜",
        title: "Constitutional Analysis",
        desc: "Detect fundamental rights violations and constitutional provisions",
      },
      {
        icon: "📊",
        title: "Document Structure",
        desc: "Automatic classification of legal document sections",
      },
    ],
  };

  if (lang === "si") {
    title = "ශ්‍රී ලංකා AI නීති සාරාංශකය";
    subtitle =
      "ව්‍යවස්ථානුකූල අයිතිවාසිකම් හඳුනාගැනීම සමඟ උසස් නීති ලේඛන විශ්ලේෂණය";
    description =
      "ඔබගේ NLR / SLR අධිකරණ තීන්දුව upload කර AI සාරාංශ සහ ව්‍යවස්ථානුකූල අයිතිවාසිකම් හඳුනාගන්න.";
    uploadBtn = "විශ්ලේෂණය ආරම්භ කරන්න";
  } else if (lang === "ta") {
    title = "இலங்கை AI சட்ட சுருக்கி";
    subtitle =
      "அரசியலமைப்பு உரிமைகள் கண்டறிதலுடன் மேம்பட்ட சட்ட ஆவண பகுப்பாய்வு";
    description =
      "உங்கள் NLR / SLR நீதிமன்ற தீர்ப்புகளை பதிவேற்றவும், AI சுருக்கங்களையும் அரசியலமைப்புச் சட்ட உரிமைகள் கண்டறிதலையும் பெறவும்.";
    uploadBtn = "பகுப்பாய்வு தொடங்கு";
  }

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
      {/* Hero Section */}
      <div
        className="card"
        style={{
          background: `linear-gradient(135deg, 
          rgba(var(--primary-blue-rgb), 0.1) 0%, 
          rgba(var(--primary-beige-rgb), 0.1) 100%)`,
          borderLeft: `4px solid var(--primary-dark)`,
          marginBottom: "var(--spacing-2xl)",
        }}
      >
        <div style={{ textAlign: "center", padding: "var(--spacing-xl)" }}>
          <h1
            style={{
              fontSize: "3rem",
              marginBottom: "var(--spacing-md)",
              background: `linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-blue) 100%)`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            {title}
          </h1>
          <p
            style={{
              fontSize: "1.25rem",
              color: "var(--text-secondary)",
              marginBottom: "var(--spacing-lg)",
              fontWeight: 500,
            }}
          >
            {subtitle}
          </p>
          <p
            style={{
              fontSize: "1.1rem",
              color: "var(--text-secondary)",
              lineHeight: 1.8,
              marginBottom: "var(--spacing-xl)",
              maxWidth: "800px",
              margin: "0 auto var(--spacing-xl)",
            }}
          >
            {description}
          </p>
          <Link
            to="/analyze"
            className="btn btn-primary"
            style={{
              fontSize: "1.1rem",
              padding: "var(--spacing-md) var(--spacing-xl)",
            }}
          >
            {uploadBtn} →
          </Link>
        </div>
      </div>

      {/* Features Grid */}
      <div style={{ marginBottom: "var(--spacing-2xl)" }}>
        <h2
          style={{
            textAlign: "center",
            marginBottom: "var(--spacing-xl)",
            fontSize: "2.5rem",
          }}
        >
          {features.title}
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "var(--spacing-lg)",
          }}
        >
          {features.items.map((feature, idx) => (
            <div
              key={idx}
              className="card"
              style={{
                textAlign: "center",
                padding: "var(--spacing-xl)",
                borderTop: `3px solid ${
                  idx === 0
                    ? "var(--primary-blue)"
                    : idx === 1
                    ? "var(--primary-beige)"
                    : idx === 2
                    ? "var(--primary-brown)"
                    : "var(--primary-dark)"
                }`,
              }}
            >
              <div
                style={{
                  fontSize: "3rem",
                  marginBottom: "var(--spacing-md)",
                }}
              >
                {feature.icon}
              </div>
              <h3
                style={{
                  fontSize: "1.25rem",
                  marginBottom: "var(--spacing-sm)",
                  color: "var(--primary-dark)",
                }}
              >
                {feature.title}
              </h3>
              <p
                style={{
                  color: "var(--text-secondary)",
                  lineHeight: 1.6,
                }}
              >
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Stats Section */}
      <div
        className="card"
        style={{
          background: `linear-gradient(135deg, 
          rgba(var(--primary-dark-rgb), 0.05) 0%, 
          rgba(var(--primary-brown-rgb), 0.05) 100%)`,
          textAlign: "center",
          padding: "var(--spacing-2xl)",
        }}
      >
        <h2 style={{ marginBottom: "var(--spacing-xl)" }}>
          System Performance
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "var(--spacing-xl)",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "3rem",
                fontWeight: "bold",
                color: "var(--primary-blue)",
                marginBottom: "var(--spacing-sm)",
              }}
            >
              87.28%
            </div>
            <div style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
              NER F1 Score
            </div>
          </div>
          <div>
            <div
              style={{
                fontSize: "3rem",
                fontWeight: "bold",
                color: "var(--primary-brown)",
                marginBottom: "var(--spacing-sm)",
              }}
            >
              98%+
            </div>
            <div style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
              Structure Accuracy
            </div>
          </div>
          <div>
            <div
              style={{
                fontSize: "3rem",
                fontWeight: "bold",
                color: "var(--primary-dark)",
                marginBottom: "var(--spacing-sm)",
              }}
            >
              8
            </div>
            <div style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
              Entity Types
            </div>
          </div>
          <div>
            <div
              style={{
                fontSize: "3rem",
                fontWeight: "bold",
                color: "var(--primary-beige)",
                marginBottom: "var(--spacing-sm)",
              }}
            >
              3
            </div>
            <div style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
              Summary Levels
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
