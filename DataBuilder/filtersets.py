from django_filters import rest_framework as filters
from .models import Product


class ProductFilter(filters.FilterSet):
    brand_search = filters.CharFilter(field_name="brand", lookup_expr="exact")

    class Meta:
        model = Product
        fields = ["brand_id", "name"]
