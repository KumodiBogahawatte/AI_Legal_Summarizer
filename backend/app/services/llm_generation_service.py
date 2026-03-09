"""
llm_generation_service.py
Grounded text generation for the RAG pipeline.

Strategy:
- Default: google/flan-t5-base (free, local, no API key needed)
- Fallback to OpenAI gpt-3.5-turbo if OPENAI_API_KEY is set in .env

ALL outputs are grounded strictly in retrieved chunks.
Prompts instruct the model: "If not in context, say 'Not found in retrieved sections.'"
"""

import os
import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# ─── Prompt Templates ─────────────────────────────────────────────────────────

BASE_SYSTEM = """You are a Master Legal Research Assistant specializing in Sri Lankan Superior Court Judgments (NLR/SLR/SLLR).
Your target audience includes law students, legal researchers, and legal professionals. Your output must be highly accurate, neutral, well-structured, and strictly professional.

STRICT OPERATIONAL RULES:
1. DATA SOURCE: Use ONLY information from the uploaded legal document's retrieved context. The executive summary must be 100% accurate and grounded in this context — no external knowledge or inference beyond what is stated.
2. NO FABRICATION: Do not generate fictional facts, parties, dates, legal principles, or outcomes. Do not invent laws, precedents, or external facts. Every factual claim must appear in the provided context.
3. ACCURACY & NEUTRALITY: Maintain strict legal accuracy and absolute neutrality. Do not include personal opinions or biases.
4. MISSING INFORMATION: If the context does not state something (e.g. parties, issue, decision), say "Not stated in the judgment" or omit that part. Never fill gaps with invented content.
5. TERMINOLOGY: Use formal Sri Lankan legal terminology. Preserve citations and case names exactly as in the context.
6. STRUCTURE: Follow the requested format exactly. Ensure the output is well-structured and highly readable.
"""

EXECUTIVE_PROMPT = """{system}

Retrieved Context (legal document excerpts — this is the ONLY source of truth):
---
{context}
---

Case Metadata: Court: {court} | Year: {year} | Case: {case_name}

Task: Write a 150-word executive summary of this case in plain English. Include:
1. The parties involved and core dispute (only if stated in the context)
2. The main legal issue (only if stated in the context)
3. The court's final decision (only if stated in the context)

STRICT ACCURACY RULES:
- Use ONLY information that appears verbatim or is directly inferable from the retrieved context above. Do not add any fact, name, citation, or outcome that is not in the context.
- If the context does not state the parties, the issue, or the decision, say "Not stated in the judgment" for that part. Do not invent or assume.
- Preserve citations and court names exactly as in the context. Keep the summary accessible to non-lawyers but 100% faithful to the document.

Summary:"""

DETAILED_PROMPT = """{system}

Retrieved Context (legal document excerpts):
---
{context}
---

Case Metadata: Court: {court} | Year: {year} | Case: {case_name}

Task: Write a detailed 700-word analysis of this case with these sections:
**Facts:** (what happened)
**Legal Issues:** (questions the court had to decide)
**Legal Analysis:** (statutes, precedents cited)
**Judicial Reasoning:** (how the court reasoned)
**Decision:** (what the court held and ordered)

Use only the retrieved context. Preserve all case citations exactly.

Analysis:"""

CONSTITUTIONAL_PROMPT = """{system}

Retrieved Context (legal document excerpts):
---
{context}
---

Retrieved Constitutional Articles matched:
---
{articles}
---

Task: Analyse the constitutional rights dimension of this case.

Write your answer as a short, structured note with the following numbered headings (no bold or other markdown formatting):
1. Engaged constitutional rights – list the specific Articles (by number and title) that are clearly engaged by the case.
2. Court's interpretation and application – explain how the court interpreted or applied those rights, grounded strictly in the context.
3. Violation and remedy – state clearly whether a violation was found, and what remedy (if any) was granted (e.g. dismissed, compensation, writs, declaratory relief).
4. Significance for Sri Lankan constitutional law – briefly explain why this case matters (or state that its broader significance is not clearly articulated in the judgment).

Do NOT include any introductory sentences like \"Based on the retrieved context...\" or closing summaries. Start directly with the numbered headings above, exactly as written.
If no constitutional issue is mentioned in the context, clearly state that under heading 1 and keep the remaining sections very brief.

Analysis:"""

PRECEDENT_COMPARISON_PROMPT = """{system}

Source Case Context:
---
{source_context}
---

Precedent Case Context:
---
{precedent_context}
---

Task: Compare these two Sri Lankan legal cases:
1. **Factual Similarity**: How similar are the facts?
2. **Legal Issues**: Do they address the same legal questions?
3. **Judicial Reasoning**: Do the courts reason in the same way?
4. **Outcome**: Were the decisions consistent?
5. **Relationship**: Does one case follow, distinguish, or depart from the other?

Use only the provided contexts. Do not infer beyond what is stated.

Comparison:"""

QA_PROMPT = """{system}

Retrieved Context from the case:
---
{context}
---

User Question: {question}

Answer the question using ONLY the retrieved context above.
If the answer is not in the context, say: "This information is not available in the retrieved case sections."

Answer:"""


