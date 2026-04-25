# FORMATTING INSTRUCTIONS (APPLY IN MICROSOFT WORD BEFORE SUBMISSION)

Per SLIIT “Guidelines on Documentation and Submission of Dissertations” and your module requirements:

| Element | Specification |
|--------|----------------|
| Font (body) | Times New Roman, 12 pt, sentence case |
| Chapter titles | ALL CAPS, Bold, 14 pt |
| Section headings | Title case, Bold, 12 pt (SLIIT); align with supervisor if “ALL CAPS” was required only for chapter titles |
| Sub-section headings | Sentence case, Bold, 12 pt |
| Line spacing | 1.5 for main body; **single** for Abstract, tables, and long indented quotations |
| Abstract text | SLIIT specifies Times New Roman **11 pt** for abstract body (Title: 12 pt Bold); verify with supervisor |
| Margins | 40 mm left and bottom; 25 mm top and right |
| Preliminary pagination | Lower-case Roman numerals (i, ii, iii…), **centred bottom** (no page number on Title page) |
| Body pagination | Arabic numerals (1, 2, 3…), **right-aligned bottom**, starting at **Chapter 1** |
| Minimum size | SLIIT: minimum **50 A4 pages** total |

**Note:** Your requested preliminary order is Table of Contents → List of Figures → List of Tables → List of Abbreviations. SLIIT’s printed guideline lists List of Tables before List of Figures; **confirm order with your supervisor** if the faculty template differs.

---

# TITLE PAGE

**(Centred; no page number)**

**AI-GENERATED NLR/SLR CASE SUMMARIZER FOR SRI LANKAN LEGAL JUDGMENTS**

**USING NATURAL LANGUAGE PROCESSING, RETRIEVAL-AUGMENTED GENERATION, AND LEGAL CORPUS ENGINEERING**

**BOGAHAWATTEGE K S**  
**IT22053282**

Submitted in partial fulfillment of the requirements for the  
**B.Sc. (Hons) Degree in Information Technology Specialized in Software Engineering**

**Department of Information Technology**  
**Sri Lanka Institute of Information Technology**  
**Sri Lanka**

**April 2026**

---

# DECLARATION

**(Page i — Roman numeral, centred bottom)**

I declare that this is my own work and this dissertation does not incorporate without acknowledgement any material previously submitted for a Degree or Diploma in any other University or institute of higher learning and to the best of my knowledge and belief it does not contain any material previously published or written by another person except where the acknowledgement is made in the text.

Also, I hereby grant to Sri Lanka Institute of Information Technology, the non-exclusive right to reproduce and distribute my dissertation, in whole or in part in print, electronic or other medium. I retain the right to use this content in whole or part in future works (such as articles or books).

___________________________  
Signature:

___________________________  
Date:

---

**Supervisor certification**

The above candidate has carried out research for the bachelor’s degree Dissertation under my supervision.

___________________________  
Signature of the supervisor:

___________________________  
Date:

**(If co-supervised, duplicate supervisor block as required.)**

---

# ABSTRACT

**(Page ii — single spacing; max 300 words; keywords 3–5)**

**Abstract**

Superior court judgments published in the New Law Reports (NLR) and Sri Lanka Law Reports (SLR) are authoritative but lengthy and linguistically dense. Non-specialists, students, journalists, and civil society actors therefore face a persistent accessibility barrier when attempting to understand facts, issues, reasoning, and orders. This dissertation presents the design, implementation, and evaluation of a web-centred AI legal summarization system tailored to Sri Lankan NLR/SLR PDFs. The methodology combines strict document validation (accepting only original law reports), PDF text extraction with OCR fallback, named entity recognition for legal spans, fundamental rights detection, citation parsing, structure-aware chunking, dense retrieval with FAISS over BGE embeddings, and grounded abstractive generation using an LLM service (Gemini via OpenAI-compatible API when configured, with FLAN-T5 and extractive fallbacks). A FastAPI backend exposes ingestion, analysis, RAG, and search routes; a React client supports upload, visualization, and export-oriented workflows. Google Colab notebooks support large-scale PDF processing into structured JSON for training and evaluation data. Results are reported in terms of pipeline reliability, retrieval behaviour, summary groundedness constraints, and qualitative review of outputs on real judgments. The work concludes that retrieval-grounded summarization with explicit anti-hallucination rules offers a practical path to safer legal AI prototypes, while highlighting risks around scanned PDFs, multilingual nuance, and professional reliance. Recommendations include expanding annotated corpora, human-in-the-loop evaluation with legal experts, and formal ethics review before any public deployment.

**Keywords:** legal document summarization, Sri Lankan judgments, retrieval-augmented generation, natural language processing, FastAPI

---

# ACKNOWLEDGEMENT

**(Page iii)**

I wish to express my sincere gratitude to my supervisors, **Ms. Thilini Jayalath** and **Mr. Kavinga Yapa Abeywardena**, for their guidance, feedback, and encouragement throughout this research. Their advice materially improved both the technical rigour and the clarity of presentation of this work.

I thank the Department of Information Technology, Sri Lanka Institute of Information Technology, for the academic environment, resources, and administrative support necessary to complete this dissertation.

I acknowledge my **project group members** (where applicable) for collaboration, code reviews, and shared responsibility for integration, testing, and documentation. Any **individual** contributions are summarized under “Summary of Each Student’s Contribution.”

I also thank the open-source communities behind **FastAPI**, **PyTorch**, **Hugging Face Transformers**, **sentence-transformers**, **FAISS**, **React**, and related libraries, without which rapid prototyping at this scale would not have been feasible.

Finally, I thank family and friends for their patience and support during intensive development and evaluation periods.

---

# TABLE OF CONTENTS

**(Page iv — update page numbers in Word)**

