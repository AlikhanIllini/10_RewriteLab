"""
RewriteLab Views

This module implements multiple Django view patterns:
1. Function-Based View with HttpResponse (manual)
2. Function-Based View with render() shortcut
3. Class-Based View inheriting from View
4. Generic Class-Based View (ListView)
5. Search views (GET and POST)
6. Analytics views with charts
7. API views with JSON responses
8. A4: Vega-Lite charts, External API, CSV/JSON exports
"""

import csv
import json
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.decorators.http import require_POST
from django.contrib import messages as django_messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Avg
from django.utils import timezone
import functools
import io
import requests
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from .models import RewriteSession, RewriteContext, ToneOption, RewriteResult


# =============================================================================
# HELPERS
# =============================================================================

def api_login_required(view_func):
    """Decorator for API endpoints: returns 401 JSON if not authenticated."""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'error': 'Authentication required. Please log in.'},
                status=401,
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# FUNCTION-BASED VIEWS
# =============================================================================

@login_required(login_url='rewrites:login')
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


@login_required(login_url='rewrites:login')
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

class SessionBaseView(LoginRequiredMixin, View):
    """
    View 3: Base CBV (inherits from View)

    Demonstrates a class-based view that inherits from django.views.View
    and implements the get() method manually.

    URL: /rewrites/cbv-base/
    For Grading: This is the Base CBV
    """
    login_url = 'rewrites:login'

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


class SessionListView(LoginRequiredMixin, ListView):
    """
    View 4: Generic CBV (ListView)

    Demonstrates a generic class-based view using Django's ListView.
    Automatically handles queryset, pagination, and template rendering.

    URL: /rewrites/cbv-generic/
    For Grading: This is the Generic CBV (ListView)
    """
    login_url = 'rewrites:login'
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


class SessionDetailView(LoginRequiredMixin, DetailView):
    """
    Bonus: Generic CBV (DetailView)

    Shows details of a single rewrite session including all results.

    URL: /rewrites/<int:pk>/
    """
    login_url = 'rewrites:login'
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


# =============================================================================
# SECTION 2: ORM QUERIES & DATA PRESENTATION
# =============================================================================

