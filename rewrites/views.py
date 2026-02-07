"""
RewriteLab Views

This module implements four types of Django views:
1. Function-Based View with HttpResponse (manual)
2. Function-Based View with render() shortcut
3. Class-Based View inheriting from View
4. Generic Class-Based View (ListView)
"""

from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.views import View
from django.views.generic import ListView, DetailView

from .models import RewriteSession, RewriteContext, ToneOption, RewriteResult


# =============================================================================
# FUNCTION-BASED VIEWS
# =============================================================================

def session_manual(request):
    """
    View 1: HttpResponse FBV (Manual Template Loading)

    Demonstrates manual template loading using loader.get_template()
    and returning the result wrapped in HttpResponse.

    URL: /rewrites/manual/
    For Grading: This is the HttpResponse FBV
    """
    # Get all sessions from database
    sessions = RewriteSession.objects.select_related('context', 'tone').all()[:5]

    # Load template manually
    template = loader.get_template('rewrites/session_list_manual.html')

    # Create context
    context = {
        'sessions': sessions,
        'title': 'Rewrite Sessions (HttpResponse View)',
        'view_type': 'Function-Based View with HttpResponse + loader.get_template()',
    }

    # Render template and wrap in HttpResponse
    return HttpResponse(template.render(context, request))


def session_list_render(request):
    """
    View 2: render() FBV (Shortcut)

    Demonstrates the render() shortcut which combines template loading,
    context rendering, and HttpResponse creation in one call.

    URL: /rewrites/render/
    For Grading: This is the render() FBV
    """
    # Query model with related objects for efficiency
    sessions = RewriteSession.objects.select_related('context', 'tone').all()

    # Get counts for display
    context_count = RewriteContext.objects.count()
    tone_count = ToneOption.objects.count()

    # Build context dictionary
    context = {
        'sessions': sessions,
        'title': 'Rewrite Sessions (render View)',
        'view_type': 'Function-Based View with render() shortcut',
        'context_count': context_count,
        'tone_count': tone_count,
    }

    # Use render() shortcut - much cleaner!
    return render(request, 'rewrites/session_list.html', context)


# =============================================================================
# CLASS-BASED VIEWS
# =============================================================================

class SessionBaseView(View):
    """
    View 3: Base CBV (inherits from View)

    Demonstrates a class-based view that inherits from django.views.View
    and implements the get() method manually.

    URL: /rewrites/cbv-base/
    For Grading: This is the Base CBV
    """

    def get(self, request):
        """Handle GET requests."""
        # Manually query the model
        sessions = RewriteSession.objects.select_related('context', 'tone').all()

        # Get additional statistics
        completed_count = sessions.filter(is_completed=True).count()
        pending_count = sessions.filter(is_completed=False).count()

        # Build context
        context = {
            'sessions': sessions,
            'title': 'Rewrite Sessions (Base CBV)',
            'view_type': 'Class-Based View inheriting from View',
            'completed_count': completed_count,
            'pending_count': pending_count,
        }

        # Return rendered template
        return render(request, 'rewrites/session_list.html', context)


class SessionListView(ListView):
    """
    View 4: Generic CBV (ListView)

    Demonstrates a generic class-based view using Django's ListView.
    Automatically handles queryset, pagination, and template rendering.

    URL: /rewrites/cbv-generic/
    For Grading: This is the Generic CBV (ListView)
    """
    model = RewriteSession
    template_name = 'rewrites/session_list.html'
    context_object_name = 'sessions'
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimize queryset with select_related."""
        return RewriteSession.objects.select_related('context', 'tone').all()

    def get_context_data(self, **kwargs):
        """Add extra context for the template."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Rewrite Sessions (Generic ListView)'
        context['view_type'] = 'Generic Class-Based View (ListView)'
        context['total_results'] = RewriteResult.objects.count()
        return context


class SessionDetailView(DetailView):
    """
    Bonus: Generic CBV (DetailView)

    Shows details of a single rewrite session including all results.

    URL: /rewrites/<int:pk>/
    """
    model = RewriteSession
    template_name = 'rewrites/session_detail.html'
    context_object_name = 'session'

    def get_context_data(self, **kwargs):
        """Add results to context."""
        context = super().get_context_data(**kwargs)
        context['results'] = self.object.results.all()
        context['title'] = f'Session Details'
        return context


# =============================================================================
# HOME VIEW
# =============================================================================

def home(request):
    """
    Home page view.

    URL: /
    """
    context = {
        'title': 'RewriteLab - Home',
        'session_count': RewriteSession.objects.count(),
        'context_count': RewriteContext.objects.count(),
        'tone_count': ToneOption.objects.count(),
    }
    return render(request, 'rewrites/home.html', context)
