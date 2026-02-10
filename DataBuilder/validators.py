from typing import Any

from rest_framework import serializers


def validate_comparison_metrics(data: dict[str, Any]) -> dict[str, Any]:
    raw_metrics = data.get("metrics", [])

    metrics: list[str] = []
    if isinstance(raw_metrics, list):
        metrics = [m for m in raw_metrics if isinstance(m, str)]

    prev_date_range = data.get("prev_date_range")

    comparison_suffixes = ("_prev", "_diff", "_diff_percent")

    needs_comparison = False
    for m in metrics:
        if m.endswith(comparison_suffixes):
            needs_comparison = True
            break

    if needs_comparison and not prev_date_range:
        raise serializers.ValidationError({"prev_date_range": ["This field is required."]})

    return data
