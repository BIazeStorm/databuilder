from rest_framework import serializers


def validate_comparison_metrics(data):
    metrics = data.get("metrics")
    prev_date_range = data.get("prev_date_range")

    comparison_suffixes = ("_prev", "_diff", "_diff_percent")

    needs_comparison = any(m.endswith(comparison_suffixes) for m in metrics)

    if needs_comparison and not prev_date_range:
        raise serializers.ValidationError(
            {
                "prev_date_range": ["This field is required."],
            }
        )

    return data
