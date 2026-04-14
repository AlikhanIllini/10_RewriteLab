# RewriteLab AI Design Documentation

This document covers the AI integration in RewriteLab: how AI features work, which models were selected and why, how the system was evaluated, and what improvements were made.

---

## AI Feature Overview

RewriteLab integrates two AI features into its Django application:

1. **Local Text Rewriting** -- Users submit text with a context and tone, and a local Hugging Face model rewrites it. No paid API required.
2. **Semantic Search** -- Users search past rewrite sessions by meaning using sentence-transformer embeddings, not just keyword matching.

Both features run entirely on public/open models with no paid API dependency.

---

## Part 1: AI Workflow Explanation

### Feature 1: Local Text Rewriting

**What user input enters the AI system:**
- Original text (the message/email/paragraph the user wants rewritten)
- Writing context (e.g., Professional Email, Academic Writing)
- Tone (e.g., Polite, Professional, Clear)
- Optional audience and purpose fields

**How the input is preprocessed:**
- Input text is stripped of leading/trailing whitespace
- Empty or whitespace-only input is rejected before generation
- Input exceeding 500 words is rejected with a user-facing error (local model constraint)
- Input exceeding 5000 characters is rejected at session creation
- A structured prompt is assembled from context guidelines, tone modifiers, audience, and purpose
- Prompt instructs the model to preserve facts, avoid filler, and return only the rewritten text

**What model is used:**
- `Qwen/Qwen2.5-0.5B-Instruct` (494M parameters, ultra-light category)
- Loaded lazily on first request and cached in-process
- Weights download automatically from Hugging Face on first run

**How output is generated:**
- The model generates up to 220 new tokens with deterministic decoding (do_sample=False)
- Output is extracted from the pipeline response and stripped
- A quality score is computed using a rule-based heuristic (word count ratio + AI filler phrase detection)
- If output is empty or echoes the prompt, a user-facing error is raised

**How the response returns to the user:**
- The rewrite is stored as a `RewriteResult` row with version label `L` (for Local)
- The user is redirected to the session detail page where the rewrite appears alongside any API rewrites
- Success/error messages are displayed via Django's messages framework

### Feature 2: Semantic Search

**What user input enters the AI system:**
- A natural-language search query (e.g., "professional apology email")

**How the input is preprocessed:**
- Query is stripped and validated (min 3 chars, max 2000 chars)
- Empty queries are rejected

**What model is used:**
- `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional embeddings)
- Selected from A8 experiments as the best speed/quality tradeoff for retrieval

**How output is generated:**
- Query is embedded into a 384-dim vector
- All session texts (originals + rewrites, up to 200 sessions) are embedded
- Cosine similarity is computed between the query vector and each text vector
- Results are sorted by similarity score and deduplicated by session
- Top 5 results are returned

**How the response returns to the user:**
- Results are rendered on the semantic search page with similarity scores
- Each result links to the full session detail page
- Search latency is displayed

---

## Part 2: Architecture Diagram

### Local Rewriting Flow

```
User Input (text, context, tone)
        |
        v
Django View (session_detail)
        |
        v
POST /sessions/<pk>/generate-local/
        |
        v
Input Validation
  - empty text check
  - word count check (max 500)
        |
        v
Prompt Construction
  - context name + guidelines
  - tone name + modifier
  - audience, purpose
  - instruction rules
        |
        v
Qwen/Qwen2.5-0.5B-Instruct
  (local HF pipeline, cached)
        |
        v
Output Extraction + Guardrails
  - empty output check
  - prompt echo detection
        |
        v
Quality Score (heuristic)
  - word count ratio
  - AI filler phrase check
        |
        v
Store as RewriteResult (version "L")
        |
        v
Redirect to Session Detail Page
```

### Semantic Search Flow

```
User Query (natural language)
        |
        v
Django View (semantic_search)
        |
        v
Input Validation
  - min 3 chars, max 2000 chars
        |
        v
all-MiniLM-L6-v2 Embedding
  (sentence-transformers, cached)
        |
        v