@login_required(login_url='rewrites:login')
def search(request):
    """
    Search view with both GET and POST forms.

    GET: For shareable search results (URL contains query params)
    POST: For form submission with hidden data

    URL: /search/
    For Grading: Demonstrates GET, POST, __icontains, __exact, relationship spanning
    """
    sessions = RewriteSession.objects.select_related('context', 'tone').all()
    contexts = RewriteContext.objects.filter(is_active=True)
    tones = ToneOption.objects.filter(is_active=True)

    # GET search - for text search (shareable URL)
    get_query = request.GET.get('q', '')
    if get_query:
        # __icontains filter for case-insensitive search
        sessions = sessions.filter(
            Q(original_text__icontains=get_query) |
            Q(audience__icontains=get_query) |
            Q(purpose__icontains=get_query)
        )

    # POST search - for filtered search (non-shareable, hides filter data)
    post_context = None
    post_tone = None
    post_status = None

    if request.method == 'POST':
        post_context = request.POST.get('context', '')
        post_tone = request.POST.get('tone', '')
        post_status = request.POST.get('status', '')

        if post_context:
            # Relationship spanning: filter by context__name
            sessions = sessions.filter(context__name__exact=post_context)

        if post_tone:
            # Relationship spanning: filter by tone__name
            sessions = sessions.filter(tone__name__exact=post_tone)

        if post_status:
            # __exact filter
            is_completed = post_status == 'completed'
            sessions = sessions.filter(is_completed__exact=is_completed)

    # Aggregations
    total_count = RewriteSession.objects.count()
    filtered_count = sessions.count()

    # Grouped aggregations - count by context
    sessions_by_context = RewriteSession.objects.values('context__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # Grouped aggregations - count by tone
    sessions_by_tone = RewriteSession.objects.values('tone__name').annotate(
        count=Count('id')
    ).order_by('-count')

    context = {
        'title': 'Search Sessions',
        'sessions': sessions,
        'contexts': contexts,
        'tones': tones,
        'get_query': get_query,
        'post_context': post_context,
        'post_tone': post_tone,
        'post_status': post_status,
        'total_count': total_count,
        'filtered_count': filtered_count,
        'sessions_by_context': sessions_by_context,
        'sessions_by_tone': sessions_by_tone,
    }
    return render(request, 'rewrites/search.html', context)


# =============================================================================
# SECTION 4: DATA VISUALIZATION (MATPLOTLIB)
# =============================================================================

@login_required(login_url='rewrites:login')
def analytics(request):
    """
    Analytics page showing charts and statistics.

    URL: /analytics/
    For Grading: Displays chart images generated by matplotlib
    """
    # Get aggregated data for display
    sessions_by_context = RewriteSession.objects.values('context__name').annotate(
        count=Count('id')
    ).order_by('-count')

    sessions_by_tone = RewriteSession.objects.values('tone__name').annotate(
        count=Count('id')
    ).order_by('-count')

    results_by_quality = RewriteResult.objects.values('quality_score').annotate(
        count=Count('id')
    ).order_by('quality_score')

    # Statistics
    total_sessions = RewriteSession.objects.count()
    total_results = RewriteResult.objects.count()
    completed_sessions = RewriteSession.objects.filter(is_completed=True).count()
    avg_results_per_session = RewriteResult.objects.count() / max(RewriteSession.objects.count(), 1)

    context = {
        'title': 'Analytics Dashboard',
        'sessions_by_context': sessions_by_context,
        'sessions_by_tone': sessions_by_tone,
        'results_by_quality': results_by_quality,
        'total_sessions': total_sessions,
        'total_results': total_results,
        'completed_sessions': completed_sessions,
        'avg_results_per_session': round(avg_results_per_session, 1),
    }
    return render(request, 'rewrites/analytics.html', context)


@login_required(login_url='rewrites:login')
def chart_sessions_by_context(request):
    """
    Generate a bar chart of sessions by context.

    URL: /charts/sessions-by-context.png
    For Grading: Image endpoint using BytesIO and HttpResponse

    Memory Awareness: Uses BytesIO to hold the image in RAM temporarily,
    then writes directly to HttpResponse. The buffer is closed after use
    to free memory.
    """
    # ORM aggregation query
    data = RewriteSession.objects.values('context__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # Extract data for plotting
    labels = [item['context__name'] for item in data]
    values = [item['count'] for item in data]

    # Create figure with appropriate size
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar chart with styling
    colors = ['#667eea', '#764ba2', '#48bb78', '#ed8936', '#f56565']
    bars = ax.bar(labels, values, color=colors[:len(labels)], edgecolor='white', linewidth=1.5)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(val), ha='center', va='bottom', fontweight='bold', fontsize=12)

    # Styling
    ax.set_xlabel('Writing Context', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Sessions', fontsize=12, fontweight='bold')
    ax.set_title('Rewrite Sessions by Context', fontsize=14, fontweight='bold', pad=20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Use BytesIO for memory-efficient image generation
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)  # Close figure to free memory

    buffer.seek(0)

    # Return image as HttpResponse with PNG MIME type
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required(login_url='rewrites:login')
def chart_sessions_by_tone(request):
    """
    Generate a pie chart of sessions by tone.

    URL: /charts/sessions-by-tone.png
    For Grading: Another chart endpoint demonstrating pie chart
    """
    # ORM aggregation query
    data = RewriteSession.objects.values('tone__name').annotate(
        count=Count('id')
    ).order_by('-count')

    labels = [item['tone__name'] for item in data]
    values = [item['count'] for item in data]

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 8))

    # Create pie chart
    colors = ['#667eea', '#764ba2', '#48bb78', '#ed8936', '#f56565', '#38b2ac', '#ed64a6']
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        colors=colors[:len(labels)],
        explode=[0.02] * len(labels),
        shadow=True,
        startangle=90
    )

    # Style the percentage labels
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title('Session Distribution by Tone', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='lower right')

    # Use BytesIO
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required(login_url='rewrites:login')
def chart_results_quality(request):
    """
    Generate a horizontal bar chart of results by quality score.

    URL: /charts/results-quality.png
    """
    data = RewriteResult.objects.values('quality_score').annotate(
        count=Count('id')
    ).order_by('quality_score')

    labels = [item['quality_score'].capitalize() for item in data]
    values = [item['count'] for item in data]

    fig, ax = plt.subplots(figsize=(8, 5))

    colors = {'Low': '#f56565', 'Medium': '#ed8936', 'High': '#48bb78'}
    bar_colors = [colors.get(label, '#667eea') for label in labels]

    bars = ax.barh(labels, values, color=bar_colors, edgecolor='white', linewidth=1.5)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                str(val), ha='left', va='center', fontweight='bold')

    ax.set_xlabel('Number of Results', fontsize=12, fontweight='bold')
    ax.set_title('Rewrite Results by Quality Score', fontsize=14, fontweight='bold', pad=20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')


# =============================================================================
# SECTION 5: FORMS & USER INPUT
# =============================================================================

class SessionSearchView(LoginRequiredMixin, ListView):
    """
    CBV that handles both GET and POST for search functionality.

    URL: /sessions/search/
    For Grading: CBV adapted to handle GET (search) and POST (create session)
    """
    login_url = 'rewrites:login'
    model = RewriteSession
    template_name = 'rewrites/session_search.html'
    context_object_name = 'sessions'

    def get_queryset(self):
        """Filter based on GET query parameters."""
        queryset = RewriteSession.objects.select_related('context', 'tone').all()

        # Handle GET parameters for filtering
        q = self.request.GET.get('q', '')
        context_filter = self.request.GET.get('context', '')

        if q:
            queryset = queryset.filter(
                Q(original_text__icontains=q) |
                Q(audience__icontains=q)
            )

        if context_filter:
            queryset = queryset.filter(context__id=context_filter)

        return queryset

    def get_context_data(self, **kwargs):
        """Add form data to context."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Search & Create Sessions'
        context['contexts'] = RewriteContext.objects.filter(is_active=True)
        context['tones'] = ToneOption.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('q', '')
        context['context_filter'] = self.request.GET.get('context', '')
        context['success_message'] = self.request.GET.get('success', '')
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST request to create a new session."""
        import secrets

        original_text = request.POST.get('original_text', '').strip()
        context_id = request.POST.get('context')
        tone_id = request.POST.get('tone')
        audience = request.POST.get('audience', '').strip()
        purpose = request.POST.get('purpose', '').strip()

        errors = []
        if len(original_text) < 10:
            errors.append('Original text must be at least 10 characters.')
        if not context_id:
            errors.append('Please select a writing context.')
        if not tone_id:
            errors.append('Please select a tone.')

        if errors:
            # Re-render with errors
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            context['errors'] = errors
            context['form_data'] = {
                'original_text': original_text,
                'context': context_id,
                'tone': tone_id,
                'audience': audience,
                'purpose': purpose,
            }
            return render(request, self.template_name, context)

        # Create new session
        session = RewriteSession.objects.create(
            original_text=original_text,
            context_id=context_id,
            tone_id=tone_id,
            audience=audience,
            purpose=purpose,
            session_token=secrets.token_hex(32),
        )

        # Redirect with success message (PRG pattern)
        return redirect(f'{request.path}?success=Session created successfully!')


# =============================================================================
# SECTION 6: CREATING APIs
# =============================================================================

@api_login_required
def api_sessions(request):
    """
    API endpoint to list sessions in JSON format.

    URL: /api/sessions/
    For Grading: JSON API endpoint with filtering support

    Query Parameters:
    - context: Filter by context name
    - tone: Filter by tone name
    - completed: Filter by completion status (true/false)
    - limit: Limit number of results (default: 20)
    """
    sessions = RewriteSession.objects.select_related('context', 'tone').all()

    # Apply filters from query parameters
    context_filter = request.GET.get('context', '')
    tone_filter = request.GET.get('tone', '')
    completed_filter = request.GET.get('completed', '')
    limit = request.GET.get('limit', '20')

    if context_filter:
        sessions = sessions.filter(context__name__icontains=context_filter)

    if tone_filter:
        sessions = sessions.filter(tone__name__icontains=tone_filter)

    if completed_filter:
        is_completed = completed_filter.lower() == 'true'
        sessions = sessions.filter(is_completed=is_completed)

    try:
        limit = min(int(limit), 100)  # Cap at 100
    except ValueError:
        limit = 20

    sessions = sessions[:limit]

    # Build JSON response
    data = {
        'count': len(sessions),
        'filters': {
            'context': context_filter or None,
            'tone': tone_filter or None,
            'completed': completed_filter or None,
        },
        'sessions': [
            {
                'id': s.id,
                'original_text': s.original_text[:200] + '...' if len(s.original_text) > 200 else s.original_text,
                'context': s.context.name,
                'tone': s.tone.name,
                'audience': s.audience or None,
                'purpose': s.purpose or None,
                'is_completed': s.is_completed,
                'created_at': s.created_at.isoformat(),
                'url': s.get_absolute_url(),
            }
            for s in sessions
        ]
    }

    # Return JsonResponse (automatically sets application/json content type)
    return JsonResponse(data, safe=False)


@api_login_required
def api_session_detail(request, pk):
    """
    API endpoint for a single session with results.

    URL: /api/sessions/<pk>/
    For Grading: Detail API endpoint
    """
    try:
        session = RewriteSession.objects.select_related('context', 'tone').get(pk=pk)
    except RewriteSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    results = session.results.all()

    data = {
        'id': session.id,
        'original_text': session.original_text,
        'context': {
            'id': session.context.id,
            'name': session.context.name,
            'description': session.context.description,
        },
        'tone': {
            'id': session.tone.id,
            'name': session.tone.name,
            'description': session.tone.description,
        },
        'audience': session.audience or None,
        'purpose': session.purpose or None,
        'is_completed': session.is_completed,
        'session_token': session.session_token,
        'created_at': session.created_at.isoformat(),
        'results': [
            {
                'id': r.id,
                'version_label': r.version_label,
                'rewritten_text': r.rewritten_text,
                'quality_score': r.quality_score,
                'change_summary': r.change_summary or None,
                'word_count_original': r.word_count_original,
                'word_count_rewritten': r.word_count_rewritten,
            }
            for r in results
        ]
    }

    return JsonResponse(data)


class APISessionsView(LoginRequiredMixin, View):
    """
    Class-Based API View for sessions.

    URL: /api/v2/sessions/
    For Grading: CBV API implementation
    """
    login_url = 'rewrites:login'

    def get(self, request):
        """Handle GET requests - list sessions."""
        sessions = RewriteSession.objects.select_related('context', 'tone').all()[:20]

        data = {
            'api_version': '2.0',
            'method': 'GET',
            'count': len(sessions),
            'sessions': [
                {
                    'id': s.id,
                    'original_text_preview': s.original_text[:100] + '...' if len(s.original_text) > 100 else s.original_text,
                    'context': s.context.name,
                    'tone': s.tone.name,
                    'is_completed': s.is_completed,
                }
                for s in sessions
            ]
        }

        return JsonResponse(data)


@api_login_required
def api_contexts(request):
    """
    API endpoint for listing available contexts.

    URL: /api/contexts/
    """
    contexts = RewriteContext.objects.filter(is_active=True)

    data = {
        'count': contexts.count(),
        'contexts': [
            {
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'session_count': c.sessions.count(),
            }
            for c in contexts
        ]
    }

    return JsonResponse(data)


@api_login_required
def api_tones(request):
    """
    API endpoint for listing available tones.

    URL: /api/tones/
    """
    tones = ToneOption.objects.filter(is_active=True)

    data = {
        'count': tones.count(),
        'tones': [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'intensity_level': t.intensity_level,
                'session_count': t.sessions.count(),
            }
            for t in tones
        ]
    }

    return JsonResponse(data)


