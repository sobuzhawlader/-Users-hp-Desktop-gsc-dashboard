import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_overview(df):
    """Calculates true weighted GSC performance metrics."""
    if df.empty or 'clicks' not in df.columns or 'impressions' not in df.columns:
        return {'total_clicks': 0, 'total_impressions': 0, 'avg_ctr': 0.0, 'avg_position': 0.0}

    total_clicks = int(df['clicks'].sum())
    total_impressions = int(df['impressions'].sum())

    # Mathematically sound weighted CTR
    avg_ctr = round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0.0

    # Mathematically sound weighted average position
    if total_impressions > 0 and 'position' in df.columns:
        avg_pos = round(float((df['position'] * df['impressions']).sum() / total_impressions), 2)
    elif 'position' in df.columns:
        avg_pos = round(float(df['position'].mean()), 2)
    else:
        avg_pos = 0.0

    return {
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'avg_ctr': avg_ctr,
        'avg_position': avg_pos
    }

def get_winning_keywords(df):
    """Aggregates queries across dates/pages and returns top ranking performers."""
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby('query').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()

    grouped['ctr'] = np.where(
        grouped['impressions'] > 0,
        (grouped['clicks'] / grouped['impressions'] * 100).round(2),
        0.0
    )
    grouped['position'] = grouped['position'].round(1)

    return grouped[
        (grouped['position'] <= 10.4) & 
        (grouped['clicks'] > 0)
    ].sort_values('clicks', ascending=False).head(50)

def get_quick_wins(df):
    """Finds striking distance queries (Page 2: positions 11-20) with high impressions."""
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby('query').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()

    grouped['ctr'] = np.where(
        grouped['impressions'] > 0,
        (grouped['clicks'] / grouped['impressions'] * 100).round(2),
        0.0
    )
    grouped['position'] = grouped['position'].round(1)

    return grouped[
        (grouped['position'] >= 10.5) & 
        (grouped['position'] <= 20.4) &
        (grouped['impressions'] >= 50)
    ].sort_values('impressions', ascending=False).head(50)

def get_cannibalization(df):
    """Finds keywords where multiple distinct pages compete for ranking."""
    if df.empty or 'query' not in df.columns or 'page' not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby('query')['page'].nunique().reset_index()
    grouped.columns = ['query', 'page_count']
    cannibalized = grouped[grouped['page_count'] > 1]
    return cannibalized.sort_values('page_count', ascending=False).head(50)

def get_search_intent(df):
    """Classifies search intent using pattern matching on query terms."""
    if df.empty or 'query' not in df.columns:
        return df

    out_df = df.copy()

    def classify_intent(query):
        q = str(query).lower()
        if any(w in q for w in ['how', 'why', 'what', 'where', 'when', 'who', 'guide', 'tips', 'tutorial', 'learn']):
            return 'Informational'
        elif any(w in q for w in ['best', 'review', 'top', 'vs', 'compare', 'versus']):
            return 'Commercial'
        elif any(w in q for w in ['buy', 'price', 'coupon', 'shop', 'order', 'cheap', 'cost']):
            return 'Transactional'
        else:
            return 'Navigational'

    out_df['intent'] = out_df['query'].apply(classify_intent)
    return out_df

def get_long_tail_keywords(df):
    """Isolates long-tail queries with 4 or more words."""
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby('query').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()

    grouped['word_count'] = grouped['query'].astype(str).str.split().str.len()
    grouped['position'] = grouped['position'].round(1)

    return grouped[grouped['word_count'] >= 4].sort_values('impressions', ascending=False).head(50)

def get_zero_click_keywords(df):
    """Finds high-impression keywords with zero clicks."""
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby('query').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()

    grouped['position'] = grouped['position'].round(1)

    return grouped[
        (grouped['clicks'] == 0) & 
        (grouped['impressions'] >= 30)
    ].sort_values('impressions', ascending=False).head(50)