| Section | Page |
|--------|------|
| Declaration | i |
| Abstract | ii |
| Acknowledgement | iii |
| Table of Contents | iv |
| List of Figures | v |
| List of Tables | vi |
| List of Abbreviations | vii |
| **CHAPTER 1: INTRODUCTION** | **1** |
| 1.1 Background and Literature Survey | 1 |
| 1.1.1 Sri Lankan Superior Court Judgments and Law Reporting | 1 |
| 1.1.2 Legal NLP and Summarization: International Context | 3 |
| 1.1.3 Retrieval-Augmented Generation and Grounding | 5 |
| 1.1.4 Named Entity Recognition and Legal Structure | 7 |
| 1.1.5 Constitutional Rights and Public Legal Literacy | 8 |
| 1.2 Research Gap | 9 |
| 1.3 Research Problem | 11 |
| 1.4 Research Objectives | 12 |
| 1.4.1 Main Objective | 12 |
| 1.4.2 Specific Objectives | 13 |
| **CHAPTER 2: METHODOLOGY** | **16** |
| 2.1 Overview of the Proposed System | 16 |
| 2.2 System Architecture | 17 |
| 2.3 Data Collection and Preprocessing (Corpus and Colab) | 22 |
| 2.4 Model Design: Summarization, NER, Embeddings, and RAG | 26 |
| 2.5 Algorithms and Core Methods | 32 |
| 2.6 Frontend and Backend Interaction | 36 |
| 2.7 Commercialization Aspects | 39 |
| 2.8 Testing and Implementation | 41 |
| **CHAPTER 3: RESULTS AND DISCUSSION** | **44** |
| 3.1 Results | 44 |
| 3.2 Research Findings | 48 |
| 3.3 Discussion | 50 |
| 3.4 Summary of Each Student’s Contribution | 52 |
| **CHAPTER 4: CONCLUSION** | **54** |
| References | 57 |
| Glossary | 60 |
| Appendices | 62 |

---

# LIST OF FIGURES

**(Page v)**

| Figure | Title | Page |
|--------|-------|------|
| Figure 1.1 | High-level problem context: accessibility of NLR/SLR judgments | 2 |
| Figure 2.1 | End-to-end system architecture (client, API, services, data stores) | 18 |
| Figure 2.2 | Document ingestion pipeline (stages 1–17) | 20 |
| Figure 2.3 | RAG retrieval and grounded generation flow | 28 |
| Figure 2.4 | Deployment view (development vs cloud) | 40 |
| Figure 3.1 | Example upload response JSON (pipeline stages) | 45 |

**[Figure 1.1: Accessibility context — stakeholders vs long judgments]**  
**[Figure 2.1: System Architecture Diagram — insert your diagram]**  
**[Figure 2.2: Ingestion Pipeline — insert swimlane or block diagram]**  
**[Figure 2.3: RAG + LLM — insert sequence diagram]**  
**[Figure 2.4: Deployment — insert AWS/DigitalOcean/Vercel diagram as used]**  
**[Figure 3.1: Screenshot of API response or network tab — anonymized]**  

---

# LIST OF TABLES

**(Page vi)**

| Table | Title | Page |
|--------|-------|------|
| Table 2.1 | Major REST API route groups and purposes | 24 |
| Table 2.2 | Pipeline stages and typical artefacts persisted | 25 |
| Table 2.3 | Models and libraries used in the implementation | 33 |
| Table 3.1 | Qualitative evaluation dimensions for legal summaries | 46 |
| Table 3.2 | Summarization paths: grounding and evidence | 47 |

*(Full evidence checklist for tables and figures: see `docs/Dissertation_Evidence_Tables_and_Screenshots.md` in the repository.)*

---

# LIST OF ABBREVIATIONS

**(Page vii)**

| Abbreviation | Expansion |
|--------------|-----------|
| API | Application Programming Interface |
| BART | Bidirectional and Auto-Regressive Transformers |
| BGE | BAAI General Embedding |
| CORS | Cross-Origin Resource Sharing |
| CRUD | Create, Read, Update, Delete |
| DB | Database |
| FAISS | Facebook AI Similarity Search |
| FLAN-T5 | Fine-tuned Language Net – T5 |
| JSON | JavaScript Object Notation |
| LLM | Large Language Model |
| MMR | Maximal Marginal Relevance |
| NER | Named Entity Recognition |
| NLP | Natural Language Processing |
| NLR | New Law Reports |
| OCR | Optical Character Recognition |
| PDF | Portable Document Format |
| RAG | Retrieval-Augmented Generation |
| REST | Representational State Transfer |
| SLR | Sri Lanka Law Reports |
| SLLR | Sri Lanka Law Reports (variant naming in citations) |
| TF-IDF | Term Frequency–Inverse Document Frequency |
| UI | User Interface |

---

# CHAPTER 1: INTRODUCTION

**(Start Arabic page numbering at 1; 1.5 line spacing)**

## 1.1 Background and Literature Survey

### 1.1.1 Sri Lankan Superior Court Judgments and Law Reporting

Sri Lanka’s superior courts produce judgments that shape statutory interpretation, administrative law, fundamental rights jurisprudence, and commercial regulation. Selected decisions are reported in serials such as the **New Law Reports (NLR)** and **Sri Lanka Law Reports (SLR)**. These publications are indispensable for lawyers and judges, yet their **volume and complexity** create friction for wider society. A single reported judgment may span dozens of pages, embed dense citations, and presuppose familiarity with procedural history, evidentiary rules, and constitutional provisions.

From an information systems perspective, law reports are **semi-structured documents**: they contain predictable rhetorical sections (facts, issues, analysis, reasoning, disposition) but vary by court, era, editorial style, and scanning quality. Digital distribution increasingly occurs through PDFs, yet **PDF is not a semantic format**; “text” may be selectable, or may be a bitmap requiring OCR. This heterogeneity is a first-order engineering constraint for any national legal AI system.

The present project, as articulated in the proposal **“AI-Generated NLR/SLR Case Summarizer for Sri Lankan Legal Judgments”** (Project code **25-26J-475**), situates itself in this context: it aims to **lower the comprehension barrier** while respecting the **authoritative status** of the underlying judgments.

### 1.1.2 Legal NLP and Summarization: International Context

Legal natural language processing has matured into a substantial research area spanning **summarization**, **citation network analysis**, **statutory entailment**, **contract review**, and **question answering**. Summarization approaches fall broadly into:

1. **Extractive summarization**, which selects salient units (typically sentences) from the source. Classical signals include **TF-IDF**, graph-based ranking, and discrete optimization under length constraints. Extractive methods offer **faithfulness** (every sentence appears in the source) but may miss **global paraphrase** or cohesive rewriting preferred by human readers.

