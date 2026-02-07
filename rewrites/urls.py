"""
URL configuration for the rewrites app.

All routes use name= for reverse URL lookup.
"""

from django.urls import path
from . import views

app_name = 'rewrites'

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Function-Based Views
    path('manual/', views.session_manual, name='session_manual'),  # HttpResponse FBV
    path('render/', views.session_list_render, name='session_render'),  # render() FBV

    # Class-Based Views
    path('cbv-base/', views.SessionBaseView.as_view(), name='session_cbv_base'),  # Base CBV
    path('cbv-generic/', views.SessionListView.as_view(), name='session_cbv_generic'),  # Generic CBV

    # Detail View (bonus)
    path('<int:pk>/', views.SessionDetailView.as_view(), name='session_detail'),
]
