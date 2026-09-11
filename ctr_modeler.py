import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

# Industry Benchmark CTR Curve for reference
BENCHMARK_CTR = {
    1: 28.5, 2: 15.7, 3: 11.0, 4: 8.0, 5: 6.1,
    6: 4.8,  7: 3.9,  8: 3.2,  9: 2.7, 10: 2.4,
    11: 1.8, 12: 1.5, 13: 1.3, 14: 1.1, 15: 1.0,
    16: 0.9, 17: 0.8, 18: 0.8, 19: 0.7, 20: 0.6
}

def build_empirical_ctr_curve(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the domain's custom empirical CTR curve by discrete SERP rank (1-20).
    Compares site's actual CTR with the global industry benchmark.
    """
    if df.empty or 'position' not in df.columns or 'clicks' not in df.columns:
        return pd.DataFrame()

    valid_df = df[(df['position'] >= 0.5) & (df['position'] <= 20.5)].copy()
    if valid_df.empty:
        return pd.DataFrame()

    valid_df['serp_rank'] = valid_df['position'].round().astype(int)
    valid_df = valid_df[(valid_df['serp_rank'] >= 1) & (valid_df['serp_rank'] <= 20)]

    curve = valid_df.groupby('serp_rank').agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum'),
        query_count=('query', 'count')
    ).reset_index()

    curve['actual_ctr'] = np.where(
        curve['total_impressions'] > 0,
        (curve['total_clicks'] / curve['total_impressions'] * 100).round(2),
        0.0
    )

    curve['benchmark_ctr'] = curve['serp_rank'].map(BENCHMARK_CTR).fillna(1.0)
    curve['ctr_performance'] = np.where(
        curve['actual_ctr'] >= curve['benchmark_ctr'],
        "Outperforming Benchmark 🟢",
        "Below Benchmark 🔴"
    )

    return curve.sort_values('serp_rank')

def forecast_traffic_opportunity(df: pd.DataFrame, target_rank: int = 3, min_impressions: int = 50) -> Tuple[pd.DataFrame, int]:
    """
    Calculates estimated additional clicks if keywords currently ranking below target_rank
    improve their positions to target_rank, based on the empirical or benchmark CTR.
    """
    if df.empty or 'position' not in df.columns:
        return pd.DataFrame(), 0

    curve = build_empirical_ctr_curve(df)
    ctr_map = dict(zip(curve['serp_rank'], curve['actual_ctr'])) if not curve.empty else BENCHMARK_CTR

    target_ctr = ctr_map.get(target_rank, BENCHMARK_CTR.get(target_rank, 10.0))

    # Candidates: ranking from target_rank + 1 up to position 20
    candidates = df[
        (df['position'] > target_rank) &
        (df['position'] <= 20) &
        (df['impressions'] >= min_impressions)
    ].copy()

    if candidates.empty:
        return pd.DataFrame(), 0

    candidates['current_ctr'] = candidates['ctr']
    candidates['target_ctr'] = target_ctr

    # Expected clicks = impressions * (target_ctr - current_ctr) / 100
    candidates['potential_clicks'] = (
        candidates['impressions'] * np.maximum(0, (target_ctr - candidates['current_ctr']) / 100)
    ).round().astype(int)

    result = candidates[candidates['potential_clicks'] > 0].sort_values('potential_clicks', ascending=False)
    total_gain = int(result['potential_clicks'].sum())

    cols = ['query', 'page', 'position', 'impressions', 'clicks', 'current_ctr', 'target_ctr', 'potential_clicks']
    available_cols = [c for c in cols if c in result.columns]

    return result[available_cols].head(50), total_gain