def get_content_decay(df):
    """Compares recent 30-day click volume with the preceding 30 days per page."""
    if df.empty or 'date' not in df.columns or 'page' not in df.columns:
        return pd.DataFrame()

    decay_df = df.copy()
    decay_df['date_dt'] = pd.to_datetime(decay_df['date'], errors='coerce')
    decay_df = decay_df.dropna(subset=['date_dt'])

    if decay_df.empty:
        return pd.DataFrame()

    max_date = decay_df['date_dt'].max()
    last_30 = max_date - timedelta(days=30)
    prev_30 = max_date - timedelta(days=60)

    recent = decay_df[decay_df['date_dt'] >= last_30].groupby('page')['clicks'].sum().reset_index()
    recent.columns = ['page', 'recent_clicks']

    previous = decay_df[
        (decay_df['date_dt'] >= prev_30) & 
        (decay_df['date_dt'] < last_30)
    ].groupby('page')['clicks'].sum().reset_index()
    previous.columns = ['page', 'previous_clicks']

    merged = recent.merge(previous, on='page', how='inner')
    merged['decay'] = merged['recent_clicks'] - merged['previous_clicks']
    merged['decay_pct'] = round(
        (merged['decay'] / merged['previous_clicks'].replace(0, 1)) * 100, 2
    )

    return merged[merged['decay'] < 0].sort_values('decay').head(20)

def get_zombie_pages(df):
    """Identifies indexed pages that receive minimal impressions (<10) and zero clicks."""
    if df.empty or 'page' not in df.columns:
        return pd.DataFrame()

    zombie = df.groupby('page').agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).reset_index()

    return zombie[
        (zombie['total_clicks'] == 0) & 
        (zombie['total_impressions'] < 10)
    ].head(50)

def get_brand_vs_nonbrand(df, brand_keywords=None):
    """Splits search performance into branded and non-branded queries."""
    if df.empty or 'query' not in df.columns:
        return {'branded_clicks': 0, 'non_branded_clicks': 0, 'branded_impressions': 0, 'non_branded_impressions': 0}

    if brand_keywords:
        pattern = '|'.join([k.strip() for k in brand_keywords if k.strip()])
        if pattern:
            branded = df[df['query'].str.contains(pattern, case=False, na=False)]
            non_branded = df[~df['query'].str.contains(pattern, case=False, na=False)]
        else:
            branded = pd.DataFrame()
            non_branded = df
    else:
        branded = pd.DataFrame()
        non_branded = df

    return {
        'branded_clicks': int(branded['clicks'].sum()) if not branded.empty else 0,
        'non_branded_clicks': int(non_branded['clicks'].sum()) if not non_branded.empty else 0,
        'branded_impressions': int(branded['impressions'].sum()) if not branded.empty else 0,
        'non_branded_impressions': int(non_branded['impressions'].sum()) if not non_branded.empty else 0
    }

def get_device_breakdown(df):
    if df.empty or 'device' not in df.columns:
        return pd.DataFrame()
    return df.groupby('device').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        avg_position=('position', 'mean')
    ).reset_index()

def get_country_breakdown(df):
    if df.empty or 'country' not in df.columns:
        return pd.DataFrame()
    return df.groupby('country').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum')
    ).reset_index().sort_values('clicks', ascending=False).head(20)

def get_top_pages(df):
    """Calculates aggregated performance by page with true weighted CTR."""
    if df.empty or 'page' not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby('page').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()

    grouped['ctr'] = np.where(
        grouped['impressions'] > 0,
        (grouped['clicks'] / grouped['impressions'] * 100).round(2),
        0.0
    )
    grouped['position'] = grouped['position'].round(1)

    return grouped.sort_values('clicks', ascending=False).head(50)

def get_high_impression_low_ctr(df):
    """Identifies queries with above-average impressions but below-average CTR."""
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()

    overview = get_overview(df)
    site_avg_ctr = overview['avg_ctr']

    grouped = df.groupby('query').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()

    grouped['ctr'] = np.where(
        grouped['impressions'] > 0,
        (grouped['clicks'] / grouped['impressions'] * 100).round(2),
        0.0
    )
    grouped['position'] = grouped['position'].round(1)

    return grouped[
        (grouped['impressions'] >= 200) & 
        (grouped['ctr'] < site_avg_ctr)
    ].sort_values('impressions', ascending=False).head(50)