2. **Abstractive summarization**, which generates new text conditioned on the source. Pre-trained transformer summarizers (e.g., BART-family models) can produce fluent summaries but are prone to **hallucination**—stating facts not grounded in the document—an unacceptable risk in legal settings.

3. **Hybrid and control-centric workflows**, including **section-aware summarization**, **template-guided generation**, and **multi-document** synthesis. For judgments, templates aligned with **Facts / Issues / Analysis / Reasoning / Decision** often match professional reading practices.

International systems rarely transfer directly to Sri Lanka because of differences in **citation formats**, **constitutional text**, **procedural vocabulary**, and **reporting conventions**. A Sri Lankan solution must therefore combine general NLP advances with **local corpus engineering** and **jurisdiction-specific validation rules**.

### 1.1.3 Retrieval-Augmented Generation and Grounding

Retrieval-Augmented Generation (**RAG**) mitigates some hallucination risks by conditioning generation on **retrieved passages** from a trusted corpus. In the implemented system, judgment text is split into **chunks** with metadata (e.g., inferred **section_type**, **article references**, **citation references**). Chunks are embedded with **sentence-transformers** (default **BAAI/bge-base-en-v1.5**) and indexed in **FAISS** for similarity search. At query or summarization time, the retriever returns a bounded context window, and the **LLMGenerationService** prompts the model to use **only** that context.

The codebase’s design philosophy is explicit: prompts include **strict operational rules**—no fabrication, preserve citations, and respond “not stated” when the context is insufficient. This aligns with emerging best practices in **grounded legal AI**, where provenance and abstention are as important as fluency.

### 1.1.4 Named Entity Recognition and Legal Structure

Legal NER identifies spans such as parties, courts, statutes, and citations. The project includes a **spaCy**-compatible **legal_ner** model path (`backend/models/legal_ner`) integrated through `NLPAnalyzer` and `legal_ner_service`. NER supports downstream UI features (entity lists), analytics, and potential linking to external knowledge bases.

Separately, **document structure** is modelled through hybrid classification (BERT / hybrid components referenced in the ingestion pipeline) and **LegalChunker** heuristics that map regex patterns to section classes such as **FACTS**, **ISSUES**, **LEGAL_ANALYSIS**, **REASONING**, **JUDGMENT**, and **ORDERS**. Structure is not merely cosmetic; it drives **chunk annotations** that improve interpretability of retrieved spans for users and evaluators.

### 1.1.5 Constitutional Rights and Public Legal Literacy

The Sri Lankan Constitution entrenches fundamental rights in Chapter III. Many superior court judgments engage these provisions directly or indirectly. The implemented system therefore includes **rights detection** and a **constitutional RAG module** (initialised at application startup in `main.py`) intended to connect judgment discourse to constitutional articles and explanations where available.

Public legal literacy is constrained not only by reading time but by **conceptual vocabulary**. The repository includes a **plain language converter** service used in multi-level summarization routes, reflecting a product stance that **accessibility** should be an explicit engineering requirement, not an afterthought.

**[Figure 1.1: Stakeholder diagram — citizens, students, journalists, NGOs, practitioners vs barriers]**  

### 1.1.6 Information Behaviour of Non-Lawyer Stakeholders

Empirical studies of legal information seeking consistently show that lay users **scan**, **keyword search**, and **abandon** long documents when cognitive load exceeds a threshold. Law students, though more trained, still face **time scarcity** during exam preparation and moot drafting. Journalists operate under **deadline pressure** and require **quotable**, **checkable** distillations. NGOs working on fundamental rights monitoring need **repeatable extraction** of which articles were argued, how courts framed proportionality, and what remedy issued.

These behaviours imply design requirements beyond “a shorter text.” The system must surface **structure** (facts vs holding), preserve **citations** for verification, and degrade gracefully when PDF extraction is weak. The implemented architecture mirrors these needs by persisting **chunk metadata** and returning **pipeline telemetry** so interfaces can explain *what succeeded* and *what was skipped*.

### 1.1.7 Related Work in Summarization Evaluation

ROUGE remains a baseline in summarization research because it is cheap and reproducible. However, legal summarization evaluation increasingly adopts **checklist methods**, **entity-centric recall**, and **post-hoc claim verification** against source spans. This dissertation adopts a **dual evaluation stance**: (1) lightweight automatic metrics where applicable, and (2) a **qualitative rubric** aligned with legal reading tasks (Table 3.1). Future iterations should add **expert pairwise ranking** (lawyer prefers A vs B) with inter-annotator agreement.

### 1.1.8 Software Engineering Perspective

Legal AI is not only a modelling problem; it is a **systems integration** problem. The repository demonstrates **separation of concerns**: routers remain thin; **services** encapsulate ML operations; **models** define persistence; scripts support **offline batch** processing. Such modularity is essential for **team development**, **testing**, and **incremental deployment**—properties that academic prototypes often neglect but SLIIT industry-oriented degrees emphasize.

### 1.1.9 Sri Lankan Digital Legal Ecosystem (Contextual)

While this dissertation does not conduct a national survey, it acknowledges institutional publishers, libraries, and emerging digitization initiatives. The prototype’s acceptance of **user-supplied PDFs** positions it as a **research and education tool** rather than an official publisher replacement. Any roadmap toward national scale must engage **copyright**, **terms of use** for law reports, and **court data governance**.

---

## 1.2 Research Gap

Despite global progress in legal NLP, several gaps persist in the Sri Lankan context:

1. **Corpus and tooling gap:** There is no commoditized, open, end-to-end pipeline that ingests **local NLR/SLR PDFs**, validates authenticity, extracts text reliably, and produces **structured, grounded summaries** with explicit anti-hallucination controls.

2. **Jurisdictional grounding gap:** General-domain summarizers lack sensitivity to **SLR/NLR citation grammar**, **local court hierarchies**, and **constitutional article referencing patterns**.

3. **Trust and safety gap:** Abstractive models without retrieval grounding can **invent** holdings. The gap is not only technical but **epistemic**: users may trust a fluent paragraph that misstates the ratio decidendi.