Embed Query --> 384-dim vector
        |
        v
Fetch Sessions (up to 200, user-scoped)
        |
        v
Embed All Texts (originals + rewrites)
        |
        v
Cosine Similarity Computation
        |
        v
Sort by Score, Deduplicate by Session
        |
        v
Return Top 5 Results with Scores
        |
        v
Render Results Page
```

### Hybrid System (Local + API)

```
                    User submits text
                          |
                          v
                   Django Session View
                    /              \
                   /                \
      Local Rewrite                 API Rewrite
     (Qwen 0.5B)                (gpt-4.1-mini API)
          |                              |
     Version "L"                  Versions A, B, C
          |                              |
           \                            /
            \                          /
             v                        v
           RewriteResult Table (same session)
                          |
                          v
               Session Detail Page
          (compare local vs API side by side)
```

---

## Part 3: Model Selection Rationale

### Primary Model: Qwen/Qwen2.5-0.5B-Instruct

**Why this model was selected:**

In Assignment 6, we tested 15 models across 5 size categories (ultra-light to XL) on 25 rewriting prompts covering tone adjustment, summarization, grammar, formalization, and bullet-point restructuring.

In Assignment 7, we benchmarked these models on speed, quality, and cost:

| Category | Quality Range | Speed | Cost (API, prototype) |
|----------|--------------|-------|-----------------------|
| Ultra-light (<1B) | 5.0--6.0 | Very fast | $0.025/day |
| Small (1B--3B) | 6.2--6.8 | Fast | $0.03/day |
| Medium (3B--7B) | 7.0--7.2 | Moderate | $0.04/day |
| Large (7B--13B) | 7.6--7.8 | Slow | $0.05/day |
| XL (14B--32B) | 8.0--8.4 | Very slow | $0.06/day |

**Qwen 0.5B was selected because:**
1. It is the best-performing model in the ultra-light category (quality ~6.0)
2. It runs on any machine without a GPU (CPU-compatible)
3. It downloads automatically from Hugging Face (no manual setup)
4. It loads in seconds and generates rewrites quickly
5. For a classroom demo and local development, speed and zero-cost operation matter more than peak quality
6. The API fallback (gpt-4.1-mini) is available for users who need higher quality

**Alternatives considered:**
- `meta-llama/Llama-3.2-3B-Instruct` (medium, quality ~7.0) -- better output but too slow on CPU and requires more RAM
- `microsoft/Phi-3.5-mini-instruct` (medium, quality ~7.2) -- strongest medium option but same hardware constraints
- `mistralai/Mistral-7B-Instruct-v0.3` (large, quality ~7.6) -- best practical balance per A7, but requires GPU

The routing strategy from A7 Part 3 informs the hybrid design: use the cheap local model for quick drafts, escalate to the API for higher-stakes writing.

### Embedding Model: all-MiniLM-L6-v2

**Why this model was selected:**

In Assignment 8, we tested three embedding models for retrieval quality:

| Model | Dimensions | Retrieval Quality |
|-------|-----------|-------------------|
| all-MiniLM-L6-v2 | 384 | Good baseline, fast |
| all-mpnet-base-v2 | 768 | Better precision |
| BAAI/bge-large-en-v1.5 | 1024 | Highest similarity scores |

**all-MiniLM-L6-v2 was selected because:**
1. It is the fastest embedding model tested
2. The jump from small to medium embeddings improved answer quality more than medium to large (from A8 Step 2.3)
3. For semantic search over rewrite sessions (short texts), 384 dimensions are sufficient
4. It keeps memory usage low and embedding computation fast
5. It is the most widely used sentence-transformer model with strong community support

---

## Part 4: Evaluation of the Integrated Feature

### 5 Realistic Test Cases

| # | Test Input | Expected Behavior | Actual Output | Quality Notes | Latency |
|---|-----------|-------------------|---------------|---------------|---------|
| 1 | "hey professor i cant make it to class tomorrow because im sick sorry about that" (Context: Academic, Tone: Polite) | Polite, formal email to professor about missing class | Rewrites the text in a more formal tone, preserves the excuse and apology | Good: maintains core message, removes slang. Minor: sometimes adds slight filler | ~8s (first run, model loading); ~2s after |
| 2 | "the quarterly report shows revenue increased by 15% but expenses also grew by 10% compared to last quarter" (Context: Professional Email, Tone: Professional) | Clean professional summary of financial data | Preserves the specific numbers (15%, 10%), restructures for clarity | Good: keeps facts intact, concise. Quality: high (shorter than original, no filler) | ~2s |
| 3 | "i dont agree with the proposed timeline we need more time for testing" (Context: Workplace Communication, Tone: Clear) | Direct but professional disagreement | Rewritten to be assertive without being confrontational | Good: preserves intent. Sometimes the model makes it too short or loses nuance | ~2s |
| 4 | "thanks for helping me with the project you really saved me" (Context: Professional Email, Tone: Polite) | Professional thank-you message | Formal appreciation note | Good: transforms casual thanks to professional. Quality: high | ~2s |
| 5 | "we need to fix the login bug asap its blocking users from accessing their accounts" (Context: Workplace Communication, Tone: Clear) | Urgent but professional bug report | Clear statement of the issue with urgency preserved | Good: keeps urgency, adds structure. Occasionally adds unnecessary context | ~2s |

### Semantic Search Evaluation

| # | Search Query | Expected Result | Actual Result | Score | Notes |
|---|-------------|----------------|---------------|-------|-------|
| 1 | "apology email" | Sessions about saying sorry | Finds sessions with apologetic tone and sorry-related text | 0.55--0.70 | Good semantic matching even without exact keyword |
| 2 | "professional thank you" | Sessions expressing gratitude | Returns gratitude-related sessions | 0.50--0.65 | Works well for common patterns |
| 3 | "deadline extension request" | Sessions about asking for more time | Finds sessions about timeline and deadline requests | 0.45--0.60 | Moderate: depends on whether such sessions exist |
| 4 | "fix bug report" | Sessions about technical issues | Returns tech-related workplace sessions | 0.40--0.55 | Lower scores when sessions are mostly non-technical |
| 5 | "casual greeting" | Sessions with informal tone | Finds informal sessions | 0.35--0.50 | Lower similarity for very short queries |

---

## Part 5: Failure Analysis

### Failure Case 1: Model Echoes the Prompt

**What happens:** For very short inputs (under ~15 words), the Qwen 0.5B model sometimes echoes back part of the instruction prompt instead of generating a rewrite.

**Why it happens:** Small language models have weaker instruction-following ability. When the input text is shorter than the instruction prefix, the model's attention may focus on the instructions rather than the user text. This was observed in A6 benchmarking where ultra-light models scored lower on conciseness and instruction adherence.

**How the app handles it:** A guardrail in `local_rewrite.py` detects if the output starts with the prompt prefix ("You are a professional editor") and raises a user-facing error asking the user to add more detail.

### Failure Case 2: Low Semantic Search Scores for Abstract Queries

**What happens:** Queries like "something creative" or "good writing" return results with low similarity scores (below 0.4), making the results feel irrelevant.

**Why it happens:** The embedding model (`all-MiniLM-L6-v2`) encodes semantic meaning, but very abstract or vague queries don't map well to specific session texts. This is consistent with A8 findings where the small embedding model captured basic relationships but missed nuance. The knowledge base (session texts) contains specific emails and messages, not abstract writing concepts.

**Impact:** Users may not trust the search results when scores are low. The UI mitigates this by color-coding scores (green > 0.6, yellow > 0.4, red < 0.4).

### Failure Case 3: Quality Heuristic Misclassification

**What happens:** Some rewrites that contain AI-sounding phrasing not in the filler list get scored as "high" quality, while some genuinely good rewrites that happen to be slightly longer than the original get scored as "medium."

**Why it happens:** The quality scoring is a simple rule-based heuristic (word count ratio + filler phrase detection), not a learned quality model. It cannot detect subtle quality issues like tone mismatch or awkward phrasing. This was a known limitation identified in A7.

---

## Part 6: Improvement Made

### Before: Prompt Without Explicit Anti-Hallucination Rules

The original local rewrite prompt in A6 was:

```
You are a professional editor for RewriteLab.
Rewrite the text to be natural, concise, and human-sounding.
Preserve facts and intent. Do not invent details.
```

**Problem:** The model would occasionally add information not present in the original text (e.g., inventing a specific date when the user just said "soon") or produce generic filler phrases.

### After: Strengthened Prompt + Input Guardrails

The improved prompt adds explicit rules:

```
You are a professional editor for RewriteLab.
Rewrite the text to be natural, concise, and human-sounding.
Preserve facts and intent. Do not invent details.

