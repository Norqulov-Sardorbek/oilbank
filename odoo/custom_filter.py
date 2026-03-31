from django.db.models import Q
from django_filters import rest_framework as filters


class OdooIDFilterSet(filters.FilterSet):
    odoo_id = filters.CharFilter(field_name="odoo_id", lookup_expr="exact")
    status = filters.CharFilter(field_name="sync_status", lookup_expr="exact")

    has_odoo_id = filters.BooleanFilter(
        method="filter_has_odoo_id", label="Has Odoo ID"
    )

    def filter_has_odoo_id(self, queryset, name, value):
        if value:
            return queryset.exclude(odoo_id__isnull=True).exclude(odoo_id="")
        return queryset.filter(Q(odoo_id__isnull=True) | Q(odoo_id=""))

    class Meta:
        fields = ["odoo_id", "status"]
