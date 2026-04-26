"""
URL configuration for invoice_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings  # noqa: I001
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from invoice_app.api.jwt_auth import CustomTokenObtainPairView
from invoice_app.monitoring.views import metrics_with_business_kpis
from invoice_app.views import health_check, health_detailed, readiness_check
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Health check endpoints (public, no authentication required)
    path("health/", health_check, name="health_check"),
    path("health/detailed/", health_detailed, name="health_detailed"),
    path("health/readiness/", readiness_check, name="readiness_check"),
    # Prometheus metrics endpoint — collects Business KPIs from DB on each scrape
    path("metrics", metrics_with_business_kpis, name="prometheus-django-metrics"),
    # Admin interface
    path("admin/", admin.site.urls),
    # Custom admin action for PDF generation
    path("admin/invoice/<int:pk>/generate_pdf/", include("invoice_app.admin_urls")),
    # JWT Authentication endpoints
    path("api/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Session-based login/logout für Template-Views (LoginRequiredMixin, Vorschau)
    path("accounts/", include("django.contrib.auth.urls")),
    # Direct include of invoice_app.urls for the root path to ensure home view works properly
    path("", include("invoice_app.urls")),  # Form-based app URLs at root level
    path("api-auth/", include("rest_framework.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="schema-swagger-ui"),
    path("api/", include("invoice_app.api.urls")),  # API URLs with explicit prefix
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
