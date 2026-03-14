# RewriteLab AI Design Notes

This document summarizes how AI rewriting works in RewriteLab and how local and external model routes coexist.

## Data Input

- User submits text in a `RewriteSession` via the existing Django UI.
- Required fields: `original_text`, `context`, `tone`.
- Optional fields: `audience`, `purpose`.
- Outputs are persisted as `RewriteResult` rows linked to the same session.

## Preprocessing

- Input text is stripped and validated before generation.
- Prompt context is assembled from:
  - selected writing context and guidelines,
  - selected tone and tone modifier,
  - optional audience and purpose.
- Prompts explicitly instruct models to preserve facts and avoid adding new claims.

## Safety Guardrails

- Empty or whitespace-only input is rejected for generation.
- Prompt instructions require:
  - preserving original meaning,
  - no invented names/dates/commitments,
  - concise and human-sounding output,
  - avoidance of generic AI filler phrasing.
- Generation failures are caught and returned as user-facing error messages instead of server crashes.
- API keys are read from `.env` (never hardcoded in source files).

## Local LLM Integration

- Local rewrite path is implemented in `rewrites/services/local_rewrite.py`.
- Uses a lightweight Hugging Face instruction model: `Qwen/Qwen2.5-0.5B-Instruct`.
- Model/tokenizer are loaded lazily and cached in-process.
- Hugging Face weights download automatically on first local run.
- Local generation stores one rewrite in the existing flow as `RewriteResult` with version label `L`.
- Existing session storage (`RewriteSession`, `RewriteResult`) is reused; no new database model is introduced.

## External API Integration

- OpenAI rewrite path remains in `rewrites/services/llm_rewrite.py`.
- It generates versions `A`, `B`, and `C` using the existing prompt and quality-score pipeline.
- OpenAI key is loaded from `OPENAI_API_KEY` in environment variables.
- Local and API routes are separate endpoints and can be used independently on the same session.

## Hybrid Potential

A practical hybrid strategy for RewriteLab:

- Run local model first for low-cost drafts and classroom demos.
- Escalate to OpenAI for higher-stakes writing (job applications, final submissions).
- Keep both outputs in one session so users can compare speed, style, and quality.
- Add future policy routing by text length, context type, or quality threshold.

