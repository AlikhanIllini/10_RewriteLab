import logging

from rewrites.models import RewriteResult, RewriteSession
from rewrites.services.llm_rewrite import compute_quality_score

logger = logging.getLogger(__name__)

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
_PIPE = None


def _get_pipeline():
    """Lazy-load the local generation pipeline and cache it in-process."""
    global _PIPE
    if _PIPE is not None:
        return _PIPE

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    except Exception as exc:  # pragma: no cover - environment-specific import errors
        raise ValueError(
            "Local model dependencies are not installed. Run: pip install -r requirements.txt"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype="auto",
        device_map="auto",
    )
    _PIPE = pipeline("text-generation", model=model, tokenizer=tokenizer)
    return _PIPE


def _build_prompt(session: RewriteSession) -> str:
    """Build a single plain-text instruction prompt for local generation."""
    return (
        "You are a professional editor for RewriteLab. "
        "Rewrite the text to be natural, concise, and human-sounding. "
        "Preserve facts and intent. Do not invent details.\n\n"
        f"Context: {session.context.name}\n"
        f"Context guidelines: {session.context.guidelines}\n"
        f"Tone: {session.tone.name}\n"
        f"Tone modifier: {session.tone.prompt_modifier}\n"
        f"Audience: {session.audience or 'N/A'}\n"
        f"Purpose: {session.purpose or 'N/A'}\n\n"
        "Return only one rewritten version, no bullets and no explanation.\n\n"
        f"Original text:\n{session.original_text.strip()}"
    )


def _extract_generated_text(output) -> str:
    try:
        return output[0]["generated_text"].strip()
    except Exception:
        return ""


def generate_local_rewrite_for_session(session: RewriteSession) -> RewriteResult:
    """
    Generate a single local rewrite and store it as version label 'L'.

    Keeps existing OpenAI versions (A/B/C) intact so both paths coexist.
    """
    original_text = (session.original_text or "").strip()
    if not original_text:
        raise ValueError("Cannot generate rewrite: original text is empty.")

    prompt = _build_prompt(session)
    pipe = _get_pipeline()

    try:
        output = pipe(
            prompt,
            max_new_tokens=220,
            do_sample=False,
            temperature=0.2,
            return_full_text=False,
        )
    except Exception as exc:
        logger.exception("Local rewrite generation failed")
        raise ValueError(f"Local model generation failed: {exc}") from exc

    rewritten_text = _extract_generated_text(output)
    if not rewritten_text:
        raise ValueError("Local model returned empty output. Try again.")

    original_wc = len(original_text.split())
    rewritten_wc = len(rewritten_text.split())
    quality = compute_quality_score(original_text, rewritten_text)

    result, _ = RewriteResult.objects.update_or_create(
        session=session,
        version_label="L",
        defaults={
            "rewritten_text": rewritten_text,
            "change_summary": "Single local Hugging Face rewrite.",
            "quality_score": quality,
            "word_count_original": original_wc,
            "word_count_rewritten": rewritten_wc,
        },
    )

    session.is_completed = True
    session.save(update_fields=["is_completed", "updated_at"])

    return result