4. **Operational integration gap:** Research prototypes often stop at notebooks. There is a gap in **deployable architectures** combining **React** frontends, **FastAPI** services, **vector indexes**, **relational persistence**, and **observable pipelines** suitable for iterative user testing.

5. **Evaluation gap:** ROUGE-like scores do not capture **legal adequacy**. The field lacks widely adopted **Sri Lankan benchmark suites** with expert annotations for summarization fidelity.

This dissertation documents a system intended to **narrow** gaps (1)–(5) through engineering integration rather than claiming exhaustive legal validation.

### 1.2.1 Corpus Gap in Detail

Many open legal NLP resources centre on **United States**, **European Union**, or **United Kingdom** corpora with mature case identifiers (e.g., neutral citations). Sri Lankan materials exhibit **heterogeneous filenames**, **publisher-specific layouts**, and **historical scanning artefacts** from older volumes. Building `combined_legal_cases.json` in Colab is therefore not a convenience but a **research method**: it forces explicit handling of **batch extraction**, **error logging**, and **reproducible manifests** (`corpus_pdf_paths.json`).

### 1.2.2 Multilingual and Vernacular Gap (Forward-Looking)

Sri Lankan judicial discourse is predominantly English in reported superior court judgments, yet practitioners and citizens also require **Sinhala** and **Tamil** explanations. The repository’s glossary artefacts (`legal_glossary_si_en_ta.json`) signal intent toward **multilingual literacy**, even if the current ingestion path is English-forward. The gap remains **substantial**: tokenization, morphology, and aligned summarization corpora require dedicated funding and linguist involvement.

---

## 1.3 Research Problem

**How can NLR/SLR judgment PDFs be processed, represented, and summarized such that (a) outputs are faithful to the source judgment, (b) key legal structure and references are preserved, and (c) the solution is implementable as a modular web system suitable for iterative evaluation in Sri Lanka?**

Sub-problems include: robust **text extraction** from heterogeneous PDFs; **rejection** of non-original documents (briefs, digests) that would poison training or mislead users; **scalable chunking and embedding**; **retrieval** that surfaces representative passages; and **generation** that respects explicit grounding constraints under API rate limits and hardware variability.

---

## 1.4 Research Objectives

### 1.4.1 Main Objective

To **design, implement, and evaluate** an integrated **AI-assisted legal summarization system** for **Sri Lankan NLR/SLR judgments**, combining **NLP**, **RAG**, **LLM-based generation with fallbacks**, and a **web application**, supported by **corpus preprocessing workflows** suitable for **Colab** execution.

### 1.4.2 Specific Objectives

1. **Corpus engineering:** Build pipelines to collect and preprocess NLR/SLR PDFs into structured forms suitable for database ingestion, annotation, and model development (including **Colab** notebooks such as `Build_Corpus_Colab.ipynb` and `colab/preprocessing.ipynb`).

2. **Document understanding:** Implement extraction, cleaning, metadata inference, **NER**, **rights detection**, **citation parsing**, and **structure classification** within a unified ingestion path (`run_ingestion_pipeline`).

3. **Retrieval layer:** Implement chunk embeddings (**BGE**), **FAISS** indexing (`RAGServiceV2`), and **MMR**-style diversity considerations for better coverage of judgment sections.

4. **Summarization layer:** Provide **multi-level summaries** (executive and detailed) using **LLMGenerationService** with **Gemini** (OpenAI-compatible client) when keys are configured, else **FLAN-T5** local generation, plus **extractive** fallbacks (`NLPAnalyzer`, historical **BART** paths in legacy routes).

5. **Application integration:** Expose coherent **REST** endpoints under `FastAPI` (`document_routes`, `summary_routes`, `rag_v2_routes`, `search_routes`, `ner_routes`, `user_routes`) with **CORS** configured for known deployment origins.

6. **User interface:** Deliver a **React** application (see root `package.json`: React 19, MUI, Redux Toolkit, axios, react-dropzone, react-pdf) enabling **upload**, progress feedback, and **summary / entity / rights** visualization.

7. **Quality assurance:** Implement automated tests and manual test scripts (`test_api_response.py`, `test_ner_api.py`, etc.) and document limitations (OCR dependence, API quotas).

8. **Ethics and deployment prudence:** Articulate limitations, misuse potential, and **non-replacement** of professional advice.

---

# CHAPTER 2: METHODOLOGY

## 2.1 Overview of the Proposed System

The system follows a **three-tier pattern**:

1. **Presentation tier:** React SPA communicating over HTTPS/HTTP with JSON payloads.
2. **Application tier:** FastAPI routers validating uploads, orchestrating pipelines, querying ORM models, and returning structured JSON.
3. **Data & intelligence tier:** Relational database (development defaults include SQLite per `README.md`; production may use PostgreSQL scripts in `backend/scripts`), **FAISS** vector store files (`faiss_chunks_v2.bin`, `faiss_chunks_v2_meta.json`), optional Elasticsearch references in comments (legacy migration notes in `main.py`), and **file system** storage under `uploaded_docs/`.

The **canonical ingestion path** is `POST /api/documents/upload-sri-lanka`, which saves the PDF, invokes `run_ingestion_pipeline`, and returns `document_id`, pipeline telemetry, and metadata such as `court`, `year`, and `case_number`.

**[Figure 2.1: System Architecture Diagram]**  

---

## 2.2 System Architecture

### 2.2.1 Logical Decomposition

**Routers (API surface)**  
- `document_routes.py`: Upload and corpus-linked PDF URL resolution (`/past-case-pdf`).  
- `summary_routes.py`: Analysis endpoints including multi-level summarization and legacy BART/NLP paths.  
- `rag_v2_routes.py`: RAG v2 upload, retrieval, QA, and summarization grounded in chunks.  
- `search_routes.py`: Search API (project migrated emphasis toward FAISS in comments).  
- `ner_routes.py`: NER-specific endpoints.  
- `user_routes.py`: User accounts and history models as scoped.

