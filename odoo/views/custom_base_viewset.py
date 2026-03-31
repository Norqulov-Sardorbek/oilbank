from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

class OdooBaseViewSet(viewsets.ModelViewSet):


    def create(self, request, *args, **kwargs):
        print(f"\n\n\n\n\n\n\n Incoming Create data from {self.__class__.__name__}", request.data)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        print(f"\n\n\n\n\n\n\n Incoming Update data from {self.__class__.__name__}", request.data)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        print(f"\n\n\n\n\n\n\n Incoming Delete data from {self.__class__.__name__}", request.data)
        instance = self.get_object()
        instance.delete(skip_odoo=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

