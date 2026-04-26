"""Custom pagination classes for the eRechnung API."""

from rest_framework.pagination import PageNumberPagination


class FlexiblePageNumberPagination(PageNumberPagination):
    """PageNumberPagination that allows the client to override page_size.

    The client can pass ``?page_size=<n>`` (up to *max_page_size*) to fetch
    more results per page – useful for dropdown / select-all scenarios where
    the default of 10 is too small.
    """

    page_size_query_param = "page_size"
    max_page_size = 1000