@api_login_required
def demo_http_vs_json(request):
    """
    Demo view showing difference between HttpResponse and JsonResponse.

    URL: /api/demo/
    For Grading: Demonstrates HttpResponse vs JsonResponse MIME types
    """
    format_type = request.GET.get('format', 'json')

    data = {
        'message': 'This is a demo response',
        'format': format_type,
        'sessions_count': RewriteSession.objects.count(),
    }

    if format_type == 'html':
        # HttpResponse with text/html content type
        html_content = f"""
        <html>
        <head><title>HTTP Response Demo</title></head>
        <body>
        <h1>HttpResponse Demo</h1>
        <p>Message: {data['message']}</p>
        <p>Format: {data['format']}</p>
        <p>Sessions Count: {data['sessions_count']}</p>
        <p><strong>Content-Type: text/html</strong></p>
        </body>
        </html>
        """
        return HttpResponse(html_content, content_type='text/html')
    else:
        # JsonResponse with application/json content type
        data['note'] = 'Content-Type: application/json'
        return JsonResponse(data)


# =============================================================================
# A4 PART 1: INTERNAL API FOR VEGA-LITE CHARTS
# =============================================================================

def api_summary(request):
    """
    Clean internal JSON API endpoint for Vega-Lite charts.

    URL: /api/summary/
    Returns simple JSON format optimized for Vega-Lite visualization.

    Query Parameters:
    - format: 'json' (default) or 'csv'
    """
    # Get aggregated data by context
    sessions_by_context = RewriteSession.objects.values('context__name').annotate(
        count=Count('id')
    ).order_by('context__name')

    # Get aggregated data by tone
    sessions_by_tone = RewriteSession.objects.values('tone__name').annotate(
        count=Count('id')
    ).order_by('tone__name')

    # Get sessions over time (by date)
    sessions_by_date = RewriteSession.objects.extra(
        select={'date': 'date(created_at)'}
    ).values('date').annotate(count=Count('id')).order_by('date')

    # Build simple array format for Vega-Lite
    context_data = [
        {'category': item['context__name'], 'count': item['count'], 'type': 'context'}
        for item in sessions_by_context
    ]

    tone_data = [
        {'category': item['tone__name'], 'count': item['count'], 'type': 'tone'}
        for item in sessions_by_tone
    ]

    date_data = [
        {'date': str(item['date']), 'count': item['count']}
        for item in sessions_by_date
    ]

    format_type = request.GET.get('format', 'json')

    if format_type == 'csv':
        # Return CSV format
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="summary.csv"'

        writer = csv.writer(response)
        writer.writerow(['category', 'count', 'type'])
        for item in context_data + tone_data:
            writer.writerow([item['category'], item['count'], item['type']])

        return response

    # Return JSON (default) - simple array format for Vega-Lite
    data = {
        'by_context': context_data,
        'by_tone': tone_data,
        'by_date': date_data,
        'totals': {
            'sessions': RewriteSession.objects.count(),
            'results': RewriteResult.objects.count(),
            'contexts': RewriteContext.objects.count(),
            'tones': ToneOption.objects.count(),
        }
    }

    response = JsonResponse(data)
    response['Access-Control-Allow-Origin'] = '*'
    return response


