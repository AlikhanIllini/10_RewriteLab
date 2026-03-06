"""
Data migration to seed default RewriteContext and ToneOption entries.
"""

from django.db import migrations


def seed_default_data(apps, schema_editor):
    """Create default contexts and tones if they don't exist."""
    RewriteContext = apps.get_model('rewrites', 'RewriteContext')
    ToneOption = apps.get_model('rewrites', 'ToneOption')

    # Default Writing Contexts
    default_contexts = [
        {
            'name': 'Professional Email',
            'description': 'Business emails to colleagues, clients, or supervisors',
            'guidelines': 'Use clear, concise language. Be respectful and professional. Avoid slang and overly casual expressions. Include a clear subject line reference. End with appropriate sign-off.',
            'is_active': True,
        },
        {
            'name': 'Academic Writing',
            'description': 'Essays, papers, and academic correspondence',
            'guidelines': 'Use formal language and proper citations style. Avoid contractions. Be precise and objective. Support claims with evidence. Use discipline-appropriate terminology.',
            'is_active': True,
        },
        {
            'name': 'Casual Message',
            'description': 'Informal messages to friends, family, or close colleagues',
            'guidelines': 'Keep it natural and conversational. Contractions are fine. Match the relationship tone. Be friendly but still clear about your message.',
            'is_active': True,
        },
    ]

    for ctx_data in default_contexts:
        RewriteContext.objects.get_or_create(
            name=ctx_data['name'],
            defaults=ctx_data
        )

    # Default Tone Options
    default_tones = [
        {
            'name': 'Professional',
            'description': 'Business-appropriate, competent, and respectful',
            'prompt_modifier': 'Write in a professional tone. Be clear, competent, and respectful. Avoid overly casual language.',
            'intensity_level': 5,
            'is_active': True,
        },
        {
            'name': 'Friendly',
            'description': 'Warm, approachable, and personable',
            'prompt_modifier': 'Write in a friendly, warm tone. Be approachable and personable while maintaining clarity.',
            'intensity_level': 5,
            'is_active': True,
        },
        {
            'name': 'Direct',
            'description': 'Concise, to-the-point, no fluff',
            'prompt_modifier': 'Write in a direct, concise tone. Get to the point quickly. Remove unnecessary words and filler.',
            'intensity_level': 7,
            'is_active': True,
        },
    ]

    for tone_data in default_tones:
        ToneOption.objects.get_or_create(
            name=tone_data['name'],
            defaults=tone_data
        )


def reverse_seed(apps, schema_editor):
    """Optional: remove seeded data on migration reversal."""
    pass  # Don't delete data on reverse - it might have been modified


class Migration(migrations.Migration):

    dependencies = [
        ('rewrites', '0002_add_user_to_session'),
    ]

    operations = [
        migrations.RunPython(seed_default_data, reverse_seed),
    ]

