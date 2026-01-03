# Legal NER Implementation Guide

## 📋 Section 1.2: Custom Legal NER Model Training - Complete

This document provides a comprehensive guide for implementing and using the Legal Named Entity Recognition (NER) system.

---

## 🎯 Overview

The Legal NER system extracts structured entities from Sri Lankan legal documents, including:

- Case names
- Court names
- Judge names
- Statutory references
- Constitutional articles
- Legal principles
- Dates
- Citations

---

## 📁 Files Created

### 1. **Training Data & Annotations**

```
data/training_data/ner_annotations/
├── README.md                        # Annotation guidelines
└── sample_annotations.json          # Sample annotated data (10 examples)
```

### 2. **Model Directory**

```
backend/models/legal_ner_model/
├── README.md                        # Comprehensive model documentation
├── config.cfg                       # spaCy training configuration
├── training_data/                   # (Created after running prepare script)
│   ├── train.spacy
│   ├── dev.spacy
│   ├── test.spacy
│   └── statistics.json
├── trained_model/                   # (Created after training)
│   ├── config.cfg
│   ├── meta.json
│   ├── ner/
│   └── tok2vec/
└── evaluation/                      # (Created after evaluation)
    └── evaluation_results.json
```

### 3. **Training Scripts**

```
backend/scripts/
├── prepare_ner_training_data.py     # Convert annotations to spaCy format
├── train_ner_model.py               # Train the NER model
├── evaluate_ner_model.py            # Evaluate model performance
├── annotation_utilities.py          # Annotation helper tools
└── add_ner_table.py                 # Database schema update
```

### 4. **Service Layer**

```
backend/app/services/
└── legal_ner_service.py             # NER inference service
```

### 5. **API Routes**

```
backend/app/routes/
└── ner_routes.py                    # NER API endpoints
```

### 6. **Database Models**

```
backend/app/models/
├── legal_entity_model.py            # LegalEntity model
├── document_model.py                # Updated with legal_entities relationship
└── __init__.py                      # Updated imports
```

---

## 🚀 Quick Start Guide

### Step 1: Install Dependencies

```bash
cd backend
pip install spacy
```

### Step 2: Add Training Data

The system includes 10 sample annotations. For production use, you need 1,000+ annotations.

**To add more annotations:**

1. Open `data/training_data/ner_annotations/sample_annotations.json`
2. Add more entries following the format:

```json
{
  "text": "Your legal text here...",
  "entities": [[start_pos, end_pos, "ENTITY_LABEL"], ...]
}
```

**Recommended annotation tools:**

- **Label Studio** (Free): https://labelstud.io/
- **Doccano** (Free): https://github.com/doccano/doccano
- **Prodigy** (Paid): https://prodi.gy/

### Step 3: Prepare Training Data

```bash
python scripts/prepare_ner_training_data.py
```

**Output:**

- Validates annotations
- Splits into train/dev/test sets (80%/10%/10%)
- Saves as spaCy binary format
- Generates statistics

### Step 4: Train the Model

```bash
python scripts/train_ner_model.py
```

**Training process:**

- Creates blank spaCy model
- Trains for 30 iterations
- Evaluates on dev/test sets
- Saves trained model

**Expected time:** 5-15 minutes (depends on data size)

### Step 5: Evaluate the Model

```bash
python scripts/evaluate_ner_model.py
```

**Evaluation metrics:**

- Precision, Recall, F1-Score (overall)
- Per-entity type performance
- Confusion matrix
- Sample prediction errors
- Improvement recommendations

### Step 6: Test the Service

```bash
# Start FastAPI server
uvicorn app.main:app --reload

# Test NER endpoint
curl -X POST "http://localhost:8000/api/ner/extract" \
  -H "Content-Type: application/json" \
  -d '{"text": "In Silva v. Fernando, the Supreme Court held..."}'
```

---

## 📊 Training Data Requirements

| Use Case         | Examples    | Expected F1 | Status                   |
| ---------------- | ----------- | ----------- | ------------------------ |
| **Demo/Testing** | 100-500     | 50-70%      | ⚠️ Current (10 examples) |
| **Development**  | 500-1,000   | 70-80%      | 🎯 Next target           |
| **Production**   | 1,000-5,000 | 80-90%      | ✅ Recommended           |
| **Optimal**      | 10,000+     | 90-95%      | 🌟 Best performance      |

**Current Status:** ⚠️ Demo mode with 10 sample annotations  
**Action Required:** Add 990+ more annotations for production use

---

## 🔌 API Endpoints

### 1. Extract Entities

```http
POST /api/ner/extract
Content-Type: application/json

{
  "text": "In Silva v. Fernando [2020] 1 SLR 345...",
  "return_positions": true
}
```

**Response:**