def api_public_context_stats(request):
    """
    PUBLIC API endpoint - returns sessions by context as a flat JSON array.

    This endpoint does NOT require authentication and includes CORS headers
    so it can be consumed by external tools (Vega-Lite editor, Python scripts, etc.).

    URL: /api/public/context-stats/
    Returns: [{"context": "...", "sessions": N}, ...]
    """
    data = RewriteSession.objects.values('context__name').annotate(
        count=Count('id')
    ).order_by('-count')

    result = [
        {'context': item['context__name'], 'sessions': item['count']}
        for item in data
    ]

    response = JsonResponse(result, safe=False)
    response['Access-Control-Allow-Origin'] = '*'
    return response


@api_login_required
def api_chart_data_context(request):
    """
    Simple JSON array endpoint for Vega-Lite bar chart (sessions by context).

    URL: /api/chart/context/
    Returns: Simple array format ideal for Vega-Lite
    """
    data = RewriteSession.objects.values('context__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # Simple array format for Vega-Lite
    result = [
        {'context': item['context__name'], 'sessions': item['count']}
        for item in data
    ]

    return JsonResponse(result, safe=False)


@api_login_required
def api_chart_data_timeline(request):
    """
    Simple JSON array endpoint for Vega-Lite line/scatter chart (sessions over time).

    URL: /api/chart/timeline/
    Returns: Simple array format with date and count
    """
    # Get sessions grouped by creation date
    data = RewriteSession.objects.extra(
        select={'date': 'date(created_at)'}
    ).values('date').annotate(count=Count('id')).order_by('date')

    # Simple array format for Vega-Lite
    result = [
        {'date': str(item['date']), 'sessions': item['count']}
        for item in data
    ]

    return JsonResponse(result, safe=False)


@api_login_required
def api_chart_data_quality(request):
    """
    Simple JSON array endpoint for results by quality.

    URL: /api/chart/quality/
    """
    data = RewriteResult.objects.values('quality_score').annotate(
        count=Count('id')
    ).order_by('quality_score')

    result = [
        {'quality': item['quality_score'], 'count': item['count']}
        for item in data
    ]

    return JsonResponse(result, safe=False)


# =============================================================================
# A4 PART 1.2: VEGA-LITE CHART PAGES
# =============================================================================

@login_required(login_url='rewrites:login')
def vegalite_charts(request):
    """
    Page displaying Vega-Lite charts embedded in HTML.

    URL: /vega-lite/
    """
    # Build the API URL based on the request
    api_base = request.build_absolute_uri('/api/chart/')

    context = {
        'title': 'Vega-Lite Charts',
        'api_context_url': request.build_absolute_uri('/api/chart/context/'),
        'api_timeline_url': request.build_absolute_uri('/api/chart/timeline/'),
    }
    return render(request, 'rewrites/vegalite_charts.html', context)


# =============================================================================
# A4 PART 2: EXTERNAL API INTEGRATION
# =============================================================================

@login_required(login_url='rewrites:login')
def external_api_quotes(request):
    """
    External API integration - Fetches quotes/advice to combine with our data.
    Uses the ZenQuotes API (https://zenquotes.io) - no API key required.

    URL: /external/quotes/
    Query params: ?q=keyword (for display purposes, API returns random quotes)
    """
    query = request.GET.get('q', 'inspiration')

    try:
        # Call external API with timeout and error handling
        response = requests.get(
            'https://zenquotes.io/api/quotes',
            timeout=5
        )
        response.raise_for_status()

        external_data = response.json()
        # ZenQuotes returns list of quotes with 'q' (quote) and 'a' (author)
        quotes = [
            {'content': q['q'], 'author': q['a']}
            for q in external_data[:5]  # Limit to 5 quotes
        ]

    except requests.exceptions.Timeout:
        quotes = []
        error_message = 'External API timed out'
    except requests.exceptions.RequestException as e:
        quotes = []
        error_message = f'External API error: {str(e)}'
    else:
        error_message = None

    # Combine with internal data - get related sessions based on tone
    # This demonstrates triangulating external + internal data
    internal_sessions = RewriteSession.objects.select_related('context', 'tone').all()[:5]

    context = {
        'title': 'Writing Inspiration',
        'query': query,
        'quotes': quotes,
        'error_message': error_message,
        'sessions': internal_sessions,
        'session_count': RewriteSession.objects.count(),
    }

    return render(request, 'rewrites/external_quotes.html', context)


@api_login_required
def api_external_quotes(request):
    """
    API endpoint that combines external API data with internal analytics.

    URL: /api/external/quotes/
    Query params: ?q=keyword
    """
    query = request.GET.get('q', 'inspiration')

    try:
        response = requests.get(
            'https://zenquotes.io/api/quotes',
            timeout=5
        )
        response.raise_for_status()
        external_data = response.json()
        quotes = [
            {'content': q['q'], 'author': q['a']}
            for q in external_data[:3]  # Limit to 3 quotes
        ]
        error = None
    except requests.exceptions.RequestException as e:
        quotes = []
        error = str(e)

    # Combine with internal aggregation
    internal_stats = {
        'total_sessions': RewriteSession.objects.count(),
        'completed_sessions': RewriteSession.objects.filter(is_completed=True).count(),
        'contexts': list(RewriteContext.objects.values_list('name', flat=True)),
    }

    data = {
        'query': query,
        'external_quotes': quotes,
        'internal_stats': internal_stats,
        'error': error,
        'generated_at': timezone.now().isoformat(),
    }

    return JsonResponse(data)


# =============================================================================
# A4 PART 3: CSV AND JSON EXPORTS
# =============================================================================

@login_required(login_url='rewrites:login')
def export_sessions_csv(request):
    """
    Export all sessions as a downloadable CSV file.

    URL: /export/sessions/csv/
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f'sessions_{timestamp}.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Header row
    writer.writerow([
        'ID', 'Original Text', 'Context', 'Tone', 'Audience',
        'Purpose', 'Completed', 'Created At'
    ])

    # Data rows
    sessions = RewriteSession.objects.select_related('context', 'tone').order_by('-created_at')
    for session in sessions:
        writer.writerow([
            session.id,
            session.original_text[:200],  # Truncate for readability
            session.context.name,
            session.tone.name,
            session.audience or '',
            session.purpose or '',
            'Yes' if session.is_completed else 'No',
            session.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


@login_required(login_url='rewrites:login')
def export_sessions_json(request):
    """
    Export all sessions as a downloadable JSON file with metadata.

    URL: /export/sessions/json/
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f'sessions_{timestamp}.json'

    sessions = RewriteSession.objects.select_related('context', 'tone').order_by('-created_at')

    data = {
        'generated_at': timezone.now().isoformat(),
        'record_count': sessions.count(),
        'sessions': [
            {
                'id': s.id,
                'original_text': s.original_text,
                'context': s.context.name,
                'tone': s.tone.name,
                'audience': s.audience or None,
                'purpose': s.purpose or None,
                'is_completed': s.is_completed,
                'created_at': s.created_at.isoformat(),
            }
            for s in sessions
        ]
    }

    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@login_required(login_url='rewrites:login')
def export_results_csv(request):
    """
    Export all rewrite results as CSV.

    URL: /export/results/csv/
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f'results_{timestamp}.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Session ID', 'Version', 'Rewritten Text', 'Quality Score',
        'Word Count Original', 'Word Count Rewritten', 'Created At'
    ])

    results = RewriteResult.objects.select_related('session').order_by('-created_at')
    for result in results:
        writer.writerow([
            result.id,
            result.session.id,
            result.version_label,
            result.rewritten_text[:200],
            result.quality_score,
            result.word_count_original,
            result.word_count_rewritten,
            result.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


@login_required(login_url='rewrites:login')
def export_results_json(request):
    """
    Export all rewrite results as JSON with metadata.

    URL: /export/results/json/
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f'results_{timestamp}.json'

    results = RewriteResult.objects.select_related('session').order_by('-created_at')

    data = {
        'generated_at': timezone.now().isoformat(),
        'record_count': results.count(),
        'results': [
            {
                'id': r.id,
                'session_id': r.session.id,
                'version_label': r.version_label,
                'rewritten_text': r.rewritten_text,
                'quality_score': r.quality_score,
                'change_summary': r.change_summary or None,
                'word_count_original': r.word_count_original,
                'word_count_rewritten': r.word_count_rewritten,
                'created_at': r.created_at.isoformat(),
            }
            for r in results
        ]
    }

    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


# =============================================================================
# A4 PART 3: REPORTS PAGE
# =============================================================================

@login_required(login_url='rewrites:login')
def reports(request):
    """
    Reports page with grouped summaries, totals, and export links.

    URL: /reports/
    """
    # Sessions grouped by context
    sessions_by_context = RewriteSession.objects.values('context__name').annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(is_completed=True)),
        pending=Count('id', filter=Q(is_completed=False)),
    ).order_by('-total')

    # Sessions grouped by tone
    sessions_by_tone = RewriteSession.objects.values('tone__name').annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(is_completed=True)),
    ).order_by('-total')

    # Results grouped by quality
    results_by_quality = RewriteResult.objects.values('quality_score').annotate(
        count=Count('id'),
        avg_word_change=Avg('word_count_rewritten') - Avg('word_count_original'),
    ).order_by('quality_score')

    # Totals
    total_sessions = RewriteSession.objects.count()
    total_completed = RewriteSession.objects.filter(is_completed=True).count()
    total_results = RewriteResult.objects.count()
    total_contexts = RewriteContext.objects.count()
    total_tones = ToneOption.objects.count()

    context = {
        'title': 'Reports & Exports',
        'sessions_by_context': sessions_by_context,
        'sessions_by_tone': sessions_by_tone,
        'results_by_quality': results_by_quality,
        'total_sessions': total_sessions,
        'total_completed': total_completed,
        'total_results': total_results,
        'total_contexts': total_contexts,
        'total_tones': total_tones,
    }

    return render(request, 'rewrites/reports.html', context)


