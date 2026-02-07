from django.contrib import admin
from .models import RewriteContext, ToneOption, RewriteSession, RewriteResult


@admin.register(RewriteContext)
class RewriteContextAdmin(admin.ModelAdmin):
    """Admin configuration for RewriteContext model."""
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('LLM Configuration', {
            'fields': ('guidelines',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ToneOption)
class ToneOptionAdmin(admin.ModelAdmin):
    """Admin configuration for ToneOption model."""
    list_display = ('name', 'intensity_level', 'is_active', 'created_at')
    list_filter = ('is_active', 'intensity_level')
    search_fields = ('name', 'description')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Configuration', {
            'fields': ('prompt_modifier', 'intensity_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class RewriteResultInline(admin.TabularInline):
    """Inline admin for RewriteResult within RewriteSession."""
    model = RewriteResult
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('version_label', 'rewritten_text', 'quality_score', 'is_selected', 'created_at')


@admin.register(RewriteSession)
class RewriteSessionAdmin(admin.ModelAdmin):
    """Admin configuration for RewriteSession model."""
    list_display = ('session_token_short', 'context', 'tone', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'context', 'tone', 'created_at')
    search_fields = ('session_token', 'original_text', 'audience', 'purpose')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RewriteResultInline]
    fieldsets = (
        ('Session Information', {
            'fields': ('session_token', 'is_completed')
        }),
        ('Input Text', {
            'fields': ('original_text',)
        }),
        ('Rewrite Settings', {
            'fields': ('context', 'tone', 'audience', 'purpose')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Session Token')
    def session_token_short(self, obj):
        """Display shortened session token."""
        return obj.session_token[:12] + '...' if len(obj.session_token) > 12 else obj.session_token


@admin.register(RewriteResult)
class RewriteResultAdmin(admin.ModelAdmin):
    """Admin configuration for RewriteResult model."""
    list_display = ('session_display', 'version_label', 'quality_score', 'is_selected', 'word_count_comparison', 'created_at')
    list_filter = ('quality_score', 'is_selected', 'version_label', 'created_at')
    search_fields = ('session__session_token', 'rewritten_text', 'change_summary')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Session Link', {
            'fields': ('session', 'version_label')
        }),
        ('Rewritten Content', {
            'fields': ('rewritten_text', 'change_summary')
        }),
        ('Metrics', {
            'fields': ('quality_score', 'word_count_original', 'word_count_rewritten', 'is_selected')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Session')
    def session_display(self, obj):
        """Display session token."""
        return obj.session.session_token[:8]

    @admin.display(description='Word Count (Orig → New)')
    def word_count_comparison(self, obj):
        """Display word count comparison."""
        return f"{obj.word_count_original} → {obj.word_count_rewritten}"