```json
{
  "entities": {
    "CASE_NAME": ["Silva v. Fernando"],
    "CITATION": ["[2020] 1 SLR 345"],
    "COURT": ["Supreme Court"],
    "ARTICLE": ["Article 12(1)"]
  },
  "total_entities": 4
}
```

### 2. Get Entity Summary

```http
POST /api/ner/extract/summary
Content-Type: application/json

{
  "text": "Your legal text..."
}
```

### 3. Extract Case Metadata

```http
POST /api/ner/extract/metadata
Content-Type: application/json

{
  "text": "Your legal text..."
}
```

### 4. Get Document Entities

```http
GET /api/ner/document/{document_id}/entities
```

### 5. Extract and Save Entities

```http
POST /api/ner/document/{document_id}/extract
```

### 6. Check NER Status

```http
GET /api/ner/status
```

---

## 🗄️ Database Schema

### legal_entities Table

```sql
CREATE TABLE legal_entities (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES legal_documents(id),
    entity_text TEXT NOT NULL,
    entity_type VARCHAR NOT NULL,
    start_pos INTEGER,
    end_pos INTEGER,
    context TEXT,
    confidence FLOAT,
    extracted_at TIMESTAMP DEFAULT NOW()
);
```

**Indexes:**

- `document_id` (foreign key)
- `entity_type` (for filtering)

---

## 🎓 Entity Types Reference

### 1. CASE_NAME

**Examples:**

- "Silva v. Fernando"
- "Attorney General v. Samaraweera"
- "In re Silva"
- "Ex parte Fernando"

**Guidelines:**

- Include both party names
- Include "v." or "vs."
- Include variants like "In re", "Ex parte"

### 2. COURT

**Examples:**

- "Supreme Court"
- "Court of Appeal"
- "High Court of Colombo"
- "SC", "CA", "HC" (abbreviations)

**Guidelines:**

- Full court names preferred
- Include location if mentioned
- Abbreviations acceptable

### 3. JUDGE

**Examples:**

- "Justice Dep P.C.J."
- "Chief Justice Mohan Pieris"
- "Marsoof J."

**Guidelines:**

- Include title (Justice, Chief Justice)
- Include full name or initials
- Include "J." suffix if present

### 4. STATUTE

**Examples:**

- "Prevention of Terrorism Act No. 48 of 1979"
- "Penal Code"
- "Constitution of Sri Lanka"

**Guidelines:**

- Include full statute name
- Include year and number if mentioned
- Short forms acceptable

### 5. ARTICLE

**Examples:**

- "Article 12(1)"
- "Section 300 of the Penal Code"
- "Article 13"

**Guidelines:**

- Include article/section number
- Include subsections: (1), (a), etc.
- Include statute reference if mentioned

### 6. LEGAL_PRINCIPLE

**Examples:**

- "natural justice"
- "res judicata"
- "ultra vires"
- "reasonable doubt"

**Guidelines:**

- Established legal doctrines
- Latin legal phrases
- Common law principles

### 7. DATE

**Examples:**

- "15th March 2019"
- "March 15, 2019"
- "2019-03-15"

**Guidelines:**

- Various date formats acceptable
- Case-relevant dates only

### 8. CITATION

**Examples:**

- "[2020] 1 SLR 345"
- "2015 BALR 123"
- "NLR 234"

**Guidelines:**

- Standard legal citation formats
- Sri Lankan reporters: SLR, NLR, BALR

---

## 🔧 Annotation Tools

### Auto-Annotation Helper

```python
from scripts.annotation_utilities import LegalNERAnnotator

annotator = LegalNERAnnotator()
suggestions = annotator.auto_annotate(text)
```

**Features:**

- Regex-based entity suggestions
- Overlap detection and resolution
- Validation checks
- Export to Prodigy format

**Note:** Auto-suggestions require manual review!

### Manual Annotation Workflow

1. Use annotation tool (Label Studio, Doccano, Prodigy)
2. Load legal documents
3. Mark entities with labels
4. Export to JSON format
5. Validate with `annotation_utilities.py`
6. Add to `sample_annotations.json`
7. Run `prepare_ner_training_data.py`

---

## 📈 Performance Monitoring

### Evaluation Metrics

```bash
python scripts/evaluate_ner_model.py
```

**Key metrics:**

- **Precision**: % of predicted entities that are correct
- **Recall**: % of actual entities that were found
- **F1-Score**: Harmonic mean of precision and recall

**Target: F1 > 85% for production use**

### Error Analysis

The evaluation script provides:

- Confusion matrix
- False negatives (missed entities)
- False positives (incorrect predictions)
- Per-entity type performance

---

## 🔄 Integration with Document Processing

### Automatic Entity Extraction

When a document is processed:

1. Document uploaded → Text extracted (OCR if needed)
2. `document_processor.py` calls `legal_ner_service.py`
3. Entities extracted and saved to `legal_entities` table
4. Frontend displays highlighted entities
5. Entities available for search/filtering

