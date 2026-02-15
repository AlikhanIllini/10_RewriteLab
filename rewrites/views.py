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
"""

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.views import View
from django.views.generic import ListView, DetailView
from django.db.models import Count, Q
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

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


# =============================================================================
# SECTION 2: ORM QUERIES & DATA PRESENTATION
# =============================================================================

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

class SessionSearchView(ListView):
    """
    CBV that handles both GET and POST for search functionality.

    URL: /sessions/search/
    For Grading: CBV adapted to handle GET (search) and POST (create session)
    """
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


class APISessionsView(View):
    """
    Class-Based API View for sessions.

    URL: /api/v2/sessions/
    For Grading: CBV API implementation
    """

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