# =============================================================================
# GENERATE REWRITES (LLM)
# =============================================================================

@require_POST
def generate_rewrites(request, pk):
    """
    Trigger LLM-based rewrite generation for a session.

    POST /sessions/<pk>/generate/
    On success -> redirect to session detail with results visible.
    On failure -> redirect with a friendly error message.
    """
    session = get_object_or_404(RewriteSession, pk=pk)

    try:
        from .services.llm_rewrite import generate_rewrites_for_session
        results = generate_rewrites_for_session(session)
        django_messages.success(
            request,
            f"Generated {len(results)} rewrites successfully!",
        )
    except ValueError as exc:
        # Missing API key or bad response format
        django_messages.error(request, f"Rewrite generation failed: {exc}")
    except Exception as exc:
        django_messages.error(
            request,
            f"An unexpected error occurred: {exc}",
        )

    return redirect('rewrites:session_detail', pk=session.pk)


# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================

def user_login(request):
    """Login view. Redirects to dashboard on success."""
    if request.user.is_authenticated:
        return redirect('rewrites:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            django_messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next', 'rewrites:dashboard')
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'rewrites/login.html', {
        'form': form,
        'title': 'Log In',
    })


def user_register(request):
    """Registration view. Logs in user automatically after registration."""
    if request.user.is_authenticated:
        return redirect('rewrites:dashboard')

    from .forms import UserRegisterForm

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            django_messages.success(
                request,
                f'Account created! Welcome to RewriteLab, {user.username}.',
            )
            return redirect('rewrites:dashboard')
    else:
        form = UserRegisterForm()

    return render(request, 'rewrites/register.html', {
        'form': form,
        'title': 'Register',
    })


