"""
GDPdU / IDEA export API view.

See ``invoice_app.services.gdpdu_export_service`` for format details.
"""

from __future__ import annotations

from datetime import date, datetime

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from invoice_app.models import AuditLog
from invoice_app.services.gdpdu_export_service import export_period


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


class GDPdUExportView(APIView):
    """
    GDPdU/IDEA export of invoices for tax audits (§147 AO, GoBD).

    GET /api/gdpdu/export/?start=YYYY-MM-DD&end=YYYY-MM-DD
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        description=(
            "GDPdU/IDEA-Export der Rechnungen im angegebenen Zeitraum als ZIP "
            "(index.xml + CSV-Tabellen). Nur für Administratoren."
        ),
        parameters=[
            OpenApiParameter(
                name="start",
                description="Startdatum (inklusive), Format YYYY-MM-DD",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name="end",
                description="Enddatum (inklusive), Format YYYY-MM-DD",
                required=True,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(description="ZIP archive (application/zip)"),
            400: OpenApiResponse(description="Invalid query parameters"),
        },
    )
    def get(self, request):
        start = _parse_iso_date(request.query_params.get("start"))
        end = _parse_iso_date(request.query_params.get("end"))
        if start is None or end is None:
            return Response(
                {"detail": "Parameter 'start' and 'end' (YYYY-MM-DD) are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if start > end:
            return Response(
                {"detail": "'start' must be on or before 'end'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        archive = export_period(start, end)

        AuditLog.log_action(
            action=AuditLog.ActionType.EXPORT,
            user=request.user,
            request=request,
            description="GDPdU-Export erstellt",
            details={
                "start": start.isoformat(),
                "end": end.isoformat(),
                "size_bytes": len(archive),
            },
            severity=AuditLog.Severity.MEDIUM,
        )

        filename = f"gdpdu-export_{start.isoformat()}_{end.isoformat()}.zip"
        response = HttpResponse(archive, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = str(len(archive))
        return response