class LLMGenerationService:
    """
    Grounded text generation for legal RAG outputs.
    Uses FLAN-T5 locally or OpenAI if API key is available.
    """

    def __init__(self):
        self._pipeline = None
        self._openai_client = None
        self._mode = None
        self._last_full_analysis = {}
        self._last_doc_id = None
        self._bart_summarizer = None  # Lazy-loaded when Gemini fails
        self._init_model()

    def _init_model(self):
        """Initialize the LLM — OpenAI/Gemini if key(s) present, else FLAN-T5."""
        raw = os.getenv("OPENAI_API_KEY", "").strip()
        # Support multiple keys: comma-separated (e.g. key1,key2,key3) for rotation on 429
        self._api_keys = [k.strip() for k in raw.split(",") if k.strip() and k.strip() != "your-openai-key-here"]
        self._key_index = 0

        if self._api_keys:
            try:
                from openai import OpenAI
                self._openai_client = self._make_openai_client(self._api_keys[0])
                self._mode = "openai"
                print(f"DEBUG: LLM mode: {self._mode}, API Key(s) present: {len(self._api_keys)}")
                logger.info("✅ LLMGenerationService: Using Gemini API (OpenAI compatibility)")
                return
            except Exception as e:
                print(f"DEBUG: OpenAI init failed: {e}")
                logger.warning(f"OpenAI init failed: {e}. Falling back to local FLAN-T5.")

        # Local FLAN-T5 — only initialize eagerly when no OpenAI key.
        # When OpenAI/Gemini is configured but fails at runtime (429/503, etc.),
        # we lazily load FLAN-T5 as a fallback in _generate().
        try:
            from transformers import T5ForConditionalGeneration, T5Tokenizer
            self._tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
            self._flan_model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")
            self._flan_model.eval()
            self._pipeline = None  # Not used
            self._mode = "flan-t5"
            logger.info("✅ LLMGenerationService: Using google/flan-t5-base (local, direct API)")
        except Exception as e:
            logger.error(f"Failed to load FLAN-T5: {e}. Generation will return context summary.")
            self._mode = "extractive_fallback"

    def _ensure_flan_backend(self) -> bool:
        """
        Lazy-initialize FLAN-T5 backend when OpenAI/Gemini returns quota/availability
        errors. Returns True if FLAN is ready to use.
        """
        # Already loaded
        if getattr(self, "_flan_model", None) is not None and getattr(self, "_tokenizer", None) is not None:
            return True
        try:
            from transformers import T5ForConditionalGeneration, T5Tokenizer
            self._tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
            self._flan_model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")
            self._flan_model.eval()
            logger.info("✅ LLMGenerationService: Switched to google/flan-t5-base after OpenAI/Gemini error")
            return True
        except Exception as e:
            logger.error(f"Failed to load FLAN-T5 fallback: {e}")
            with open("llm_errors.log", "a", encoding="utf-8") as f:
                f.write(f"ERROR loading FLAN-T5 fallback: {e}\n")
            return False

    def _make_openai_client(self, api_key: str):
        """Create OpenAI client for Gemini (OpenAI-compatible endpoint)."""
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    def _try_next_key(self) -> bool:
        """On 429, switch to next API key if multiple are configured. Returns True if switched."""
        if not getattr(self, "_api_keys", None) or len(self._api_keys) <= 1:
            return False
        self._key_index = (self._key_index + 1) % len(self._api_keys)
        key = self._api_keys[self._key_index]
        try:
            self._openai_client = self._make_openai_client(key)
            logger.info(f"Rotated to next Gemini API key (index {self._key_index + 1}/{len(self._api_keys)})")
            return True
        except Exception as e:
            logger.warning(f"Next API key failed to init: {e}")
            return False

    # ─── Internal Generation ──────────────────────────────────────────────────

    def _generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Route to the appropriate generation backend."""
        print(f"DEBUG: _generate called with mode={self._mode}")
        try:
            if self._mode == "openai":
                model_name = "gemini-flash-latest"
                response = self._openai_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3,
                )
                result = response.choices[0].message.content.strip()
                return result
            elif self._mode == "flan-t5":
                # Use T5 model directly — truncate to 512 tokens max
                inputs = self._tokenizer(
                    prompt,
                    return_tensors="pt",
                    max_length=512,
                    truncation=True,
                )
                outputs = self._flan_model.generate(
                    **inputs,
                    max_new_tokens=min(max_tokens, 512),
                    num_beams=2,
                    early_stopping=True,
                )
                return self._tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

            else:
                # Extractive fallback — return first 150 words of the context
                return self._extractive_fallback(prompt)
        except Exception as e:
            err_str = str(e)
            is_quota = "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str
            is_invalid_key = "API key expired" in err_str or "API_KEY_INVALID" in err_str or (
                "400" in err_str and ("invalid" in err_str.lower() or "API key" in err_str)
            )
            if is_quota and self._mode == "openai" and self._try_next_key():
                # Retry once with next key
                try:
                    response = self._openai_client.chat.completions.create(
                        model="gemini-flash-latest",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.3,
                    )
                    return response.choices[0].message.content.strip()
                except Exception as retry_e:
                    logger.warning(f"Retry with next key failed: {retry_e}")
                    err_str = str(retry_e)
                    is_quota = "429" in err_str or "quota" in err_str.lower()
            if is_quota:
                logger.warning("LLM quota exceeded (429); returning user-friendly message without FLAN fallback.")
            elif is_invalid_key:
                logger.warning("LLM API key expired or invalid; returning user-friendly message.")
            else:
                logger.error(f"LLM generation error: {e}")
            with open("llm_errors.log", "a", encoding="utf-8") as f:
                f.write(f"ERROR in _generate: {e}\n")
            if is_quota:
                return (
                    "Constitutional analysis is temporarily unavailable due to high demand. "
                    "Please try again in a few minutes. The matched provisions and fundamental rights above are still available."
                )
            if is_invalid_key:
                return (
                    "API key expired or invalid. Create a new key at Google AI Studio and set OPENAI_API_KEY in backend/.env, then restart the backend. "
                    "The matched provisions and fundamental rights above are still available."
                )
            # For other errors, try FLAN-T5 fallback only if available (avoids SentencePiece noise when not installed)
            if self._mode == "openai":
                if self._ensure_flan_backend():
                    self._mode = "flan-t5"
                    try:
                        inputs = self._tokenizer(
                            prompt,
                            return_tensors="pt",
                            max_length=512,
                            truncation=True,
                        )
                        outputs = self._flan_model.generate(
                            **inputs,
                            max_new_tokens=min(max_tokens, 512),
                            num_beams=2,
                            early_stopping=True,
                        )
                        return self._tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
                    except Exception as flan_err:
                        logger.error(f"FLAN-T5 fallback generation error: {flan_err}")
                        with open("llm_errors.log", "a", encoding="utf-8") as f:
                            f.write(f"ERROR in FLAN-T5 fallback: {flan_err}\n")
            return "Analysis could not be generated at this time. Please try again later."

    def _extractive_fallback(self, prompt: str) -> str:
        """
        When no LLM is available, extract a coherent summary from the raw context blocks.
        NEVER returns prompt template text — only actual case content.
        """
        # Context blocks are between --- markers in the prompt.
        # Extract all text between --- ... --- and take the first 200 words.
        blocks = re.findall(r'---\s*\n(.+?)\n---', prompt, re.DOTALL)
        if blocks:
            # Filter out blocks that look like metadata (< 40 chars per line on average)
            content_blocks = [b.strip() for b in blocks if len(b.strip()) > 100]
            if content_blocks:
                combined = "\n".join(content_blocks)
                # Strip section headers like [FACTS - Chunk 1]
                combined = re.sub(r'\[[A-Z_]+ - Chunk \d+\]', '', combined)
                words = combined.split()
                return " ".join(words[:200])
        # Last resort: find anything after a colon/newline in the prompt that looks like case text
        lines = [l.strip() for l in prompt.splitlines() if len(l.strip()) > 80
                 and not l.strip().startswith('You are')
                 and not l.strip().startswith('-')
                 and not l.strip().startswith('STRICT')
                 and not l.strip().startswith('Task:')]
        if lines:
            return " ".join(" ".join(lines[:3]).split()[:150])
        return "Insufficient context retrieved to generate an answer. Please ensure the document has been processed."

    def _extractive_fallback_from_text(self, text: str, max_words: int = 150) -> str:
        """Produce a short summary from raw document text (no prompt). 100% grounded."""
        if not text or len(text.strip()) < 100:
            return "Insufficient document text to generate a summary."
        cleaned = re.sub(r'\s+', ' ', text.strip())
        words = cleaned.split()
        return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

    def _build_context(self, chunks: List[Dict], max_chars: int = 3000) -> str:
        """Combine chunks into a single context string, respecting token limits."""
        parts = []
        total = 0
        for i, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            section = chunk.get("section_type", "OTHER")
            header = f"[{section} - Chunk {i+1}]"
            entry = f"{header}\n{text}\n"
            if total + len(entry) > max_chars:
                break
            parts.append(entry)
            total += len(entry)
        return "\n---\n".join(parts)

    def _is_bad_executive_result(self, text: str) -> bool:
        """True if the executive summary result is a failure or unusable."""
        if not text or not str(text).strip():
            return True
        t = str(text).strip()
        if t.startswith("Generation failed:") or t.startswith("Insufficient context"):
            return True
        if len(t.split()) < 20:
            return True
        return False

    def _get_bart_summarizer(self):
        """Lazy-load BART summarizer (free, local). Returns None if unavailable."""
        if self._bart_summarizer is not None:
            return self._bart_summarizer
        try:
            from .bart_summarizer import BARTLegalSummarizer
            self._bart_summarizer = BARTLegalSummarizer()
            logger.info("BART summarizer loaded for executive summary fallback.")
            return self._bart_summarizer
        except Exception as e:
            logger.warning(f"BART summarizer not available: {e}")
            return None

    def _try_bart_executive_summary(self, chunks: List[Dict], max_chars: int = 4000) -> Optional[str]:
        """
        Generate executive summary using BART (free, extractive-style) from chunk text.
        Used when Gemini/API is unavailable. Result is 100% grounded in the provided text.
        Returns None if BART fails or chunks are empty.
        """
        if not chunks:
            return None
        combined = self._build_context(chunks, max_chars=max_chars)
        # Strip chunk headers so BART sees plain text
        combined = re.sub(r'\[[A-Z_]+ - Chunk \d+\]\n?', '', combined)
        if len(combined.strip()) < 200:
            return None
        bart = self._get_bart_summarizer()
        if not bart:
            return None
        try:
            # BART pipeline uses token limits; 150 words ≈ 200 tokens
            summary = bart.summarize_legal_document(
                combined,
                max_length=150,
                min_length=80,
            )
            if summary and len(summary.split()) >= 30:
                return summary.strip()
        except Exception as e:
            logger.warning(f"BART executive summary failed: {e}")
        return None

    def _parse_json_safely(self, text: str) -> Dict:
        """Try to extract and parse JSON from LLM response, with regex fallbacks."""
        import json
        if not (text and isinstance(text, str)):
            return {}
        # Don't try to parse user-facing error messages
        if any(
            phrase in text
            for phrase in (
                "Constitutional analysis is temporarily unavailable",
                "API key expired or invalid",
                "Please try again in a few minutes",
                "Please try again later.",
            )
        ):
            return {}
        raw = text.strip()
        # Strip markdown code fences (```json ... ``` or ``` ... ```)
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                obj = json.loads(match.group(0))
                return self._normalize_analysis_keys(obj)
            return self._normalize_analysis_keys(json.loads(raw))
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}. Attempting recovery.")
            recovered = self._recover_analysis_from_text(raw)
            return self._normalize_analysis_keys(recovered)

    def _normalize_analysis_keys(self, obj: Dict) -> Dict:
        """Map common LLM key variants to canonical keys."""
        if not obj or not isinstance(obj, dict):
            return obj or {}
        key_map = {
            "executive_summary": ["executive_summary", "executiveSummary", "Executive Summary", "executive summary"],
            "detailed_summary": ["detailed_summary", "detailedSummary", "Detailed Summary", "detailed summary"],
            "section_summaries": ["section_summaries", "sectionSummaries", "Section Summaries", "section summaries"],
            "legal_terms_glossary": ["legal_terms_glossary", "legalTermsGlossary", "legal_terms", "glossary"],
        }
        out = {}
        for canonical, aliases in key_map.items():
            for alias in aliases:
                if alias in obj and obj[alias] is not None:
                    out[canonical] = obj[alias]
                    break
            if canonical not in out:
                out.setdefault(canonical, {} if canonical in ("detailed_summary", "section_summaries", "legal_terms_glossary") else "")
        for k, v in obj.items():
            if k not in out and not k.startswith("_"):
                out[k] = v
        return out

    def _recover_analysis_from_text(self, text: str) -> Dict:
        """Extract executive_summary and optional detailed_summary from broken JSON."""
        import json
        recovered = {}
        # Executive summary: allow multiline quoted value
        for key in ["executive_summary", "Executive Summary", "executiveSummary"]:
            m = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
            if m:
                recovered["executive_summary"] = m.group(1).replace("\\n", "\n").replace('\\"', '"').strip()
                break
        if "executive_summary" not in recovered:
            m = re.search(r'"executive_summary"\s*:\s*"([^"]+)"', text)
            if m:
                recovered["executive_summary"] = m.group(1).strip()
        # Detailed summary: nested object - look for "detailed_summary": { ... }
        ds_match = re.search(r'"detailed_summary"\s*:\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})', text, re.DOTALL)
        if ds_match:
            try:
                recovered["detailed_summary"] = json.loads(ds_match.group(1))
            except Exception:
                recovered["detailed_summary"] = {}
        else:
            for key in ["facts", "legal_issues", "decision"]:
                m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
                if m:
                    recovered.setdefault("detailed_summary", {})[key] = m.group(1).replace("\\n", "\n").replace('\\"', '"').strip()
        return recovered

    # ─── Public API ───────────────────────────────────────────────────────────

    def generate_full_analysis(self, doc_id: int, text: str, metadata: Dict) -> Dict:
        """
        Master call that generates EVERYTHING in one LLM pass.

        Returns a structured dictionary with the following canonical schema
        (keys may be empty when using fallback modes, but they are always present
        when _source == \"llm\"):

        {
          \"executive_summary\": str,
          \"detailed_summary\": {
            \"facts\": str,
            \"procedural_posture\": str,
            \"arguments\": {
              \"petitioner\": str,
              \"respondent\": str,
            },
            \"courts_analysis\": str,
            \"decision\": str,
          },
          \"legal_terms_glossary\": {
            <term>: {\"simplified\": str, \"occurrences\": int}
          },
          \"section_summaries\": {
            \"Case Identification\": str,
            \"Statutory Provisions\": str,
            \"Legal Issue\": str,
            \"Facts\": str,
            \"Procedural History\": str,
            \"Arguments\": str,
            \"Court’s Reasoning\": str,
            \"Decision / Holding\": str,
            \"Rule of Law\": str,
            \"Key Takeaways\": str,
          },
          \"_source\": \"llm\" | \"flan_t5\" | \"regex_fallback\"
        }
        """
        # Return cached analysis only when it's from the LLM/flan — never reuse fallback so that
        # after the API becomes available, a refetch will call the LLM again instead of serving old fallback.
        if self._last_doc_id == doc_id and self._last_full_analysis:
            src = self._last_full_analysis.get("_source") or ""
            if src in ("llm", "flan_t5"):
                return self._last_full_analysis

        if self._mode not in ("openai", "google_genai"):
            # Use FLAN-T5 for executive summary only (no JSON); rest will be extractive in the route
            if self._mode == "flan-t5" and getattr(self, "_flan_model", None) is not None:
                if len(text) > 4000:
                    context = text[:3000] + "\n\n[...]\n\n" + text[-1000:]
                else:
                    context = text
                prompt = f"""Summarize this Sri Lankan court case in about 150 words. Include: parties, main legal issue, and the court's decision. Use only the text below.

