from rest_framework import viewsets, filters as drf_filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum
import pandas as pd


from .models import Brand, Shop, Product, CartItem
from .serializers import BrandSerializer, ShopSerializer, ProductSerializer, AnalyticsRequestSerializer
from .filtersets import ProductFilter


class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter, drf_filters.SearchFilter]


class BrandViewSet(BaseViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class ShopViewSet(BaseViewSet):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class ProductViewSet(BaseViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'brand_id']


class AnalyticsViewSet(BaseViewSet):

    @action(detail=False, methods=['post'], url_path='get-analytics')
    def get_analytics(self, request):
        serializer = AnalyticsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        params = serializer.validated_data
        metrics = params['metrics']
        dimensions = params['group_by']
        date_range = params['date_range']

        dimension_mapping = {
            'product': 'product__name',
            'brand': 'product__brand__name',
            'shop': 'receipt__shop__name',
        }

        metric_mapping = {
            'turnover': Sum('total_price'),
            'profit': Sum('margin_price_total'),
        }


        db_group_fields = [
            dimension_mapping[d] for d in dimensions
            if d in dimension_mapping
        ]

        db_aggregates = {
            m: metric_mapping[m] for m in metrics
            if m in metric_mapping
        }

        if not db_group_fields or not db_aggregates:
            return Response({"error": "Invalid dimensions or metrics"}, status=status.HTTP_400_BAD_REQUEST)


        queryset = CartItem.objects.all().filter(
            datetime__gte=date_range['from'],
            datetime__lte=date_range['to'],
        ).values(*db_group_fields).annotate(**db_aggregates)


        df = pd.DataFrame(list(queryset))

        if df.empty:
            return Response([])

        reverse_mapping = {v: k for k, v in dimension_mapping.items()}
        df.rename(columns=reverse_mapping, inplace=True)

        result = df.to_dict(orient='records')

        return Response(result)