**Core services**  
- `document_processor.py` (invoked by pipeline): extraction, validation, cleaning, persistence.  
- `document_ingestion_pipeline.py`: **single entry-point** orchestrating stages 1–17 (as documented in module docstring).  
- `legal_chunker.py`: sentence-aware, overlap-aware chunking with **citation integrity** and **article** regex extraction.  
- `embedding_service.py`: **SentenceTransformer** wrapper with BGE query prefixing for retrieval.  
- `rag_service_v2.py`: FAISS **IndexFlatIP** on **L2-normalized** embeddings (cosine via inner product), index persistence, rebuild from DB.  
- `llm_generation_service.py`: grounded prompts for **executive** (~150 words) and **detailed** (~700 words) analyses, constitutional notes, precedent comparison, QA.  
- `constitutional_rag_module.py`, `sri_lanka_legal_engine.py`, `plain_language_converter.py`: jurisdiction-specific reasoning and simplification.  
- `nlp_analyzer.py`: **TF-IDF** extractive summarization and keyword extraction; optional **spaCy** NER integration.

**Models and persistence**  
ORM models include `LegalDocument`, `DocumentChunk`, `LegalEntity`, rights and citation tables (see `app/models`). Migrations may be managed with Alembic (`backend/alembic`).

### 2.2.2 Runtime Lifecycle

On startup (`main.py`), the service initializes the database, attempts **non-blocking** warm-up of `RAGServiceV2` and `ConstitutionalRAGModule`, and exposes health routes `/` and `/health`. This design acknowledges that **heavy models** may fail on resource-constrained hosts without crashing the API shell.

### 2.2.3 Security and Configuration

Secrets (e.g., `OPENAI_API_KEY` for Gemini endpoint) are environment-driven. The LLM service supports **key rotation** on HTTP 429. Optional ingestion flag `INGESTION_SKIP_POST_CHUNK_LLM` allows faster uploads by skipping slow post-chunk LLM passes.

**[Figure 2.2: Ingestion pipeline diagram — correlate with Table 2.2]**  

**Table 2.1 Major REST API route groups and purposes**

| Route group (base path) | Main purpose | Representative endpoints |
|-------------------------|--------------|---------------------------|
| `/api/documents` | Upload NLR/SLR PDF; full ingestion pipeline | `POST /api/documents/upload-sri-lanka`; `GET /api/documents/past-case-pdf` |
| `/api/analysis` | Summaries, structure, entities, corpus tools | e.g. `GET .../summarize/multi-level/{document_id}`, `GET .../summarize/executive/{document_id}`, `GET .../llm-status`, `POST .../summarize/with-local-context` |
| `/api/rag` | RAG v2: job-based upload, retrieve, grounded LLM | `POST /api/rag/upload`, `GET /api/rag/process/{job_id}`, `POST /api/rag/retrieve`, `GET /api/rag/summarize/{doc_id}`, `POST /api/rag/chat` |
| `/api/search` | Document search / suggest / advanced | `POST /api/search/documents`, `GET /api/search/suggest`, `POST /api/search/advanced` |
| `/api/ner` | Standalone legal NER | `POST /api/ner/extract`, `GET /api/ner/document/{document_id}/entities` |
| `/api` (user routes) | User language preference | `POST /api/set-language`, `GET /api/language/{user_id}` |
| `/` | API health | `GET /health` |

---

## 2.3 Data Collection and Preprocessing (Corpus and Colab)

### 2.3.1 Data Sources

The repository includes **Sri Lanka legal corpus artefacts** under `data/sri_lanka_legal_corpus/` (e.g., constitution articles, glossary JSON), **training data** for NER and document structure (`data/training_data/...`), and processed path manifests (e.g., `data/processed/corpus_pdf_paths.json`). These artefacts support **supervised fine-tuning**, **evaluation**, and **lexical resources** for rights and definitions.

### 2.3.2 Google Colab Workflows

The notebook `backend/scripts/Build_Corpus_Colab.ipynb` documents a practical pattern: install `pdfplumber`, ingest ZIPs of PDFs or Google Drive folders, extract text, and export **`combined_legal_cases.json`** into `data/processed/`. This addresses **scalability**: attorneys’ machines may not tolerate batch OCR; **Colab GPUs/TPUs** and Drive bandwidth decentralize compute.

`colab/preprocessing.ipynb` and `colab/Sri_Lanka_Fundamental_Rights_Processor.ipynb` align with **constitutional processing** and rights-centric corpora. The methodology is **reproducible**: notebooks specify installation cells, directory conventions, and expected outputs.

### 2.3.3 Validation Policy

The pipeline rejects documents that fail `DocumentProcessor.is_sri_lanka_legal_document`, enforcing the product rule: **only original NLR/SLR reports**, not student briefs or secondary analyses. This is a **data ethics** choice: it reduces training contamination and user confusion.

### 2.3.4 Text Extraction and OCR

`DocumentProcessor` (invoked by the pipeline) uses **pdfplumber-first** extraction with **OCR fallback** when needed (as described in pipeline comments). Image-only PDFs may yield **short extracted text**; the pipeline raises `ValueError` when text is too short for reliable summaries, nudging users toward text-layer PDFs or OCR dependencies.

---

## 2.4 Model Design: Summarization, NER, Embeddings, and RAG

### 2.4.1 Summarization Strategy

The system employs **layered summarization**:

- **Primary:** Grounded **LLM** generation from retrieved chunks (`LLMGenerationService`), with prompts mandating fidelity. When API keys exist, the service uses **Gemini** (`gemini-flash-latest`) via OpenAI-compatible base URL `https://generativelanguage.googleapis.com/v1beta/openai/`.

- **Secondary local:** **FLAN-T5** (`google/flan-t5-base`) for development or outage scenarios.

- **Tertiary extractive:** **TF-IDF sentence ranking** (`NLPAnalyzer.extractive_summary`) used in legacy routes or when neural models fail.

- **Historical / auxiliary:** `BARTLegalSummarizer` (`facebook/bart-large-cnn`) appears in `summary_routes` as an optional path; comments in `main.py` note migration toward OpenAI + FAISS—document honestly as **evolutionary** design during the project timeline.

### 2.4.2 Embeddings and Retrieval