{context}

Summary:"""
                exec_text = self._generate(prompt, max_tokens=250)
                if exec_text and not exec_text.startswith("Generation failed:"):
                    result = {
                        "executive_summary": exec_text.strip(),
                        "detailed_summary": {},
                        "section_summaries": {},
                        "_source": "flan_t5",
                    }
                    self._last_full_analysis = result
                    self._last_doc_id = doc_id
                    return result
            logger.warning(f"RAG: LLM mode '{self._mode}' does not support full analysis pass.")
            return {"_source": "regex_fallback"}

        # Send enough context so summaries are accurate; avoid dropping key facts/decision in the middle.
        # Use first 10k + last 6k chars when doc is long (was 8k+4k) so less content is omitted.
        if len(text) > 16000:
            context = text[:10000] + "\n\n[... OMITTED INTERMEDIATE TEXT ...]\n\n" + text[-6000:]
        elif len(text) > 12000:
            context = text[:9000] + "\n\n[... OMITTED INTERMEDIATE TEXT ...]\n\n" + text[-5000:]
        else:
            context = text
        
        prompt = f"""{BASE_SYSTEM}
Task: Perform a deep legal analysis of this Sri Lankan Superior Court judgment.
Respond ONLY with a valid JSON object.

METADATA: {metadata}
CONTENT: {context}

