#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/Users/alikhan/Documents/info490/RewriteLab')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rewritelab_project.settings.development')
django.setup()

from rewrites.models import RewriteSession, RewriteContext, ToneOption, RewriteResult
import secrets
from datetime import timedelta
from django.utils import timezone

# Get contexts and tones
contexts = list(RewriteContext.objects.all())
tones = list(ToneOption.objects.all())

print(f"Found {len(contexts)} contexts and {len(tones)} tones")

# Skip if sessions already exist
if RewriteSession.objects.count() > 0:
    print(f"Sessions already exist: {RewriteSession.objects.count()}")
else:
    # Create sample sessions
    sample_texts = [
        "I am writing to request an extension on the assignment due to unforeseen circumstances.",
        "Please find attached the quarterly report for your review and consideration.",
        "I would like to schedule a meeting to discuss the project timeline and deliverables.",
        "Thank you for your consideration of my application for the software developer position.",
        "I am reaching out to inquire about potential collaboration opportunities.",
        "Could you please provide feedback on the attached document at your earliest convenience?",
        "I wanted to follow up on our previous conversation regarding the budget proposal.",
        "Please let me know if you need any additional information to process my request.",
    ]

    created = 0
    for i, text in enumerate(sample_texts):
        ctx = contexts[i % len(contexts)]
        tone = tones[i % len(tones)]

        session = RewriteSession.objects.create(
            original_text=text,
            context=ctx,
            tone=tone,
            audience="Manager" if i % 2 == 0 else "Professor",
            purpose="Request" if i % 3 == 0 else "Follow-up",
            session_token=secrets.token_hex(32),
            is_completed=i % 3 != 0,
        )

        # Add some results
        if i % 2 == 0:
            RewriteResult.objects.create(
                session=session,
                version_label="A",
                rewritten_text=f"Improved version: {text[:50]}...",
                quality_score="high" if i % 3 == 0 else "medium",
                word_count_original=len(text.split()),
                word_count_rewritten=len(text.split()) + 5,
            )

        created += 1
        # Backdate some sessions for timeline variety
        if i > 0:
            session.created_at = timezone.now() - timedelta(days=i)
            session.save()

    print(f"Created {created} sessions")

print(f"Total sessions: {RewriteSession.objects.count()}")
print(f"Total results: {RewriteResult.objects.count()}")