`EmbeddingService` defaults to **BAAI/bge-base-en-v1.5** with **normalized** embeddings. For queries, `encode_for_retrieval` prepends the BGE instruction string to match training assumptions. `RAGServiceV2` stores chunk metadata including `section_type`, `article_refs`, and `citation_refs`, enriching UI and downstream analytics.

### 2.4.3 NER Model

A custom spaCy model is loaded from `backend/models/legal_ner` when present. The trained pipeline’s NER label set is defined in `meta.json` (spaCy version constraint `>=3.8.11,<3.9.0`): **ARTICLE**, **CASE_NAME**, **CITATION**, **COURT**, **DATE**, **JUDGE**, **LEGAL_PRINCIPLE**, **STATUTE**.

### 2.4.4 Constitutional and Precedent Components

Services such as `constitutional_rag_module.py` and `precedent_rag_engine.py` (present in tree) support **jurisdiction-aware** analysis beyond generic summarization. The dissertation should summarize their **intended behaviour** and note any **feature flags** or partial integrations evidenced by imports and startup logs.

**Table 2.3 Models, libraries, and identifiers used in the implementation**

| Layer | Technology / identifier | Role |
|-------|-------------------------|------|
| Web API | FastAPI (`version="1.0"` in `main.py`) | REST server, CORS, router mounting |
| Frontend | React ^19.2.0, MUI ^7.x, axios ^1.13.2, react-dropzone, react-pdf (root `package.json`) | Upload UI, API calls, PDF preview |
| ORM / DB | SQLAlchemy; SQLite default per `README.md` | `LegalDocument`, `DocumentChunk`, entities, citations |
| PDF text | pdfplumber | Primary extraction in `document_processor.py` |
| OCR | pytesseract, pdf2image, PIL | Fallback when little text extracted |
| Embeddings | sentence-transformers; **BAAI/bge-base-en-v1.5** | Chunk and query vectors (`embedding_service.py`) |
| Vector index | FAISS `IndexFlatIP`; files `faiss_chunks_v2.bin`, `faiss_chunks_v2_meta.json` | Similarity search; cosine via normalized inner product |
| Retrieval | `RAGServiceV2`; MMR re-ranking (`mmr_lambda` e.g. 0.6–0.7) | Diverse top-*k* chunks |
| Local LLM | `google/flan-t5-base` | Fallback generation (`llm_generation_service.py`) |
| API LLM (when configured) | Gemini `gemini-flash-latest` via OpenAI-compatible client | Primary grounded generation |
| Optional summarizer | `facebook/bart-large-cnn` | Legacy / alternate summarization path |
| Extractive baseline | scikit-learn `TfidfVectorizer`, NLTK `sent_tokenize` | Baseline summary + keywords (`nlp_analyzer.py`) |
| NER | spaCy pipeline in `backend/models/legal_ner` | Eight entity types (see §2.4.3) |
| Colab corpus | `Build_Corpus_Colab.ipynb`, `colab/preprocessing.ipynb` | Batch PDF → JSON for `data/processed/` |

---

## 2.5 Algorithms and Core Methods

### 2.5.1 Extractive Summarization (TF-IDF)

Given sentence segmentation, a **TF-IDF matrix** is constructed per sentence. Sentences with highest aggregate TF-IDF mass are selected until the budget `n_sentences` is met. Complexity scales with vocabulary and sentence count; this is **transparent** and **faithful**, useful as a baseline.

### 2.5.2 Chunking with Legal Constraints

`LegalChunker` implements: sentence-boundary splits; approximate token sizing; overlap; **regex** detection of SL citations and constitutional **Articles**; and **SECTION_PATTERNS** mapping rhetorical cues to labels. This is a **hybrid rules + ML** philosophy: rules handle brittle local phenomena; classifiers handle broader segmentation.

### 2.5.3 FAISS Indexing

Embeddings are **L2-normalized**; **IndexFlatIP** inner product approximates **cosine similarity**. The index rebuilds from DB when disk files are absent. New chunks can be appended via `add_chunks_to_index`, supporting incremental growth.

### 2.5.4 Grounded Prompting

The `BASE_SYSTEM` and task prompts in `llm_generation_service.py` operationalize **context-only** answers, with explicit instructions for **missing information** handling. This is an algorithm of **discourse control** rather than numeric optimization, but it is central to **trust**.

**Important code pattern (illustrative snippet — do not dump full file):**

```python
# llm_generation_service.py (conceptual structure)
BASE_SYSTEM = """You are a Master Legal Research Assistant ...
STRICT OPERATIONAL RULES:
1. DATA SOURCE: Use ONLY information from the uploaded legal document's retrieved context ...
2. NO FABRICATION: ...
"""
```

### 2.5.5 Citation Parsing

`_CITATION_STRUCT` regex in `document_ingestion_pipeline.py` extracts year, reporter (NLR/SLR/SLLR/CLR), and page fields where patterns match—supporting structured tables in the UI and future **citation graph** analytics.

---

## 2.6 Frontend and Backend Interaction

The React app (CRA per `react-scripts` in `package.json`) uses **axios** for HTTP and **react-dropzone** for uploads. Typical flow:

1. User selects an NLR/SLR PDF.  
2. Frontend `POST`s multipart form data to `/api/documents/upload-sri-lanka`.  
3. Backend saves file, runs `run_ingestion_pipeline`, returns JSON with `document_id` and pipeline stage telemetry.  
4. Frontend requests summaries via `/api/analysis/...` or RAG endpoints under `/api/rag/...` using `document_id`.  
5. Optional: `react-pdf` renders preview; **jsPDF/html2canvas** may export reports.

**CORS** in `main.py` enumerates localhost ports and deployed hosts (e.g., `lawknow.vercel.app`), illustrating **environment-specific** configuration.

**[Insert Screenshot of Frontend UI Here]**  

---

## 2.7 Commercialization Aspects

Potential **value propositions** include: (1) **SaaS** for law firms with private deployment; (2) **institutional licenses** for universities; (3) **API metering** for newsrooms; (4) **pro bono** tiers for NGOs with audit logs.

**Go-to-market considerations:** legal disclaimers, **terms of use**, supervision by qualified attorneys, **data residency**, and **liability** caps. The prototype should be framed as **decision support**, not autonomous legal advice.

