# hrbot/urls.py
from django.urls import path
from .views import analyze_message_view

urlpatterns = [
    path("analyze/", analyze_message_view, name="analyze-message"),
]
