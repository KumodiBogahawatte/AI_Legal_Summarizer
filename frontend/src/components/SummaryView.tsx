import React from "react";

interface SummaryViewProps {
  summary: string;
  keywords: string[];
  lang?: string;
}

const SummaryView: React.FC<SummaryViewProps> = ({
  summary,
  keywords,
  lang,
}) => {
  let summaryTitle = "Case Summary";
  let noSummaryText = "No summary generated yet.";
  let keywordsTitle = "Keywords";

  if (lang === "si") {
    summaryTitle = "කේස් සාරාංශය";
    noSummaryText = "සාරාංශයක් තවම නිපදවා නැත.";
    keywordsTitle = "මූලික වචන";
  } else if (lang === "ta") {
    summaryTitle = "வழக்கு சுருக்கம்";
    noSummaryText = "இன்னும் சுருக்கம் உருவாக்கப்படவில்லை.";
    keywordsTitle = "முக்கிய சொற்கள்";
  }

  return (
    <div className="summary-container">
      <h2>{summaryTitle}</h2>
      <p>{summary || noSummaryText}</p>

      <h3>{keywordsTitle}</h3>
      <ul>
        {keywords?.map((k) => (
          <li key={k}>{k}</li>
        ))}
      </ul>
    </div>
  );
};

export default SummaryView;
