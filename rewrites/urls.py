"""
URL configuration for the rewrites app.

All routes use name= for reverse URL lookup.
"""

from django.urls import path
from . import views

app_name = 'rewrites'

urlpatterns = [
    # ==========================================================================
    # HOME & NAVIGATION (Section 1)
    # ==========================================================================
    path('', views.home, name='home'),

    # ==========================================================================
    # DEMO VIEWS (Previous Assignment)
    # ==========================================================================
    path('manual/', views.session_manual, name='session_manual'),  # HttpResponse FBV
    path('render/', views.session_list_render, name='session_render'),  # render() FBV
    path('cbv-base/', views.SessionBaseView.as_view(), name='session_cbv_base'),  # Base CBV
    path('cbv-generic/', views.SessionListView.as_view(), name='session_cbv_generic'),  # Generic CBV

    # ==========================================================================
    # DETAIL VIEW with PK (Section 1)
    # ==========================================================================
    path('sessions/<int:pk>/', views.SessionDetailView.as_view(), name='session_detail'),

    # ==========================================================================
    # SEARCH & FILTERING (Section 2 + Section 5)
    # ==========================================================================
    path('search/', views.search, name='search'),  # GET & POST search
    path('sessions/search/', views.SessionSearchView.as_view(), name='session_search'),  # CBV with GET/POST

    # ==========================================================================
    # ANALYTICS & CHARTS (Section 4 - Matplotlib)
    # ==========================================================================
    path('analytics/', views.analytics, name='analytics'),
    path('charts/sessions-by-context.png', views.chart_sessions_by_context, name='chart_context'),
    path('charts/sessions-by-tone.png', views.chart_sessions_by_tone, name='chart_tone'),
    path('charts/results-quality.png', views.chart_results_quality, name='chart_quality'),

    # ==========================================================================
    # API ENDPOINTS (Section 6)
    # ==========================================================================
    path('api/sessions/', views.api_sessions, name='api_sessions'),  # FBV API
    path('api/sessions/<int:pk>/', views.api_session_detail, name='api_session_detail'),
    path('api/v2/sessions/', views.APISessionsView.as_view(), name='api_sessions_v2'),  # CBV API
    path('api/contexts/', views.api_contexts, name='api_contexts'),
    path('api/tones/', views.api_tones, name='api_tones'),
    path('api/demo/', views.demo_http_vs_json, name='api_demo'),  # HttpResponse vs JsonResponse demo

    # ==========================================================================
    # A4 PART 1: INTERNAL API FOR VEGA-LITE CHARTS
    # ==========================================================================
    path('api/summary/', views.api_summary, name='api_summary'),  # Clean summary endpoint
    path('api/chart/context/', views.api_chart_data_context, name='api_chart_context'),  # Bar chart data
    path('api/chart/timeline/', views.api_chart_data_timeline, name='api_chart_timeline'),  # Line chart data
    path('api/chart/quality/', views.api_chart_data_quality, name='api_chart_quality'),  # Quality data

    # ==========================================================================
    # A4 PART 1.2: VEGA-LITE CHARTS PAGE
    # ==========================================================================
    path('vega-lite/', views.vegalite_charts, name='vegalite_charts'),

    # ==========================================================================
    # A4 PART 2: EXTERNAL API INTEGRATION
    # ==========================================================================
    path('external/quotes/', views.external_api_quotes, name='external_quotes'),  # HTML page
    path('api/external/quotes/', views.api_external_quotes, name='api_external_quotes'),  # JSON API

    # ==========================================================================
    # A4 PART 3: EXPORTS (CSV & JSON)
    # ==========================================================================
    path('export/sessions/csv/', views.export_sessions_csv, name='export_sessions_csv'),
    path('export/sessions/json/', views.export_sessions_json, name='export_sessions_json'),
    path('export/results/csv/', views.export_results_csv, name='export_results_csv'),
    path('export/results/json/', views.export_results_json, name='export_results_json'),

    # ==========================================================================
    # A4 PART 3: REPORTS PAGE
    # ==========================================================================
    path('reports/', views.reports, name='reports'),
]
