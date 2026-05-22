import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_overview(df):
    if df.empty:
        return {}
    return {
        'total_clicks': int(df['clicks'].sum()),
        'total_impressions': int(df['impressions'].sum()),
        'avg_ctr': round(df['ctr'].mean(), 2),
        'avg_position': round(df['position'].mean(), 2)
    }

def get_quick_wins(df):
    if df.empty:
        return pd.DataFrame()
    return df[
        (df['position'] >= 11) & 
        (df['position'] <= 20) &
        (df['impressions'] > 100)
    ].sort_values('impressions', ascending=False).head(50)

def get_cannibalization(df):
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()
    grouped = df.groupby('query')['page'].nunique().reset_index()
    grouped.columns = ['query', 'page_count']
    cannibalized = grouped[grouped['page_count'] > 1]
    return cannibalized.sort_values('page_count', ascending=False).head(50)

def get_search_intent(df):
    if df.empty or 'query' not in df.columns:
        return df
    
    def classify_intent(query):
        query = str(query).lower()
        if any(w in query for w in ['how', 'why', 'what', 'guide', 'tips', 'tutorial', 'learn']):
            return 'Informational'
        elif any(w in query for w in ['best', 'review', 'top', 'vs', 'compare', 'versus']):
            return 'Commercial'
        elif any(w in query for w in ['buy', 'price', 'coupon', 'shop', 'order', 'cheap']):
            return 'Transactional'
        else:
            return 'Navigational'
    
    df['intent'] = df['query'].apply(classify_intent)
    return df

def get_long_tail_keywords(df):
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()
    df['word_count'] = df['query'].str.split().str.len()
    return df[df['word_count'] >= 4].sort_values('impressions', ascending=False).head(100)

def get_zero_click_keywords(df):
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame()
    return df[
        (df['clicks'] == 0) & 
        (df['impressions'] > 50)
    ].sort_values('impressions', ascending=False).head(50)

def get_content_decay(df):
    if df.empty or 'date' not in df.columns:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    today = datetime.now()
    last_30 = today - timedelta(days=30)
    prev_30 = today - timedelta(days=60)
    
    recent = df[df['date'] >= last_30].groupby('page')['clicks'].sum().reset_index()
    recent.columns = ['page', 'recent_clicks']
    
    previous = df[
        (df['date'] >= prev_30) & 
        (df['date'] < last_30)
    ].groupby('page')['clicks'].sum().reset_index()
    previous.columns = ['page', 'previous_clicks']
    
    merged = recent.merge(previous, on='page', how='inner')
    merged['decay'] = merged['recent_clicks'] - merged['previous_clicks']
    merged['decay_pct'] = round(
        (merged['decay'] / merged['previous_clicks'].replace(0, 1)) * 100, 2
    )
    
    return merged[merged['decay'] < 0].sort_values('decay').head(20)

def get_zombie_pages(df):
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

def get_brand_vs_nonbrand(df, brand_keywords=[]):
    if df.empty or 'query' not in df.columns:
        return {'branded': 0, 'non_branded': 0}
    
    if brand_keywords:
        pattern = '|'.join(brand_keywords)
        branded = df[df['query'].str.contains(pattern, case=False, na=False)]
        non_branded = df[~df['query'].str.contains(pattern, case=False, na=False)]
    else:
        branded = pd.DataFrame()
        non_branded = df
    
    return {
        'branded_clicks': int(branded['clicks'].sum()) if not branded.empty else 0,
        'non_branded_clicks': int(non_branded['clicks'].sum()),
        'branded_impressions': int(branded['impressions'].sum()) if not branded.empty else 0,
        'non_branded_impressions': int(non_branded['impressions'].sum())
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
    if df.empty or 'page' not in df.columns:
        return pd.DataFrame()
    return df.groupby('page').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        avg_ctr=('ctr', 'mean'),
        avg_position=('position', 'mean')
    ).reset_index().sort_values('clicks', ascending=False).head(50)

def get_winning_keywords(df):
    if df.empty:
        return pd.DataFrame()
    return df[
        (df['position'] <= 10) & 
        (df['clicks'] > 0)
    ].sort_values('clicks', ascending=False).head(50)

def get_high_impression_low_ctr(df):
    if df.empty:
        return pd.DataFrame()
    avg_ctr = df['ctr'].mean()
    return df[
        (df['impressions'] > 500) & 
        (df['ctr'] < avg_ctr)
    ].sort_values('impressions', ascending=False).head(50)