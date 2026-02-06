from django.db.models import Sum, Count, DecimalField, F
from django.db.models.functions import (
    TruncDay, TruncMonth, TruncYear, TruncQuarter, ExtractHour,
    ExtractWeekDay, ExtractMonth, ExtractQuarter, NullIf, Cast
)
import pandas as pd
from .models import CartItem


class AnalyticsService:
    DIMENSION_MAPPING = {
        'product_name': F('product__name'),
        'brand_name': F('product__brand__name'),
        'shop_name': F('receipt__shop__name'),
        'day_month_year': TruncDay('datetime'),
        'day_of_week': ExtractWeekDay('datetime'),
        'month': ExtractMonth('datetime'),
        'month_year': TruncMonth('datetime'),
        'quarter': ExtractQuarter('datetime'),
        'quarter_year': TruncQuarter('datetime'),
        'year': TruncYear('datetime'),
        'hour': ExtractHour('datetime'),
    }

    _turnover = Sum('total_price')
    _profit = Sum('margin_price_total')
    _qty = Sum("qty")

    _checks_count = Count('receipt_id', distinct=True)
    _checks_count_safe = NullIf(Count('receipt_id', distinct=True), 0)
    _sales_qty_safe = NullIf(Sum('qty'), 0)

    METRIC_MAPPING = {
        'turnover': _turnover,
        'profit': _profit,
        'sales_qty': _qty,
        'checks_count': _checks_count,
        'avg_check': Cast(
            _turnover / _checks_count_safe,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        'avg_price': Cast(
            _turnover / _sales_qty_safe,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        'avg_cost': Cast(
            (_turnover - _profit) / _sales_qty_safe,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        'unique_products_sold': Count('product_id', distinct=True),
    }

    def __init__(self, dimensions: list, metrics: list):
        self.dimensions = dimensions
        self.metrics = metrics

        self.db_group_kwargs = {
            m: self.DIMENSION_MAPPING[m]
            for m in self.dimensions
            if m in self.DIMENSION_MAPPING
        }

        self.db_aggregates = {
            m: self.METRIC_MAPPING[m]
            for m in self.metrics
            if m in self.METRIC_MAPPING
        }

    def get_dataframe(self, date_from, date_to):
        queryset = CartItem.objects.filter(
            datetime__gte=date_from,
            datetime__lte=date_to,
        )

        queryset = queryset.annotate(**self.db_group_kwargs)

        if 'brand_name' in self.db_group_kwargs:
            queryset = queryset.exclude(brand_name__isnull=True).exclude(brand_name__exact='')

        queryset = queryset.values(
            *list(self.db_group_kwargs.keys())
        ).annotate(
            **self.db_aggregates
        )

        df = pd.DataFrame(list(queryset))

        return df
