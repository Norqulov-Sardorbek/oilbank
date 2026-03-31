from rest_framework.pagination import (
    LimitOffsetPagination,
    NotFound,
)
from rest_framework import status
from rest_framework.response import Response


class DefaultLimitOffSetPagination(LimitOffsetPagination):
    default_limit = 10

    def generate_response(self, query_set, serializer_obj, request):
        try:
            page_data = self.paginate_queryset(query_set, request)
        except NotFound:
            return Response(
                {"error": "No result was found for the requested page!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serialized_page = serializer_obj(
            page_data, many=True, context={"request": self.request}
        )
        return self.get_paginated_response(serialized_page.data)
