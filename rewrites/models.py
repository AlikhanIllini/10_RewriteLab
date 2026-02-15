from django.db import models
from django.core.validators import MinLengthValidator
from django.urls import reverse


class RewriteContext(models.Model):
    """
    Represents a writing context category for text rewriting.

    This model stores predefined context types (e.g., 'Professional Email',
    'Academic Writing') that help the LLM understand the appropriate style
    and conventions to use when generating rewrites. Each context has specific
    guidelines that influence how text should be transformed.

    Why it exists: Different writing situations require different conventions.
    An email to a professor needs different phrasing than a workplace message.
    This model allows the system to categorize and apply context-specific rules.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the writing context (e.g., 'Professional Email')"
    )
    description = models.TextField(
        help_text="Detailed description of when this context should be used"
    )
    guidelines = models.TextField(
        help_text="Specific guidelines for the LLM when rewriting in this context"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this context is available for users to select"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Rewrite Context"
        verbose_name_plural = "Rewrite Contexts"

    def __str__(self):
        return self.name


class ToneOption(models.Model):
    """
    Represents a tone/style option for text rewriting.

    This model stores predefined tone options (e.g., 'Clear', 'Polite',
    'Professional') that determine the emotional quality and formality level
    of generated rewrites. Tones can be combined with any context.

    Why it exists: Users need control over how their text "sounds" beyond just
    the context. A professional email can be direct or diplomatic; academic
    writing can be formal or accessible. This model provides that granularity.
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Name of the tone (e.g., 'Polite', 'Professional')"
    )
    description = models.TextField(
        help_text="Description of what this tone conveys"
    )
    prompt_modifier = models.TextField(
        help_text="Instructions added to the LLM prompt to achieve this tone"
    )
    intensity_level = models.PositiveSmallIntegerField(
        default=5,
        help_text="Intensity level from 1 (subtle) to 10 (strong)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this tone is available for users to select"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Tone Option"
        verbose_name_plural = "Tone Options"

    def __str__(self):
        return self.name


class RewriteSession(models.Model):
    """
    Represents a single rewrite request session from a user.

    This is the main model that captures the user's original text along with
    their selected context, tone, and optional metadata (audience, purpose).
    Each session can generate multiple rewrite results. Sessions are immutable
    once created - editing input creates a new session.

    Why it exists: This is the core entity of RewriteLab. It captures the
    complete state of a rewrite request, enabling the comparison view and
    potential future features like history and analytics.
    """
    original_text = models.TextField(
        validators=[MinLengthValidator(10)],
        help_text="The original text submitted by the user for rewriting"
    )
    context = models.ForeignKey(
        RewriteContext,
        on_delete=models.PROTECT,
        related_name='sessions',
        help_text="The writing context selected for this rewrite"
    )
    tone = models.ForeignKey(
        ToneOption,
        on_delete=models.PROTECT,
        related_name='sessions',
        help_text="The tone selected for this rewrite"
    )
    audience = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Optional: intended audience (e.g., 'professor', 'manager')"
    )
    purpose = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Optional: purpose of the text (e.g., 'request extension', 'follow up')"
    )
    session_token = models.CharField(
        max_length=64,
        unique=True,
        help_text="Unique token to identify this session (for URL sharing)"
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Whether rewrites have been successfully generated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Rewrite Session"
        verbose_name_plural = "Rewrite Sessions"
        constraints = [
            models.UniqueConstraint(
                fields=['original_text', 'context', 'tone'],
                name='unique_text_context_tone_combination'
            )
        ]

    def __str__(self):
        preview = self.original_text[:50] + '...' if len(self.original_text) > 50 else self.original_text
        return f"Session {self.session_token[:8]}: {preview}"

    def get_absolute_url(self):
        """
        Returns the canonical URL for this session.
        Used in templates with {{ session.get_absolute_url }} instead of
        manually building URLs with {% url %} and session.pk
        """
        return reverse('rewrites:session_detail', kwargs={'pk': self.pk})


class RewriteResult(models.Model):
    """
    Represents a single generated rewrite for a session.

    Each RewriteSession can have multiple RewriteResults (typically 2-3),
    allowing users to compare different versions side by side. Each result
    includes the rewritten text and optional metadata about what was changed.

    Why it exists: The core value proposition of RewriteLab is providing
    multiple alternative rewrites for comparison. This model stores each
    generated alternative, enabling the side-by-side comparison feature.
    """
    QUALITY_CHOICES = [
        ('high', 'High Quality'),
        ('medium', 'Medium Quality'),
        ('low', 'Low Quality'),
    ]

    session = models.ForeignKey(
        RewriteSession,
        on_delete=models.CASCADE,
        related_name='results',
        help_text="The session this rewrite belongs to"
    )
    rewritten_text = models.TextField(
        help_text="The generated rewritten version of the original text"
    )
    version_label = models.CharField(
        max_length=20,
        help_text="Label for this version (e.g., 'A', 'B', 'C')"
    )
    change_summary = models.TextField(
        blank=True,
        default='',
        help_text="Optional summary of what was changed in this rewrite"
    )
    quality_score = models.CharField(
        max_length=10,
        choices=QUALITY_CHOICES,
        default='medium',
        help_text="Estimated quality of this rewrite"
    )
    word_count_original = models.PositiveIntegerField(
        default=0,
        help_text="Word count of the original text"
    )
    word_count_rewritten = models.PositiveIntegerField(
        default=0,
        help_text="Word count of this rewritten version"
    )
    is_selected = models.BooleanField(
        default=False,
        help_text="Whether the user selected/copied this version"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['session', 'version_label']
        verbose_name = "Rewrite Result"
        verbose_name_plural = "Rewrite Results"
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'version_label'],
                name='unique_session_version_label'
            )
        ]

    def __str__(self):
        return f"{self.session.session_token[:8]} - Version {self.version_label}"