CRITICAL: Use ONLY information from CONTENT. Identify the case name and party names (petitioner, respondent, appellant, etc.) from the CONTENT and use them exactly in your summary. Do not substitute or invent different names. If CONTENT is truncated (e.g. "[... OMITTED INTERMEDIATE TEXT ...]"), state only what appears in the parts you have.

JSON REQUIREMENTS:
- executive_summary MUST be 100% grounded in CONTENT above: only state facts, parties, issues, and decision that appear in the judgment. Do not add anything not in CONTENT. If something is not stated, say \"Not stated in the judgment\" for that part.
- Do not invent facts, party names, dates, or outcomes. For any element not clearly stated in CONTENT, use \"Not stated in the judgment\" for that field.
{{
  "executive_summary": "A 150-word high-level summary for a non-lawyer, using ONLY information from CONTENT.",
  "detailed_summary": {{
    "facts": "Chronological material facts of the case.",
    "procedural_posture": "Detailed history (Lower Court -> Court of Appeal -> Supreme Court).",
    "arguments": {{
        "petitioner": "Main legal arguments submitted by the appellant/petitioner.",
        "respondent": "Counter-arguments by the respondent/Attorney General."
    }},
    "courts_analysis": "Step-by-step analysis of the statutes and precedents applied by the judges.",
    "decision": "The final holding, the operative order, and whether the appeal was allowed or dismissed."
  }},
  "legal_terms_glossary": {{
    "TERM": {{"simplified": "Easy to understand explanation", "occurrences": 1}}
  }},
  "section_summaries": {{
    "Case Identification": "Include the case name, citation, court, judges, and year if available.",
    "Statutory Provisions": "List all statutes, legal sections, ordinances, or constitutional provisions referenced in the case.",
    "Legal Issue": "State ONLY the legal question(s) the court had to decide, in question form (e.g. 'Whether the Magistrate was required to acquit if in doubt'; 'Whether the accused breached section X'). Do NOT include facts, dates, quotes, or procedural narrative—only the issues.",
    "Facts": "Provide a concise summary of the key facts that led to the dispute.",
    "Procedural History": "Explain how the case reached the current court (for example: lower court decision, appeal, revision, etc.).",
    "Arguments": "Summarize the main arguments presented by the parties.",
    "Court’s Reasoning": "Explain the reasoning used by the judge(s), including interpretation of the law and evaluation of evidence.",
    "Decision / Holding": "State the court’s decision in response to the legal issues.",
    "Rule of Law": "Identify the legal principle or rule established by the case.",
    "Key Takeaways": "Provide short bullet points summarizing the significance of the case."
  }}
}}
"""
        response_text = self._generate(prompt, max_tokens=4000)
        
        # Detect failure in _generate (e.g. 429 Quota Exceeded)
        if response_text.startswith("Generation failed:"):
            logger.error(f"LLM failed for doc {doc_id}: {response_text}. Using fallback.")
            from .case_brief_generator import CaseBriefGenerator
            fallback = CaseBriefGenerator.generate_case_brief(text, metadata)
            # Prefer BART for executive summary when API failed (100% grounded in document)
            chunks_from_text = [{"text": text[:4000], "section_type": "OTHER"}]
            bart_exec = self._try_bart_executive_summary(chunks_from_text, max_chars=4000)
            if bart_exec:
                fallback["executive_summary"] = bart_exec
            elif fallback.get("executive_summary"):
                pass  # keep CaseBriefGenerator's
            else:
                fallback["executive_summary"] = self._extractive_fallback_from_text(text)
            return {**fallback, "_source": "regex_fallback"}

        analysis = self._parse_json_safely(response_text)
        exec_text = str(analysis.get("executive_summary") or "").strip() if isinstance(analysis, dict) else ""
        # If parsing failed or returned no usable executive summary, use fallback
        if not analysis or not exec_text or len(exec_text) < 30:
            logger.warning("LLM response parsing failed or no executive_summary. Using fallback.")
            from .case_brief_generator import CaseBriefGenerator
            fallback = CaseBriefGenerator.generate_case_brief(text, metadata)
            chunks_from_text = [{"text": text[:4000], "section_type": "OTHER"}]
            bart_exec = self._try_bart_executive_summary(chunks_from_text, max_chars=4000)
            if bart_exec:
                fallback["executive_summary"] = bart_exec
            elif not fallback.get("executive_summary"):
                fallback["executive_summary"] = self._extractive_fallback_from_text(text)
            return {**fallback, "_source": "regex_fallback"}

        # Ensure the master object has the canonical keys expected by callers
        analysis = analysis or {}
        analysis.setdefault("executive_summary", "")
        analysis.setdefault("detailed_summary", {})
        analysis.setdefault("legal_terms_glossary", {})
        analysis.setdefault("section_summaries", {})
        analysis["_source"] = "llm"
        
        # Cache results for this document
        self._last_full_analysis = analysis
        self._last_doc_id = doc_id
        
        return analysis

    def _normalize_case_brief_structure(self, brief: Dict, metadata: Dict | None = None) -> Dict:
        """
        Normalise case-brief output so both LLM-based and regex-based generators
        adhere to a single JSON contract expected by the API.

        Canonical case_brief schema:
          - case_identification: { case_name, court, year, citation }
          - executive_summary: str
          - facts: str
          - issues: List[str]
          - holding: str
          - reasoning: str
          - final_order: str
          - ratio_decidendi: List[str]
          - procedural_principles: {
                statutory_provisions: List[str],
                procedural_rules: List[str],
            }
          - area_of_law: str (optional, defaults to \"Civil / Constitutional\")
        """
        brief = dict(brief or {})

        # Case identification: prefer filename-derived case name (e.g. ALLIS v. SIGERA) to avoid LLM typos
        cid = brief.get("case_identification") or {}
        if metadata and metadata.get("file_name"):
            try:
                from .case_brief_generator import case_name_from_filename
                from_file = case_name_from_filename(metadata["file_name"])
                if from_file and "v." in from_file:
                    cid = {**cid, "case_name": from_file}
            except Exception:
                pass
        case_name = cid.get("case_name") or (metadata or {}).get("case_name") if metadata else None
        brief["case_identification"] = {
            "case_name": case_name or (metadata or {}).get("file_name", "N/A") if metadata else cid.get("case_name", "N/A"),
            "court": cid.get("court") or (metadata or {}).get("court", "N/A") if metadata else cid.get("court", "N/A"),
            "year": cid.get("year") or (str((metadata or {}).get("year")) if metadata and metadata.get("year") else "N/A"),
            "citation": cid.get("citation") or (metadata or {}).get("citation", "N/A") if metadata else cid.get("citation", "N/A"),
        }

        # Executive summary + core narrative fields
        brief.setdefault("executive_summary", "Summary not available.")
        brief.setdefault("facts", "Facts not available.")
        issues = brief.get("issues") or []
        brief["issues"] = issues if isinstance(issues, list) else [str(issues)]
        brief.setdefault("holding", "Holding/Decision: Not available.")
        brief.setdefault("reasoning", "Reasoning: Not available.")
        brief.setdefault("final_order", "Final Order: Not available.")

        ratio = brief.get("ratio_decidendi") or []
        brief["ratio_decidendi"] = ratio if isinstance(ratio, list) else [str(ratio)]

        # Procedural principles – normalise to dict with two lists
        proc = brief.get("procedural_principles")
        if isinstance(proc, dict):
            statutory = proc.get("statutory_provisions") or []
            rules = proc.get("procedural_rules") or []
            if not isinstance(statutory, list):
                statutory = [str(statutory)]
            if not isinstance(rules, list):
                rules = [str(rules)]
            proc_norm = {
                "statutory_provisions": statutory,
                "procedural_rules": rules,
            }
        else:
            # LLM path used a single-string or list summary; convert into procedural_rules
            if isinstance(proc, list):
                summary_text = "; ".join(str(x) for x in proc if x)
            elif isinstance(proc, str):
                summary_text = proc
            else:
                summary_text = ""
            proc_norm = {
                "statutory_provisions": [],
                "procedural_rules": [summary_text] if summary_text else [],
            }
        brief["procedural_principles"] = proc_norm

        # Area of law – optional but useful
        brief.setdefault("area_of_law", "Civil / Constitutional")

        return brief

    @staticmethod
    def _is_generic_or_weak_brief_value(field: str, value: Any) -> bool:
        """True if this LLM value is generic/placeholder and we should prefer regex."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return True
        s = (value if isinstance(value, str) else " ".join(str(x) for x in value) if isinstance(value, list) else str(value)).strip().lower()
        generic_phrases = [
            "not available",
            "not stated",
            "not identified",
            "not clearly stated",
            "please refer to the full",
            "review the full judgment",
            "review judgment",
            "cannot be determined",
            "could not be extracted",
            "the judgment does not provide",
            "no binding legal principles are expressly stated",
            "summary not available",
            "facts not available",
            "issues not identified",
            "decision not available",
            "reasoning not available",
            "order not available",
            "ratio not identified",
            "n/a",
        ]
        if any(p in s for p in generic_phrases):
            return True
        if field == "facts" and len(s) < 80:
            return True
        if field == "holding" and (len(s) < 40 or s.endswith("...")):
            return True
        if field == "reasoning" and len(s) < 60:
            return True
        return False

    @staticmethod
    def _merge_brief_with_regex(llm_brief: Dict, regex_brief: Dict, text: str) -> Dict:
        """
        Hybrid merge: use regex for any field where LLM is generic, empty, or contradicts the document.
        Ensures SLR/NLR uploads get accurate case briefs.
        """
        text_lower = text[-4000:].lower() if len(text) > 4000 else text.lower()
        merged = dict(llm_brief)

        def use_regex_if_weak(field: str, llm_val: Any, regex_val: Any) -> Any:
            if regex_val is None or (isinstance(regex_val, str) and not str(regex_val).strip()):
                return llm_val
            if LLMGenerationService._is_generic_or_weak_brief_value(field, llm_val):
                return regex_val
            # Validation: appeal outcome contradiction
            if field in ("holding", "final_order") and llm_val:
                llm_s = str(llm_val).lower()
                if "appeal allowed" in llm_s or "appeal granted" in llm_s:
                    if "dismissed" in text_lower or "dismissed the appeal" in text_lower:
                        return regex_val
                if "dismissed" in llm_s and "allowed" in text_lower and "appeal" in text_lower:
                    if "appeal allowed" in text_lower or "allow the appeal" in text_lower:
                        return regex_val
            return llm_val

        for key in ("facts", "holding", "reasoning", "final_order"):
            if key in regex_brief and key in merged:
                merged[key] = use_regex_if_weak(key, merged.get(key), regex_brief.get(key))

        if "issues" in regex_brief and isinstance(regex_brief["issues"], list) and regex_brief["issues"]:
            llm_issues = merged.get("issues") or []
            if isinstance(llm_issues, str):
                llm_issues = [llm_issues]
            if LLMGenerationService._is_generic_or_weak_brief_value("issues", llm_issues):
                merged["issues"] = regex_brief["issues"]
            elif not llm_issues or (len(llm_issues) == 1 and LLMGenerationService._is_generic_or_weak_brief_value("issues", llm_issues[0])):
                merged["issues"] = regex_brief["issues"]

        if "ratio_decidendi" in regex_brief and isinstance(regex_brief["ratio_decidendi"], list) and regex_brief["ratio_decidendi"]:
            llm_ratio = merged.get("ratio_decidendi") or []
            if isinstance(llm_ratio, str):
                llm_ratio = [llm_ratio]
            if LLMGenerationService._is_generic_or_weak_brief_value("ratio_decidendi", llm_ratio):
                merged["ratio_decidendi"] = regex_brief["ratio_decidendi"]
            elif not llm_ratio or all(LLMGenerationService._is_generic_or_weak_brief_value("ratio_decidendi", r) for r in llm_ratio):
                merged["ratio_decidendi"] = regex_brief["ratio_decidendi"]

        return merged

    def generate_case_brief(self, doc_id: int, text: str, metadata: Dict) -> Dict:
        """
        Generate a structured case brief (hybrid: LLM + regex merge).

        Always runs regex extraction. If LLM is available, uses LLM output but overrides
        any generic/empty or contradictory field with regex so SLR/NLR uploads get
        accurate briefs.
        """
        from .case_brief_generator import CaseBriefGenerator
        regex_brief = CaseBriefGenerator.generate_case_brief(text, metadata)
        # Try LLM path
        if self._last_doc_id != doc_id or not self._last_full_analysis:
            logger.info(f"Generating full analysis for brief (doc_id: {doc_id})")
            self.generate_full_analysis(doc_id, text, metadata)
            
        if self._last_full_analysis and self._mode in ("openai", "google_genai"):
            # Transform full analysis into brief format, then normalise schema
            fa = self._last_full_analysis
            ds = fa.get("detailed_summary", {})
            ss = fa.get("section_summaries", {})

            llm_brief = {
                "case_identification": {
                    "case_name": metadata.get("case_name") or metadata.get("file_name", "N/A"),
                    "court": metadata.get("court", "N/A"),
                    "year": metadata.get("year", "N/A"),
                    "citation": metadata.get("citation", "N/A"),
                },
                "executive_summary": fa.get("executive_summary", "Summary not available."),
                "facts": ds.get("facts") or ss.get("Facts", "Facts not available."),
                "issues": [ss.get("Legal Issue", ds.get("procedural_posture", "Issues not identified."))],
                "holding": ss.get("Decision / Holding", ds.get("decision", "Decision not available.")),
                "reasoning": ss.get("Court’s Reasoning", ds.get("courts_analysis", "Reasoning not available.")),
                "final_order": ds.get("decision", "Order not available."),
                "ratio_decidendi": [ss.get("Rule of Law", "Ratio not identified.")],
                "procedural_principles": [ds.get("procedural_posture", "N/A")],
            }
            merged = self._merge_brief_with_regex(llm_brief, regex_brief, text)
            return self._normalize_case_brief_structure(merged, metadata)
        
        # No LLM: use regex brief only
        return self._normalize_case_brief_structure(regex_brief, metadata)

    def generate_executive_summary(
        self,
        chunks: List[Dict],
        case_metadata: Optional[Dict] = None,
    ) -> str:
        """
        Generate a 150-word executive summary 100% grounded in retrieved chunks.

        Fallback order when Gemini/API is unavailable or fails:
        1. Gemini (or OpenAI-compatible) API
        2. BART (facebook/bart-large-cnn, free/local) — extractive-style, document-accurate
        3. FLAN-T5 (if API failed but FLAN was loaded)
        4. Extractive fallback (first N words from context)
        """
        meta = case_metadata or {}
        context = self._build_context(chunks, max_chars=2000)
        prompt = EXECUTIVE_PROMPT.format(
            system=BASE_SYSTEM,
            context=context,
            court=meta.get("court", "Unknown court"),
            year=meta.get("year", "Unknown year"),
            case_name=meta.get("case_name", "Unknown case"),
        )
        result = self._generate(prompt, max_tokens=250)
        if not self._is_bad_executive_result(result):
            return result
        # Gemini/FLAN failed or returned unusable text — try BART (free, accurate)
        bart_summary = self._try_bart_executive_summary(chunks, max_chars=4000)
        if bart_summary:
            logger.info("Executive summary produced by BART fallback.")
            return bart_summary
        # BART unavailable (e.g. no torch) — try extractive summarizer (100% grounded)
        try:
            from .advanced_summarizer import AdvancedLegalSummarizer
            combined = self._build_context(chunks, max_chars=5000)
            combined = re.sub(r'\[[A-Z_]+ - Chunk \d+\]\n?', '', combined)
            adv = AdvancedLegalSummarizer()
            out = adv.generate_executive_summary(combined.strip(), structured_content=None)
            if out and out.get("summary") and len(out["summary"].split()) >= 30:
                logger.info("Executive summary produced by extractive (AdvancedLegalSummarizer) fallback.")
                return out["summary"]
        except Exception as e:
            logger.warning(f"AdvancedLegalSummarizer fallback failed: {e}")
        return self._extractive_fallback(prompt)

    def generate_detailed_summary(
        self,
        chunks: List[Dict],
        case_metadata: Optional[Dict] = None,
    ) -> str:
        """Generate a ~700-word detailed structured summary."""
        meta = case_metadata or {}
        context = self._build_context(chunks, max_chars=3500)
        prompt = DETAILED_PROMPT.format(
            system=BASE_SYSTEM,
            context=context,
            court=meta.get("court", "Unknown court"),
            year=meta.get("year", "Unknown year"),
            case_name=meta.get("case_name", "Unknown case"),
        )
        return self._generate(prompt, max_tokens=1024)

    def generate_constitutional_analysis(
        self,
        chunks: List[Dict],
        matched_articles: List[Dict],
    ) -> str:
        """Generate constitutional rights analysis grounded in chunks + article matches."""
        context = self._build_context(chunks, max_chars=2000)
        parts = []
        for a in matched_articles[:5]:
            num = a.get("article_number", "")
            title = a.get("title", "")
            expl = a.get("explanation", "") or a.get("text", "")
            if expl and len(expl) > 200:
                expl = expl[:200] + "..."
            parts.append(f"Article {num} ({title}): {expl}")
        articles_text = "\n".join(parts) if parts else "No constitutional articles matched."

        prompt = CONSTITUTIONAL_PROMPT.format(
            system=BASE_SYSTEM,
            context=context,
            articles=articles_text,
        )
        raw = self._generate(prompt, max_tokens=600)
        if not raw or not str(raw).strip():
            return "No constitutional issue is discussed in the case."

        text = str(raw).strip()

        def _looks_incomplete(t: str) -> bool:
            # Too short / single word outputs
            if len(t) < 80:
                return True
            if re.match(r"^[A-Za-z\s,\.]+$", t) and len(t.split()) <= 6:
                return True
            # Common incomplete template: intro + "### 1" with no substance
            if re.search(r"^.*###\s*1\s*$", t, flags=re.IGNORECASE | re.DOTALL):
                return True
            # If it starts like a boilerplate and doesn't contain meaningful section content
            tl = t.lower()
            if tl.startswith("based on the provided") and ("### 2" not in t and "2." not in t):
                return True
            # Meta-instruction style responses (model talking about the prompt instead of the case)
            if "the prompt asks" in tl or tl.startswith("action:"):
                return True
            return False

        if _looks_incomplete(text):
            # Grounded deterministic fallback: avoid fabricating any court interpretation
            if not matched_articles:
                return "No constitutional issue is discussed in the case."
            arts = ", ".join([str(a.get("article_number")) for a in matched_articles[:5] if a.get("article_number")]) or "No matched articles"
            return (
                "The retrieved excerpts do not contain a complete constitutional analysis narrative. "
                f"However, the retrieval pipeline matched the case text against constitutional material "
                f"for: {arts}. Please review the matched provisions and the cited judgment excerpts above."
            )

        return text

    def generate_precedent_comparison(
        self,
        source_chunks: List[Dict],
        precedent_chunks: List[Dict],
    ) -> str:
        """Generate structured comparison between source case and a precedent."""
        source_ctx = self._build_context(source_chunks, max_chars=1500)
        precedent_ctx = self._build_context(precedent_chunks, max_chars=1500)
        prompt = PRECEDENT_COMPARISON_PROMPT.format(
            system=BASE_SYSTEM,
            source_context=source_ctx,
            precedent_context=precedent_ctx,
        )
        return self._generate(prompt, max_tokens=700)

    def answer_question(
        self,
        question: str,
        chunks: List[Dict],
    ) -> str:
        """Answer a user question grounded strictly in retrieved chunks."""
        context = self._build_context(chunks, max_chars=2500)
        prompt = QA_PROMPT.format(
            system=BASE_SYSTEM,
            context=context,
            question=question,
        )
        return self._generate(prompt, max_tokens=400)

    def get_mode(self) -> str:
        """Return which LLM backend is active."""
        return self._mode or "unknown"


# Global singleton
_llm_service: Optional[LLMGenerationService] = None


def get_llm_service() -> LLMGenerationService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMGenerationService()
    return _llm_service
