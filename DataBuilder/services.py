from django.db.models import Sum
import pandas as pd
from .models import CartItem


class AnalyticsService:

    DIMENSION_MAPPING = {
        'product': 'product__name',
        'brand': 'product__brand__name',
        'shop': 'receipt__shop__name',
    }

    METRIC_MAPPING = {
        'turnover': Sum('total_price'),
        'profit': Sum('margin_price_total'),
    }


    def __init__(self, dimensions: list, metrics: list):
        self.dimensions = dimensions
        self.metrics = metrics

        self.db_group_fields = [
            self.DIMENSION_MAPPING[d] for d in self.dimensions
            if d in self.DIMENSION_MAPPING
        ]

        self.db_aggregates = {
            m: self.METRIC_MAPPING[m] for m in self.metrics
            if m in self.METRIC_MAPPING
        }


    def get_dataframe(self, date_from, date_to):

        queryset = CartItem.objects.filter(
            datetime__gte=date_from,
            datetime__lte=date_to,
        ).values(*self.db_group_fields).annotate(**self.db_aggregates)

        df = pd.DataFrame(list(queryset))

        reverse_mapping = {
            v: k for k, v in self.DIMENSION_MAPPING.items()
            if k in self.dimensions
        }
        df.rename(columns=reverse_mapping, inplace=True)

        return df