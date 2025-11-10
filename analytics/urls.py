from django.urls import path, include
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, analytics_dashboard, trigger_analysis, home

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', home, name='home'),  
    path('api/', include(router.urls)),
    path('analyse/', trigger_analysis, name='trigger-analysis'),
    path('dashboard/', analytics_dashboard, name='dashboard'),
    # Add alias for conversation list - redirects to API endpoint
    path('conversations/', lambda request: redirect('/api/conversations/'), name='conversation-list'),
]
