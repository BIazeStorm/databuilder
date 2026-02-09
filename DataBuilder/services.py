from django.db.models import Sum, Count, DecimalField, F
from django.db.models.functions import (
    TruncDay, TruncMonth, TruncYear, TruncQuarter, ExtractHour,
    ExtractWeekDay, ExtractMonth, ExtractQuarter, NullIf, Cast
)
import pandas as pd
import numpy as np
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

    SUFFIXES = ['_prev', '_diff', '_diff_percent']

    def __init__(self, dimensions: list, metrics: list):
        self.requested_dimensions = dimensions
        self.requested_metrics = metrics

        self.base_metrics = set()
        for m in self.requested_metrics:
            if m in self.METRIC_MAPPING:
                self.base_metrics.add(m)
                continue

            for suffix in self.SUFFIXES:
                if m.endswith(suffix):
                    base_name = m[:-len(suffix)]
                    if base_name in self.METRIC_MAPPING:
                        self.base_metrics.add(base_name)
                    break

        self.db_group_kwargs = {
            m: self.DIMENSION_MAPPING[m]
            for m in self.requested_dimensions
            if m in self.DIMENSION_MAPPING
        }

        self.db_aggregates = {
            m: self.METRIC_MAPPING[m]
            for m in self.base_metrics
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

    def get_comparison_dataframe(self, current_range, prev_range):
        df_curr = self.get_dataframe(current_range['from_date'], current_range['to_date'])
        df_prev = self.get_dataframe(prev_range['from_date'], prev_range['to_date'])

        merge_on = list(self.db_group_kwargs.keys())

        rename_map = {m: f"{m}_prev" for m in self.base_metrics}
        df_prev = df_prev.rename(columns=rename_map)

        df_merged = pd.merge(
            df_curr,
            df_prev,
            on=merge_on,
            how="outer",
        )

        df_merged = df_merged.fillna(0)
        requested_set = set(self.requested_metrics)

        for base in self.base_metrics:
            curr_col = base
            prev_col = f"{base}_prev"

            diff_col = f"{base}_diff"
            if diff_col in requested_set:
                df_merged[diff_col] = df_merged[curr_col] - df_merged[prev_col]
                df_merged[diff_col] = df_merged[diff_col].round(2)

            pct_col = f"{base}_diff_percent"
            if pct_col in requested_set:
                if diff_col in df_merged.columns:
                    diff_values = df_merged[diff_col]
                else:
                    diff_values = df_merged[curr_col] - df_merged[prev_col]

                with np.errstate(divide='ignore', invalid='ignore'):
                    pct_values = (diff_values / df_merged[prev_col]) * 100

                pct_values = np.nan_to_num(pct_values, posinf=100.0, neginf=-100.0, nan=0.0)
                df_merged[pct_col] = pct_values.round(2)

        df_merged = df_merged.fillna(0)

        final_columns = self.requested_dimensions + self.requested_metrics

        available_columns = [c for c in final_columns if c in df_merged.columns]

        return df_merged[available_columns]
