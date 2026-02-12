import hashlib
import json
import datetime
import pandas as pd
import numpy as np


def generate_analytics_cache_key(
    date_from: datetime.date,
    date_to: datetime.date,
    dimensions: list[str],
    metrics: list[str],
) -> str:
    payload = {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "dimensions": sorted(dimensions),
        "metrics": sorted(metrics),
    }

    payload_str = json.dumps(payload, sort_keys=True)
    hash_object = hashlib.md5(payload_str.encode("utf-8"))

    return f"analytics:{hash_object.hexdigest()}"


def calculate_diffs(
    df_curr: pd.DataFrame,
    df_prev: pd.DataFrame,
    merge_on: list[str],
    base_metrics: set[str],
    requested_metrics: list[str],
) -> pd.DataFrame:
    rename_map = {m: f"{m}_prev" for m in base_metrics}
    df_prev = df_prev.rename(columns=rename_map)

    df_merged = pd.merge(
        df_curr,
        df_prev,
        on=merge_on,
        how="outer",
    )

    df_merged = df_merged.fillna(0)
    requested_set = set(requested_metrics)

    for base in base_metrics:
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

            with np.errstate(divide="ignore", invalid="ignore"):
                pct_values = (diff_values / df_merged[prev_col]) * 100

            pct_values = np.nan_to_num(pct_values, posinf=100.0, neginf=-100.0, nan=0.0)
            df_merged[pct_col] = pct_values.round(2)

    df_merged = df_merged.fillna(0)

    return df_merged