**Monetization blockers:** API costs (Gemini), compute for embeddings, storage for judgments, and **expert validation** costs. A credible roadmap phases **human evaluation** before paid launch.

---

## 2.8 Testing and Implementation

### 2.8.1 Automated and Script-Based Testing

The backend contains multiple `test_*.py` modules exercising imports, NER APIs, brief generation, and RAG responses. Celery (`celery_app.py`) may offload long tasks in production configurations.

### 2.8.2 Deployment Notes

`main.py` CORS entries reference a public IP and custom domains, implying **cloud deployment** during the project. Document the **actual** stack you used (e.g., Ubuntu VM + systemd + Uvicorn, or Docker if applicable).

### 2.8.3 Observability and Failure Modes

Pipeline `result["stages_failed"]` and `warnings` arrays surface partial failures (NER unavailable, LLM skipped). This transparency is methodologically important: **legal AI** should expose **provenance and degradation** honestly.

**Table 2.2 Pipeline stages and typical artefacts persisted** (from `document_ingestion_pipeline.py` docstring)

| Stage | Description | Typical artefact |
|------|-------------|------------------|
| 1 | Extract text (pdfplumber → OCR fallback) | Text passed to validation and save |
| 2 | Validate Sri Lankan legal document | Reject non-NLR/SLR; no persist if fail |
| 3 | Clean text + metadata (year, case number, court) | `LegalDocument` fields |
| 4 | Document structure analysis (hybrid classifier if available) | Structure stats / classifier output |
| 5 | Save `LegalDocument` | DB row |
| 6 | NER | `LegalEntity` rows |
| 7 | Fundamental rights detection | Detected rights records |
| 8 | Citation extraction | `SLCitation` + parsed year/reporter/page |
| 9 | Structure classification on paragraphs | Section types for chunks |
| 10 | `LegalChunker` chunking | Chunk objects |
| 11 | BGE embeddings | Vectors per chunk |
| 12 | Save `DocumentChunk` | DB rows with embeddings |
| 13 | FAISS index update | `faiss_chunks_v2.bin`, `faiss_chunks_v2_meta.json` |
| 14 | Elasticsearch (if available) | Optional index |
| 15 | LLM executive + detailed summaries | Columns on `LegalDocument` |
| 16 | Constitutional RAG analysis | Analysis text / related persist |
| 17 | Case similarity / precedent placeholder | As per pipeline implementation |

### 2.8.4 Document Validation Methodology (Empirical Design)

`DocumentProcessor.is_sri_lanka_legal_document` implements a **layered scorer** rather than a single brittle regex. Filename fast-paths accept many authentic PDFs extracted from volumes whose body text may not repeat “NLR/SLR” in the first pages. Conversely, **non-original** indicators reject filenames containing `_analysis`, `_summary`, or `_brief`. A **text-start heuristic** rejects documents whose opening paragraphs match “case analysis” style language unless strong judicial cues appear early.

This design is methodologically interesting because it encodes **domain priors** explicitly—something end-to-end classifiers can learn only with labelled data. The trade-off is **false negatives** (rare judgments with unusual filenames) and **false positives** (sophisticated forgeries). Mitigations include raising thresholds, adding manual review queues, and logging rejection reasons for error analysis.

### 2.8.5 Asynchronous Ingestion via RAG Jobs

`rag_v2_routes.py` defines `_run_full_ingestion`, which opens a fresh SQLAlchemy session, updates a `RAGJob` row (`status`, `progress`, `current_stage`, `document_id`, `chunk_count`, `message`), and runs `run_ingestion_pipeline` identically to the synchronous document router path. This pattern supports **responsive APIs**: the client receives a job identifier quickly while heavy stages continue server-side.

Methodologically, background ingestion introduces **consistency** questions: the user may query summaries before completion unless the UI gates on job status. The dissertation should describe the **actual UI behaviour** implemented in your React branch (polling vs websockets).

### 2.8.6 Hybrid Document Classifier Integration

When `HybridDocumentClassifier` imports successfully, `DocumentProcessor` attaches richer **structure_analysis** statistics (paragraph counts, section distributions). When PyTorch DLL issues occur on Windows hosts, the classifier gracefully disables, demonstrating **defensive integration** appropriate for student laptops and lab machines.

### 2.8.7 OCR Stack and Operational Dependencies

OCR fallback chains `pdf2image` → PIL images → `pytesseract`. This introduces **system dependencies** (Poppler/Tesseract binaries) that must be documented in appendices for reproducibility. Methodologically, OCR is both a **saviour** for scanned volumes and a **noise amplifier**; evaluation should stratify results by `extraction_quality` flags emitted by the pipeline.

---

# CHAPTER 3: RESULTS AND DISCUSSION

## 3.1 Results

### 3.1.1 Functional Outcomes

The integrated system successfully demonstrates: **PDF upload**; **validation**; **persistence** of `LegalDocument` rows; **chunk creation**; **FAISS indexing**; **retrieval** endpoints; and **summary generation** under varied LLM availability scenarios.

**Table 3.2 Comparison of summarization paths (characteristics from implementation; add your own timing/ROUGE columns after experiments)**

| Path | Code location | Grounded in explicit retrieved chunks? | Notes |
|------|---------------|----------------------------------------|--------|
| TF–IDF extractive | `NLPAnalyzer.extractive_summary` | N/A (selects source sentences) | Fast baseline; sentences always from source |
| BART | `bart_summarizer.py` / `summary_routes` | No | Full-span summarization; optional fallback |
| FLAN-T5 | `LLMGenerationService` when no API key / on failure | Prompt-limited to provided context | Local; CPU/GPU dependent |
| Gemini + RAG | `LLMGenerationService` + `RAGServiceV2` retrieval | Yes (design intent) | Requires `OPENAI_API_KEY`; network latency |

*Evidence:* Screenshot `GET /api/analysis/llm-status` and append timing table once you measure three runs per path on the same `document_id`.

### 3.1.2 Qualitative Metrics

Because legal adequacy is not captured by n-gram overlap alone, evaluate along dimensions adapted from legal informatics literature:

**Table 3.1 Qualitative evaluation dimensions for legal summaries**