### Manual Trigger

```python
# Via API
POST /api/ner/document/{document_id}/extract

# Via service
from app.services.legal_ner_service import get_ner_service

ner_service = get_ner_service()
entities = ner_service.extract_entities(text)
```

---

## 🐛 Troubleshooting

### Model Not Loading

**Error:** "NER model not found"

**Solution:**

1. Check if model exists: `backend/models/legal_ner_model/trained_model/`
2. Train the model: `python scripts/train_ner_model.py`
3. Verify training completed successfully

### Low Accuracy (F1 < 70%)

**Causes:**

- Insufficient training data
- Poor annotation quality
- Imbalanced entity distribution

**Solutions:**

1. Add more training data (target: 1,000+ examples)
2. Review and fix annotation errors
3. Balance entity types in training set
4. Train for more iterations

### Entity Boundary Errors

**Problem:** Entities cut off or too long

**Solutions:**

1. Review annotation guidelines
2. Ensure consistent annotation of boundaries
3. Add more examples of boundary cases
4. Check tokenization quality

### Memory Issues During Training

**Error:** Out of memory

**Solutions:**

1. Reduce batch size in `config.cfg`
2. Train on GPU if available
3. Process documents in smaller chunks

---

## 📚 Next Steps

### Immediate (Week 2)

- [ ] Collect 100+ more annotations
- [ ] Retrain model with larger dataset
- [ ] Test on real legal documents
- [ ] Integrate with document upload pipeline

### Short-term (Week 3-4)

- [ ] Reach 1,000 annotations
- [ ] Achieve F1 > 80%
- [ ] Add entity highlighting in frontend
- [ ] Create search by entity feature

### Long-term (Month 2-3)

- [ ] 5,000+ annotations
- [ ] F1 > 90%
- [ ] Fine-tune with BERT-based model
- [ ] Add confidence scoring
- [ ] Entity linking and resolution

---

## 🎯 Success Criteria

### Phase 1 (Current) ✅

- [x] Training pipeline created
- [x] Sample data (10 examples)
- [x] Model training script
- [x] Evaluation framework
- [x] API endpoints
- [x] Database schema
- [x] Service layer

### Phase 2 (Week 2-4) 🎯

- [ ] 1,000+ annotations
- [ ] F1 score > 85%
- [ ] Production-ready model
- [ ] Frontend integration
- [ ] Real-world testing

### Phase 3 (Month 2-3) 🌟

- [ ] 5,000+ annotations
- [ ] F1 score > 90%
- [ ] Advanced features (confidence, linking)
- [ ] Performance optimization
- [ ] Expert validation

---

## 📖 Resources

### Documentation

- **spaCy NER**: https://spacy.io/usage/training#ner
- **Legal NLP Papers**: Search "Legal NER" on arXiv
- **Sri Lankan Law**: http://www.lawnet.gov.lk/

### Tools

- **Label Studio**: https://labelstud.io/
- **Doccano**: https://github.com/doccano/doccano
- **Prodigy**: https://prodi.gy/

### Datasets

- NLR (Nawaloka Legal Reports)
- SLR (Sri Lanka Law Reports)
- BALR (Bar Association Law Reports)
- Supreme Court website judgments

---

## ✅ Checklist

### Setup

- [x] Install spaCy
- [x] Create training data structure
- [x] Setup model directory
- [x] Create training scripts
- [x] Setup database schema
- [x] Create API endpoints
- [x] Create service layer

### Training

- [x] Prepare sample annotations (10 examples)
- [ ] Collect 1,000+ annotations (⚠️ IN PROGRESS)
- [ ] Train initial model
- [ ] Evaluate performance
- [ ] Iterate and improve

### Integration

- [x] API endpoints working
- [x] Database model created
- [ ] Frontend integration (NEXT)
- [ ] Document processing integration (NEXT)
- [ ] Search integration (NEXT)

### Testing

- [ ] Unit tests for NER service
- [ ] Integration tests for API
- [ ] Performance testing
- [ ] User acceptance testing

---

## 🎉 Completion Status

**Section 1.2: Custom Legal NER Model Training**

**Status: 80% Complete** ✅

**Completed:**

- ✅ Training infrastructure
- ✅ Sample annotations
- ✅ Training pipeline
- ✅ Evaluation framework
- ✅ API endpoints
- ✅ Database integration
- ✅ Service layer
- ✅ Documentation

**Remaining:**

- ⚠️ Collect sufficient training data (1,000+ examples)
- ⚠️ Train production model
- ⚠️ Frontend integration
- ⚠️ Document processing integration

**Ready for:** Development testing with sample data  
**Production-ready:** After collecting 1,000+ annotations

---

**Last Updated:** December 9, 2025  
**Project:** AI-Generated Sri Lankan Legal Case Summarizer  
**Student ID:** IT22053282