def user_logout(request):
    """Logout view. Redirects to home."""
    logout(request)
    django_messages.success(request, 'You have been logged out.')
    return redirect('rewrites:home')


# =============================================================================
# USER DASHBOARD
# =============================================================================

@login_required(login_url='rewrites:login')
def dashboard(request):
    """
    User dashboard showing their sessions and stats.

    URL: /dashboard/
    """
    sessions = RewriteSession.objects.filter(
        user=request.user
    ).select_related('context', 'tone').order_by('-created_at')

    total = sessions.count()
    completed = sessions.filter(is_completed=True).count()
    pending = total - completed
    total_rewrites = RewriteResult.objects.filter(session__user=request.user).count()

    return render(request, 'rewrites/dashboard.html', {
        'title': 'Dashboard',
        'sessions': sessions,
        'total_sessions': total,
        'completed_sessions': completed,
        'pending_sessions': pending,
        'total_rewrites': total_rewrites,
    })


# =============================================================================
# SESSION CRUD (Create, Edit, Delete)
# =============================================================================

@login_required(login_url='rewrites:login')
def session_create(request):
    """
    Create a new RewriteSession.

    POST: validate form, generate session_token, save, redirect to detail.
    GET: show empty form.
    """
    import secrets
    from .forms import SessionCreateForm

    if request.method == 'POST':
        form = SessionCreateForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.session_token = secrets.token_hex(32)
            try:
                session.save()
                django_messages.success(request, 'Session created! You can now generate rewrites.')
                return redirect('rewrites:session_detail', pk=session.pk)
            except Exception:
                django_messages.error(
                    request,
                    'A session with this exact text, context, and tone already exists.',
                )
    else:
        form = SessionCreateForm()

    return render(request, 'rewrites/session_create.html', {
        'form': form,
        'title': 'New Session',
    })


