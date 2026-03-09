# Legal NER Training Data

This directory contains training data for the Custom Legal Named Entity Recognition (NER) model.

## Entity Types

The model is trained to recognize the following entity types in Sri Lankan legal documents:

1. **CASE_NAME** - Names of legal cases (e.g., "Silva v. Fernando")
2. **COURT** - Court names (e.g., "Supreme Court", "Court of Appeal")
3. **JUDGE** - Judge names (e.g., "Justice Dep P.C.J.", "Marsoof J.")
4. **STATUTE** - Statutory references (e.g., "Prevention of Terrorism Act", "Penal Code")
5. **ARTICLE** - Constitutional articles (e.g., "Article 12", "Article 13(1)")
6. **LEGAL_PRINCIPLE** - Legal doctrines and principles (e.g., "natural justice", "res judicata")
7. **DATE** - Dates relevant to the case (e.g., "12th January 2020")
8. **CITATION** - Legal citations (e.g., "[2020] 1 SLR 345", "2015 BALR 123")

## Data Format

Training data should be in spaCy's format (.spacy binary or JSON):

```json
{
  "text": "In the case of Silva v. Fernando, the Supreme Court held...",
  "entities": [
    [15, 32, "CASE_NAME"],
    [38, 51, "COURT"]
  ]
}
```

## Annotation Guidelines

### 1. CASE_NAME

- Include both party names connected by "v." or "vs."
- Example: "Bandara v. Attorney General"
- Include alternative formats: "In re Silva", "Ex parte Fernando"

### 2. COURT

- Full court names
- Examples: "Supreme Court of Sri Lanka", "High Court of Colombo"
- Abbreviations: "SC", "CA", "HC"

### 3. JUDGE

- Include title and name
- Examples: "Justice Dep P.C.J.", "Chief Justice Mohan Pieris"
- Multiple judges: Annotate each separately

### 4. STATUTE

- Full statute names
- Examples: "Prevention of Terrorism Act No. 48 of 1979"
- Short forms: "Penal Code", "Constitution"

### 5. ARTICLE

- Constitutional articles with numbers
- Examples: "Article 12(1)", "Article 13", "Section 3(a)"

### 6. LEGAL_PRINCIPLE

- Established legal doctrines
- Latin phrases: "habeas corpus", "res judicata", "ultra vires"
- Common law principles: "reasonable doubt", "burden of proof"

### 7. DATE

- Case dates, judgment dates
- Formats: "12th January 2020", "2020-01-12", "January 12, 2020"

### 8. CITATION

- Legal citations in standard formats
- Examples: "[2020] 1 SLR 345", "2015 BALR 123", "NLR 234"

## Annotation Tools

Recommended tools for annotation:

1. **Prodigy** - https://prodi.gy/ (Paid, excellent for spaCy)
2. **Label Studio** - https://labelstud.io/ (Free, open source)
3. **Doccano** - https://github.com/doccano/doccano (Free, open source)
4. **spaCy's built-in annotator** - https://github.com/explosion/spacy-annotator

## Sample Annotations

See `sample_annotations.json` for examples of properly annotated legal text.

## Training Data Requirements

- **Minimum:** 1,000 annotated sentences
- **Recommended:** 2,000-5,000 annotated sentences
- **Optimal:** 10,000+ annotated sentences

## Quality Assurance

- Double-check entity boundaries
- Ensure consistent labeling across documents
- Include negative examples (text without entities)
- Balance entity types in training data

## Data Sources

Training data can be sourced from:

- NLR (Nawaloka Legal Reports) judgments
- SLR (Sri Lanka Law Reports) judgments
- BALR (Bar Association Law Reports) judgments
- Supreme Court website
- Court of Appeal website
- Law library archives

## Privacy & Legal Considerations

- Use publicly available judgments only
- Remove personally identifiable information if required
- Ensure compliance with data protection regulations
