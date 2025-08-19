# controller_reports/urls.py
from django.urls import path
from .views import ReportView

urlpatterns = [
    path("<slug:slug>/", ReportView.as_view(), name="report"),
]