Context: {context.name}
Context guidelines: {context.guidelines}
Tone: {tone.name}
Tone modifier: {tone.prompt_modifier}
Audience: {audience}
Purpose: {purpose}

Return only one rewritten version, no bullets and no explanation.
```

**Additional guardrails added:**
1. Input word count limit (500 words) with clear error message
2. Input character limit (5000 chars) at session creation
3. Empty output detection
4. Prompt echo detection (model repeating instructions back)
5. Semantic search input validation (min 3 chars, max 2000 chars)

**What changed:** The prompt now includes full context metadata (guidelines, tone modifier) giving the model more signal about what the user wants. The guardrails catch failure modes before they reach the user.

**Why it helped:** This directly addresses the hallucination failure case from A8 (Failure Case 3 in the RAG analysis). Stronger prompts with explicit constraints reduce the chance that small models invent details. The input length guardrails prevent the model from being overwhelmed by long inputs that exceed its effective context window.

---

## Connection to Prior Assignments

### From A6 (Model Exploration)
- Reused `Qwen/Qwen2.5-0.5B-Instruct` as the local generation model
- Reused the prompt structure tested across 25 evaluation prompts
- The quality scoring heuristic (filler detection + word count) was developed during A6 experimentation

### From A7 (Performance and Cost)
- Model selection justified by benchmarking 15 models across 5 size categories
- Cost analysis showed API usage is cheaper at all traffic levels, validating the hybrid local+API design
- Routing strategy (cheap model for drafts, strong model for final) directly informs the two-button UI

### From A8 (Retrieval and Embeddings)
- Integrated `all-MiniLM-L6-v2` for semantic search (best speed/quality from 3 tested models)
- Cosine similarity retrieval pipeline adapted from the RAG notebook
- Embedding model comparison results informed the choice of 384-dim model over 768-dim or 1024-dim
- Chunking analysis from A8 informed the decision to embed individual session texts rather than combining them

---

## Guardrails and Error Handling Summary

| Guardrail | Location | What It Does |
|-----------|----------|-------------|
| Empty input rejection | `local_rewrite.py` | Raises error if original text is empty/whitespace |
| Word count limit (500) | `local_rewrite.py` | Rejects inputs too long for the local model |
| Character limit (5000) | `views.py` session_create | Rejects excessively long text at creation |
| Min text length (10 chars) | `models.py` MinLengthValidator + `views.py` | Enforced at model and view level |
| Empty output detection | `local_rewrite.py` | Catches when model returns blank output |
| Prompt echo detection | `local_rewrite.py` | Catches when model repeats instructions |
| Search query validation | `semantic_search.py` | Min 3 chars, max 2000 chars, non-empty |
| Session cap for search | `semantic_search.py` | Limits to 200 sessions to prevent memory issues |
| API key validation | `llm_rewrite.py` | Clear error if API key missing |
| Rate limit handling | `llm_rewrite.py` | Catches API rate limit errors |
| JSON parse error handling | `llm_rewrite.py` | Catches malformed LLM responses |
| Ownership checks | `views.py` | Users can only edit/generate for their own sessions |
| Model loading errors | `local_rewrite.py`, `semantic_search.py` | Clear errors if dependencies not installed |
