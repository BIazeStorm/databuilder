import datetime
from typing import TypedDict

from django.db.models import Sum, Count, DecimalField, F, Expression, QuerySet
from django.db.models.functions import (
    TruncDay,
    TruncMonth,
    TruncYear,
    TruncQuarter,
    ExtractHour,
    ExtractWeekDay,
    ExtractMonth,
    ExtractQuarter,
    NullIf,
    Cast,
)
from django.core.cache import cache
from django.conf import settings
import pandas as pd
from .models import CartItem
from .utils import calculate_diffs, generate_analytics_cache_key


class DateRangeDict(TypedDict):
    from_date: datetime.date
    to_date: datetime.date


class AnalyticsService:
    DIMENSION_MAPPING: dict[str, Expression] = {
        "product_name": F("product__name"),
        "brand_name": F("product__brand__name"),
        "shop_name": F("receipt__shop__name"),
        "day_month_year": TruncDay("datetime"),
        "day_of_week": ExtractWeekDay("datetime"),
        "month": ExtractMonth("datetime"),
        "month_year": TruncMonth("datetime"),
        "quarter": ExtractQuarter("datetime"),
        "quarter_year": TruncQuarter("datetime"),
        "year": TruncYear("datetime"),
        "hour": ExtractHour("datetime"),
    }

    _turnover = Sum("total_price")
    _profit = Sum("margin_price_total")
    _qty = Sum("qty")

    _checks_count = Count("receipt_id", distinct=True)
    _checks_count_safe = NullIf(Count("receipt_id", distinct=True), 0)
    _sales_qty_safe = NullIf(Sum("qty"), 0)

    METRIC_MAPPING: dict[str, Expression] = {
        "turnover": _turnover,
        "profit": _profit,
        "sales_qty": _qty,
        "checks_count": _checks_count,
        "avg_check": Cast(
            _turnover / _checks_count_safe,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        "avg_price": Cast(
            _turnover / _sales_qty_safe,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        "avg_cost": Cast(
            (_turnover - _profit) / _sales_qty_safe,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        "unique_products_sold": Count("product_id", distinct=True),
    }

    SUFFIXES: list[str] = ["_prev", "_diff", "_diff_percent"]

    def __init__(self, dimensions: list[str], metrics: list[str]) -> None:
        self.requested_dimensions = dimensions
        self.requested_metrics = metrics

        self.base_metrics: set[str] = set()
        for m in self.requested_metrics:
            if m in self.METRIC_MAPPING:
                self.base_metrics.add(m)
                continue

            for suffix in self.SUFFIXES:
                if m.endswith(suffix):
                    base_name = m[: -len(suffix)]
                    if base_name in self.METRIC_MAPPING:
                        self.base_metrics.add(base_name)
                    break

        self.db_group_kwargs: dict[str, Expression] = {
            m: self.DIMENSION_MAPPING[m] for m in self.requested_dimensions if m in self.DIMENSION_MAPPING
        }

        self.db_aggregates: dict[str, Expression] = {
            m: self.METRIC_MAPPING[m] for m in self.base_metrics if m in self.METRIC_MAPPING
        }

    def get_dataframe(self, date_from: datetime.date, date_to: datetime.date, as_total: bool = False) -> pd.DataFrame:
        current_dimensions = list(self.db_group_kwargs.keys())
        current_metrics = list(self.db_aggregates.keys())
        dimensions_for_cache = current_dimensions + ["__total__"] if as_total else current_dimensions

        cache_key = generate_analytics_cache_key(
            date_from,
            date_to,
            dimensions_for_cache,
            current_metrics,
        )

        cached_df = cache.get(cache_key)
        if cached_df is not None:
            return cached_df

        queryset: QuerySet[CartItem] = CartItem.objects.filter(
            datetime__gte=date_from,
            datetime__lte=date_to,
        )

        if current_dimensions:
            queryset = queryset.annotate(**self.db_group_kwargs)
            if "brand_name" in self.db_group_kwargs:
                queryset = queryset.exclude(brand_name__isnull=True).exclude(brand_name__exact="")

        if current_dimensions and not as_total:
            queryset = queryset.values(*current_dimensions).annotate(**self.db_aggregates)
            df = pd.DataFrame(list(queryset))
        else:
            agg_result = queryset.aggregate(**self.db_aggregates)
            if any(val is not None for val in agg_result.values()):
                df = pd.DataFrame([agg_result])
            else:
                df = pd.DataFrame()

        if not df.empty:
            cols_to_convert = [col for col in current_metrics if col in df.columns and col not in current_dimensions]
            if cols_to_convert:
                df[cols_to_convert] = df[cols_to_convert].astype(float)

            ttl = getattr(settings, "ANALYTICS_CACHE_TTL", 3600)
            cache.set(cache_key, df, timeout=ttl)

        return df

    def get_comparison_dataframe(
        self, current_range: DateRangeDict, prev_range: DateRangeDict, as_total: bool = False
    ) -> pd.DataFrame:

        df_curr = self.get_dataframe(current_range["from_date"], current_range["to_date"], as_total=as_total)
        df_prev = self.get_dataframe(prev_range["from_date"], prev_range["to_date"], as_total=as_total)

        merge_on = [] if as_total else list(self.db_group_kwargs.keys())

        df_merged = calculate_diffs(
            df_curr,
            df_prev,
            merge_on=merge_on,
            base_metrics=self.base_metrics,
            requested_metrics=self.requested_metrics,
        )

        final_columns = self.requested_metrics if as_total else self.requested_dimensions + self.requested_metrics
        available_columns = [c for c in final_columns if c in df_merged.columns]

        return df_merged[available_columns]