| # | Dimension | Question / check | Suggested evidence |
|---|-----------|------------------|-------------------|
| 1 | Fidelity | Are parties, dates, and orders consistent with the judgment? | PDF excerpt + summary side-by-side |
| 2 | Coverage | Are facts, issues, reasoning, and disposition represented if present in source? | Checklist per case |
| 3 | Neutrality | Is tone non-partisan (no advocacy)? | Screenshot of output paragraph |
| 4 | Citations | Are SLR/NLR references preserved verbatim where shown? | Highlight in PDF and in summary |
| 5 | Abstention | Does output say “not stated” or omit when chunks lack the fact? | Screenshot of a thin-context case |
| 6 | Pipeline transparency | Does the upload response list `stages_completed` / `warnings`? | Network tab JSON |

### 3.1.3 Representative Outputs

Include **anonymized** excerpts of **executive** vs **detailed** summaries for one Supreme Court case and one Court of Appeal case, with **paragraph-level citations** back to chunk indices if available.

**[Figure 3.1: Example JSON response showing pipeline stages]**  

---

## 3.2 Research Findings

1. **Grounding prompts materially affect behaviour**—models still err under ambiguous retrieval; MMR and chunk size tuning matter.  
2. **PDF quality dominates** downstream quality; OCR introduces noise that misleads both NER and retrieval.  
3. **Validation gates** reduce garbage-in from non-original PDFs and should be retained in any production system.  
4. **API-first design** accelerates iteration: multiple clients (web, scripts) share one ingestion contract.

---

## 3.3 Discussion

### 3.3.1 Threats to Validity

- **Construct validity:** Proxy metrics may not reflect lawyer satisfaction.  
- **External validity:** Findings on a subset of judgments may not generalize across decades of formatting changes.  
- **Conclusion validity:** Without inter-annotator agreement, qualitative claims remain tentative.

### 3.3.2 Ethics

Misinterpretation can harm litigants or distort journalism. The system must display **prominent disclaimers**, **source links**, and **chunk provenance** where feasible.

### 3.3.3 Future Work

Fine-tune summarizers on **Sri Lankan parallel** summary data; add **Sinhala/Tamil** pipelines; integrate **court-approved** APIs; build **human review** workflows.

---

## 3.4 Summary of Each Student’s Contribution

**(If solo, replace with a short statement that the dissertation is an individual submission and delete subsections.)**

**Student A — [Name, ID]:** Backend ingestion, FAISS RAG, embedding service integration, deployment.  
**Student B — [Name, ID]:** Frontend React UI, axios client, state management, UX testing.  
**Student C — [Name, ID]:** NER data annotation batches, Colab corpus notebooks, evaluation scripts.  
**Student D — [Name, ID]:** Constitutional RAG experiments, documentation, literature survey chapters.

**Adjust to match your true division of labour and obtain sign-off from all members.**

---

# CHAPTER 4: CONCLUSION

This dissertation presented an **integrated architecture** for **AI-assisted summarization** of **Sri Lankan NLR/SLR** judgments, grounded in a **validated ingestion pipeline**, **structure-aware chunking**, **BGE embeddings**, **FAISS retrieval**, and **LLM-based generation** with explicit **fidelity constraints** and **local fallbacks**. Colab-centric corpus tooling addresses **scale**, while FastAPI and React deliver a **deployable** demonstrator.

The work reaffirms that **accessibility gains** must be paired with **humility about error modes**: OCR noise, retrieval misses, and residual hallucination risk remain open problems. Responsible next steps are **expert evaluation**, **dataset expansion**, and **policy alignment** with Sri Lanka’s legal information ecosystem.

The project advances a **practical middle path** between brittle extractive-only tools and unconstrained abstractive chatbots: **retrieval-grounded summarization with provenance-first UX.**

---

# REFERENCES

**(Use APA 7th or IEEE as required by your department; examples below in APA 7th)**

Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *Proceedings of NAACL-HLT 2019*, 4171–4186.

Lewis, M., Liu, Y., Goyal, N., Ghazvininejad, M., Mohamed, A., Levy, O., Stoyanov, V., & Zettlemoyer, L. (2020). BART: Denoising sequence-to-sequence pre-training for natural language generation, translation, and comprehension. *Proceedings of ACL 2020*, 7871–7880.

Gao, L., Ma, X., Lin, J., & Callan, J. (2022). Precise zero-shot dense retrieval without relevance labels. *Proceedings of ACL 2022*, 1762–1777. (Context: BGE-style dense retrieval practices.)

Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data*, 7(3), 535–547.

Ramírez, R., et al. (2024). *FastAPI* [Computer software]. https://fastapi.tiangolo.com/

Facebook Research. (2024). *FAISS: A library for efficient similarity search* [Computer software]. https://github.com/facebookresearch/faiss

Sri Lanka Institute of Information Technology. (n.d.). *Guidelines on documentation and submission of dissertations* [Institutional guideline].

**Add:** Sri Lankan Constitution (as cited legally), leading SLR/NLR manuals, NLP survey papers you used, and any **Gemini / Google AI** documentation URLs.

---

# GLOSSARY

**Abstractive summarization:** Generating new sentences paraphrasing the source.  
**Chunk:** A contiguous text span used as a retrieval unit.  
**Cosine similarity:** Measure of orientation between two vectors, often used for semantic nearness.  
**Extractive summarization:** Selecting existing sentences from the source.  
**Grounding:** Conditioning outputs on explicit retrieved passages.  
**Hallucination:** Fluent but factually unsupported generated content.  
**RAG:** Retrieval-Augmented Generation.

---

# APPENDICES

**Appendix A:** Ethics checklist and user disclaimer text (screenshot).  
**Appendix B:** Sample API request/response (`upload-sri-lanka`).  
**Appendix C:** Database ER diagram (ORM models).  
**Appendix D:** Colab notebook export (PDF) — `Build_Corpus_Colab.ipynb`.  
**Appendix E:** Selected `pytest` logs or `curl` transcripts.  
**Appendix F:** Glossary JSON excerpt from `data/sri_lanka_legal_corpus/legal_glossary_si_en_ta.json` (small sample only).

**End of dissertation draft body — expand each subsection with additional paragraphs, figures, and tables to reach 50+ A4 pages in Word.**
