"""
Seed realistic simulated AI call logs for the A10 analytics dashboard.

Generates rows spread across the last N days across all 3 AI features
(llm_rewrite, local_rewrite, semantic_search) with realistic distributions
for latency, tokens, and cost so the dashboard has data to visualize on
the deployed site even without live traffic.

Usage:
    python manage.py seed_ai_logs              # default: 400 rows over 14 days
    python manage.py seed_ai_logs --count 1000 --days 30
    python manage.py seed_ai_logs --clear      # wipe existing simulated rows first
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from rewrites.models import AICallLog, RewriteSession
from rewrites.signals import estimate_cost, PRICE_TABLE


class Command(BaseCommand):
    help = "Seed simulated AI call logs for the analytics dashboard."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=400)
        parser.add_argument('--days', type=int, default=14)
        parser.add_argument('--clear', action='store_true',
                            help='Delete existing AICallLog rows first')

    def handle(self, *args, **opts):
        if opts['clear']:
            deleted, _ = AICallLog.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing AICallLog rows.")

        User = get_user_model()
        users = list(User.objects.all()[:20])
        sessions = list(RewriteSession.objects.all()[:200])

        count = opts['count']
        days = opts['days']
        now = timezone.now()

        # Feature mix: LLM gets the majority of traffic
        feature_weights = [
            ('llm_rewrite', 0.60),
            ('semantic_search', 0.25),
            ('local_rewrite', 0.15),
        ]
        features, weights = zip(*feature_weights)

        # Status mix: mostly success, some errors
        status_mix = [('success', 0.93), ('error', 0.05), ('timeout', 0.02)]
        status_vals, status_w = zip(*status_mix)

        created = 0
        for _ in range(count):
            feature = random.choices(features, weights=weights, k=1)[0]
            status = random.choices(status_vals, weights=status_w, k=1)[0]

            # Bias timestamps toward recent days (more recent = more traffic)
            day_offset = int(random.triangular(0, days, 1))
            hour_offset = random.randint(0, 23)
            minute_offset = random.randint(0, 59)
            ts = now - timedelta(
                days=day_offset, hours=hour_offset, minutes=minute_offset
            )

            # Realistic latency distributions per feature
            if feature == 'llm_rewrite':
                latency_ms = int(random.lognormvariate(7.4, 0.4))  # ~1400-3000ms typical
                input_chars = random.randint(80, 1200)
                prompt_tokens = int(input_chars / 4 * 1.2)
                completion_tokens = int(prompt_tokens * random.uniform(0.7, 1.3))
            elif feature == 'local_rewrite':
                latency_ms = int(random.lognormvariate(8.2, 0.3))  # slower on CPU
                input_chars = random.randint(80, 800)
                prompt_tokens = int(input_chars / 4 * 1.2)
                completion_tokens = int(prompt_tokens * random.uniform(0.6, 1.1))
            else:  # semantic_search
                latency_ms = int(random.lognormvariate(5.5, 0.4))  # ~200-400ms
                input_chars = random.randint(10, 200)
                prompt_tokens = int(input_chars / 4)
                completion_tokens = 0

            # Error/timeout tweaks
            if status == 'timeout':
                latency_ms = max(latency_ms * 5, 15000)
                completion_tokens = 0
            elif status == 'error':
                completion_tokens = 0

            cost = estimate_cost(feature, prompt_tokens, completion_tokens)
            model_name = PRICE_TABLE[feature]['model']

            user = random.choice(users) if users else None
            session = random.choice(sessions) if sessions and random.random() < 0.6 else None

            log = AICallLog.objects.create(
                feature=feature,
                model_name=model_name,
                user=user,
                session=session,
                latency_ms=latency_ms,
                input_chars=input_chars,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                status=status,
            )
            # auto_now_add prevents direct assignment on create; backfill:
            AICallLog.objects.filter(pk=log.pk).update(created_at=ts)
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} AICallLog rows across {days} days."
        ))