@login_required(login_url='rewrites:login')
def session_edit(request, pk):
    """
    Edit an existing RewriteSession.

    Only the session owner can edit.
    If context or tone changes, clear existing results and reset completion.
    """
    from .forms import SessionCreateForm

    session = get_object_or_404(RewriteSession, pk=pk)

    # Ownership check
    if session.user and session.user != request.user:
        django_messages.error(request, 'You do not have permission to edit this session.')
        return redirect('rewrites:session_detail', pk=pk)

    old_context = session.context_id
    old_tone = session.tone_id

    if request.method == 'POST':
        form = SessionCreateForm(request.POST, instance=session)
        if form.is_valid():
            updated = form.save(commit=False)
            # If context or tone changed, reset completion and delete results
            if updated.context_id != old_context or updated.tone_id != old_tone:
                updated.is_completed = False
                updated.save()
                updated.results.all().delete()
                django_messages.info(
                    request,
                    'Context or tone changed — previous rewrites cleared. Generate new ones.',
                )
            else:
                updated.save()
                django_messages.success(request, 'Session updated.')
            return redirect('rewrites:session_detail', pk=session.pk)
    else:
        form = SessionCreateForm(instance=session)

    return render(request, 'rewrites/session_edit.html', {
        'form': form,
        'session': session,
        'title': 'Edit Session',
    })


