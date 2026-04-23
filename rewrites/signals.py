"""
Signal handlers for RewriteLab.

The post_save handler on RewriteResult creates an AICallLog entry with
metrics derived from the existing data model. This keeps the analytics
dashboard up-to-date for real traffic without modifying the AI service
modules (llm_rewrite.py, local_rewrite.py).

Metrics are ESTIMATES derived from what's available:
- latency_ms: distance between session.created_at and result.created_at,
  divided across the N results in the session so numbers stay realistic
- prompt_tokens: ~ word_count_original * 1.3 (OpenAI tokenizer rule-of-thumb)
- completion_tokens: ~ word_count_rewritten * 1.3
- cost_usd: rate-card lookup per feature/model

For precise, real-time telemetry, the AI service modules could be
instrumented directly; derived metrics are adequate for the demo dashboard
and are supplemented by seeded simulated rows.
"""

from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import RewriteResult, AICallLog


# USD per 1K tokens. Kept conservative / illustrative.
PRICE_TABLE = {
    'llm_rewrite': {
        'model': 'gpt-4.1-mini',
        'prompt_per_1k': Decimal('0.00040'),
        'completion_per_1k': Decimal('0.00160'),
    },
    'local_rewrite': {
        'model': 'Qwen2.5-0.5B-Instruct',
        'prompt_per_1k': Decimal('0.00000'),  # self-hosted
        'completion_per_1k': Decimal('0.00000'),
    },
    'semantic_search': {
        'model': 'all-MiniLM-L6-v2',
        'prompt_per_1k': Decimal('0.00000'),
        'completion_per_1k': Decimal('0.00000'),
    },
}


def estimate_cost(feature: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    rates = PRICE_TABLE.get(feature, PRICE_TABLE['llm_rewrite'])
    prompt_cost = (Decimal(prompt_tokens) / Decimal(1000)) * rates['prompt_per_1k']
    completion_cost = (Decimal(completion_tokens) / Decimal(1000)) * rates['completion_per_1k']
    return (prompt_cost + completion_cost).quantize(Decimal('0.000001'))


@receiver(post_save, sender=RewriteResult)
def log_ai_call_from_result(sender, instance: RewriteResult, created: bool, **kwargs):
    """
    Create an AICallLog record when a RewriteResult is first saved.

    Only runs on creation (not updates) to avoid duplicating metrics when
    a user selects a version (is_selected=True flips).
    """
    if not created:
        return

    session = instance.session
    # local rewrite uses version_label "L"; everything else counts as API
    feature = 'local_rewrite' if instance.version_label == 'L' else 'llm_rewrite'
    rates = PRICE_TABLE[feature]

    # Latency proxy: total session wall-clock spread across all results
    elapsed_ms = int(
        (instance.created_at - session.created_at).total_seconds() * 1000
    )
    # guard against clock skew / same-timestamp races
    if elapsed_ms < 0:
        elapsed_ms = 0
    # Spread across expected batch size so per-call numbers are realistic
    batch_size = 3 if feature == 'llm_rewrite' else 1
    latency_ms = max(elapsed_ms // batch_size, 50)

    prompt_tokens = int(instance.word_count_original * 1.3)
    completion_tokens = int(instance.word_count_rewritten * 1.3)
    cost = estimate_cost(feature, prompt_tokens, completion_tokens)

    AICallLog.objects.create(
        feature=feature,
        model_name=rates['model'],
        user=session.user,
        session=session,
        latency_ms=latency_ms,
        input_chars=len(session.original_text),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost,
        status='success',
    )
