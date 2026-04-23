from django.apps import AppConfig


class RewritesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rewrites'

    def ready(self):
        # Register signal handlers (creates AICallLog rows on RewriteResult save)
        from . import signals  # noqa: F401