@login_required(login_url='rewrites:login')
def session_delete(request, pk):
    """
    Delete a RewriteSession.

    GET: show confirmation page.
    POST: delete and redirect to dashboard.
    Only the session owner can delete.
    """
    session = get_object_or_404(RewriteSession, pk=pk)

    # Ownership check
    if session.user and session.user != request.user:
        django_messages.error(request, 'You do not have permission to delete this session.')
        return redirect('rewrites:session_detail', pk=pk)

    if request.method == 'POST':
        session.delete()
        django_messages.success(request, 'Session deleted.')
        return redirect('rewrites:dashboard')

    return render(request, 'rewrites/session_delete.html', {
        'session': session,
        'title': 'Delete Session',
    })


# =============================================================================
# CUSTOM CONTEXT AND TONE CREATION
# =============================================================================

@login_required(login_url='rewrites:login')
def context_create(request):
    """
    Create a new custom RewriteContext.

    POST: validate form, save, redirect back to session create.
    GET: show form.
    """
    from .forms import ContextCreateForm

    if request.method == 'POST':
        form = ContextCreateForm(request.POST)
        if form.is_valid():
            context = form.save(commit=False)
            context.is_active = True
            context.save()
            django_messages.success(request, f'Context "{context.name}" created successfully!')
            return redirect('rewrites:session_create')
    else:
        form = ContextCreateForm()

    return render(request, 'rewrites/context_create.html', {
        'form': form,
        'title': 'Add Writing Context',
    })


@login_required(login_url='rewrites:login')
def tone_create(request):
    """
    Create a new custom ToneOption.

    POST: validate form, save, redirect back to session create.
    GET: show form.
    """
    from .forms import ToneCreateForm

    if request.method == 'POST':
        form = ToneCreateForm(request.POST)
        if form.is_valid():
            tone = form.save(commit=False)
            tone.is_active = True
            tone.intensity_level = 5  # Default intensity
            tone.save()
            django_messages.success(request, f'Tone "{tone.name}" created successfully!')
            return redirect('rewrites:session_create')
    else:
        form = ToneCreateForm()

    return render(request, 'rewrites/tone_create.html', {
        'form': form,
        'title': 'Add Tone Option',
    })

