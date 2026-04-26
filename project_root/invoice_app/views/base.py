"""Base views and utility functions."""

from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Display a home page with links to various parts of the app."""

    template_name = "invoice_app/home.html"
