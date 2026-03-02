"""
LLM-powered rewrite generation service for RewriteLab.

This module encapsulates all OpenAI interaction logic:
- build_prompt(session) — assembles the chat messages
- call_llm(messages) — sends the request and parses JSON
- compute_quality_score(original, rewritten) — simple heuristic
- generate_rewrites_for_session(session) — orchestrates the full flow
"""

import json
import os
import logging
from typing import Optional

from openai import OpenAI, APIError, AuthenticationError, RateLimitError

from rewrites.models import RewriteSession, RewriteResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Filler phrases used in quality heuristic
# ---------------------------------------------------------------------------
AI_FILLER_PHRASES = [
    "i hope this email finds you well",
    "i wanted to reach out",
    "please let me know if you have any questions",
    "please don't hesitate to",
    "i would like to take this opportunity",
    "as per our conversation",
    "in today's fast-paced world",
    "it goes without saying",
    "at the end of the day",
    "needless to say",
    "with that being said",
]

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

SYSTEM_MESSAGE = (
    "You are a professional editor. You rewrite text to sound human, "
    "concise, and context-appropriate. No filler."
)


def build_prompt(session: RewriteSession) -> list[dict]:
    """
    Build the chat-completion messages list for a RewriteSession.

    Returns a list of message dicts with roles: system, developer, user.
    """
    # --- developer instructions ---
    dev_parts = [
        "Rewrite the user's text into 3 distinct versions (A, B, C).",
        "",
        f"Writing context: {session.context.name}",
        f"Context guidelines: {session.context.guidelines}",
        "",
        f"Tone: {session.tone.name}",
        f"Tone modifier: {session.tone.prompt_modifier}",
    ]

    if session.audience:
        dev_parts.append(f"Audience: {session.audience}")
    if session.purpose:
        dev_parts.append(f"Purpose: {session.purpose}")

    dev_parts += [
        "",
        "Rules:",
        "- Preserve every fact. Do NOT invent names, dates, or commitments.",
        "- Do NOT add new information that isn't in the original.",
        "- Avoid clichés and generic AI phrases (e.g. 'I hope this finds you well').",
        "- Use short sentences. Remove redundancy and filler.",
        "- Keep the user's intent exactly.",
        "- Sound like a competent human editor, not a chatbot.",
        "",
        "Version guidelines:",
        "- A: most concise and direct.",
        "- B: balanced professional — clear and polite.",
        "- C: slightly warmer / more diplomatic, still concise.",
        "",
        "Return STRICT JSON only (no markdown, no extra text):",
        '{',
        '  "rewrites": [',
        '    {"version_label":"A","rewritten_text":"...","change_summary":"one sentence"},',
        '    {"version_label":"B","rewritten_text":"...","change_summary":"one sentence"},',
        '    {"version_label":"C","rewritten_text":"...","change_summary":"one sentence"}',
        '  ]',
        '}',
    ]

    developer_message = "\n".join(dev_parts)

    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "developer", "content": developer_message},
        {"role": "user", "content": session.original_text},
    ]


# ---------------------------------------------------------------------------
# LLM caller
# ---------------------------------------------------------------------------

def _get_client() -> OpenAI:
    """Return an OpenAI client. Raises ValueError if key is missing."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or environment variables."
        )
    return OpenAI(api_key=api_key)


def call_llm(messages: list[dict], model: str = "gpt-4.1-mini") -> list[dict]:
    """
    Send messages to the OpenAI chat-completions API and return parsed
    rewrite dicts.

    Returns a list of dicts, each with keys:
        version_label, rewritten_text, change_summary
    """
    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
    except AuthenticationError:
        raise ValueError(
            "Invalid OpenAI API key. Please check your OPENAI_API_KEY "
            "in the .env file and make sure it is a valid key from "
            "https://platform.openai.com/account/api-keys"
        )
    except RateLimitError:
        raise ValueError(
            "OpenAI rate limit exceeded or quota reached. "
            "Please wait a moment and try again, or check your plan's usage limits."
        )
    except APIError as exc:
        logger.error("OpenAI API error: %s", exc)
        raise ValueError(
            f"OpenAI API error (status {exc.status_code}): "
            "The request could not be completed. Please try again later."
        )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw[:500])
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    rewrites = data.get("rewrites")
    if not isinstance(rewrites, list) or len(rewrites) < 2:
        raise ValueError(
            f"Expected 'rewrites' array with 2–3 items, got: {type(rewrites)}"
        )

    # Validate each rewrite dict
    for rw in rewrites:
        for key in ("version_label", "rewritten_text", "change_summary"):
            if key not in rw:
                raise ValueError(f"Missing key '{key}' in rewrite: {rw}")

    return rewrites[:3]  # cap at 3


# ---------------------------------------------------------------------------
# Quality heuristic
# ---------------------------------------------------------------------------

def compute_quality_score(original_text: str, rewritten_text: str) -> str:
    """
    Simple rule-based quality score.

    Returns 'high' if:
    - rewritten word count <= original word count * 1.15 (not much longer)
    - no AI filler phrases detected
    - rewritten text is non-empty

    Otherwise returns 'medium'.
    """
    if not rewritten_text.strip():
        return "low"

    original_wc = len(original_text.split())
    rewritten_wc = len(rewritten_text.split())

    # Check for filler phrases
    lower_text = rewritten_text.lower()
    has_filler = any(phrase in lower_text for phrase in AI_FILLER_PHRASES)

    # Shorter or similar length + no filler = high
    if rewritten_wc <= original_wc * 1.15 and not has_filler:
        return "high"

    return "medium"


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def generate_rewrites_for_session(
    session: RewriteSession,
    n: int = 3,
) -> list[RewriteResult]:
    """
    Generate rewrites for a session via the LLM, save as RewriteResult
    objects, and mark the session completed.

    Steps:
    1. Build prompt from session data
    2. Call LLM
    3. Delete any existing results for this session
    4. Create new RewriteResult rows
    5. Mark session.is_completed = True

    Returns the list of created RewriteResult instances.
    """
    messages = build_prompt(session)
    rewrites = call_llm(messages)

    original_wc = len(session.original_text.split())

    # Delete old results (enables regeneration)
    session.results.all().delete()

    created = []
    for rw in rewrites[:n]:
        rewritten_text = rw["rewritten_text"]
        rewritten_wc = len(rewritten_text.split())
        quality = compute_quality_score(session.original_text, rewritten_text)

        result = RewriteResult.objects.create(
            session=session,
            version_label=rw["version_label"],
            rewritten_text=rewritten_text,
            change_summary=rw.get("change_summary", ""),
            quality_score=quality,
            word_count_original=original_wc,
            word_count_rewritten=rewritten_wc,
        )
        created.append(result)

    session.is_completed = True
    session.save(update_fields=["is_completed", "updated_at"])

    return created




