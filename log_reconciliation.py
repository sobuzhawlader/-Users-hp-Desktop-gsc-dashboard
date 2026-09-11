import pandas as pd
import numpy as np
from urllib.parse import urlparse
from typing import Dict, Any

def normalize_url_path(url_str: str) -> str:
    """Normalizes URL to comparable pathname (lowercase, stripped trailing slash)."""
    if not url_str or not isinstance(url_str, str):
        return ""
    try:
        parsed = urlparse(url_str)
        path = parsed.path.lower().rstrip('/')
        return path if path else "/"
    except Exception:
        return url_str.lower().rstrip('/')

def reconcile_crawl_with_gsc(crawl_df: pd.DataFrame, gsc_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Reconciles an internal site crawl (e.g. from Screaming Frog) with GSC performance data.
    Identifies Orphaned Performers (URLs earning clicks but having 0 internal inlinks).
    """
    if crawl_df.empty or gsc_df.empty:
        return {'status': 'error', 'message': 'Both Crawl CSV and GSC Data must be provided.'}

    # Standardize Crawl Columns
    crawl = crawl_df.copy()
    url_col = None
    inlinks_col = None

    for col in crawl.columns:
        c_lower = col.lower()
        if 'address' in c_lower or 'url' in c_lower:
            url_col = col
            break

    for col in crawl.columns:
        c_lower = col.lower()
        if 'inlink' in c_lower or 'internal link' in c_lower:
            inlinks_col = col
            break

    if not url_col:
        return {'status': 'error', 'message': "Crawl CSV must contain an 'Address' or 'URL' column."}

    crawl['norm_path'] = crawl[url_col].apply(normalize_url_path)
    if inlinks_col:
        crawl['inlinks'] = pd.to_numeric(crawl[inlinks_col], errors='coerce').fillna(0).astype(int)
    else:
        crawl['inlinks'] = 0

    # Aggregate GSC performance by Page
    gsc_page = gsc_df.groupby('page').agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum'),
        avg_pos=('position', 'mean')
    ).reset_index()
    gsc_page['norm_path'] = gsc_page['page'].apply(normalize_url_path)

    # Outer Join on normalized path
    merged = pd.merge(gsc_page, crawl, on='norm_path', how='outer')
    merged['total_clicks'] = merged['total_clicks'].fillna(0).astype(int)
    merged['total_impressions'] = merged['total_impressions'].fillna(0).astype(int)
    merged['inlinks'] = merged['inlinks'].fillna(0).astype(int)

    # 1. Orphaned Performers: Has Clicks in GSC, but 0 Inlinks (or missing from crawl)
    orphans = merged[
        (merged['total_clicks'] > 0) &
        (merged['inlinks'] == 0)
    ].sort_values('total_clicks', ascending=False)

    # 2. Strong Inlinked Pages with 0 Impressions
    dead_links = merged[
        (merged['inlinks'] >= 5) &
        (merged['total_impressions'] == 0)
    ].sort_values('inlinks', ascending=False)

    return {
        'status': 'success',
        'orphaned_performers': orphans[['page', 'total_clicks', 'total_impressions', 'inlinks']].head(50),
        'unindexed_inlinked': dead_links[[url_col, 'inlinks', 'total_impressions']].head(50) if url_col in dead_links.columns else dead_links.head(50),
        'total_orphans_found': len(orphans),
        'total_dead_links_found': len(dead_links)
    }

def reconcile_server_logs_with_gsc(logs_df: pd.DataFrame, gsc_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Reconciles Googlebot Server Access Logs with GSC performance data.
    Identifies Programmatic Crawl Waste (High bot requests but 0 GSC clicks/impressions).
    """
    if logs_df.empty or gsc_df.empty:
        return {'status': 'error', 'message': 'Both Logs CSV and GSC Data must be provided.'}

    logs = logs_df.copy()
    url_col = None
    hits_col = None

    for col in logs.columns:
        c_lower = col.lower()
        if 'url' in c_lower or 'path' in c_lower or 'request' in c_lower:
            url_col = col
            break

    for col in logs.columns:
        c_lower = col.lower()
        if 'hit' in c_lower or 'count' in c_lower or 'request' in c_lower:
            hits_col = col

    if not url_col:
        return {'status': 'error', 'message': "Logs CSV must contain a 'URL' or 'Path' column."}

    logs['norm_path'] = logs[url_col].apply(normalize_url_path)
    if hits_col and hits_col != url_col:
        logs['bot_hits'] = pd.to_numeric(logs[hits_col], errors='coerce').fillna(1).astype(int)
    else:
        logs_counted = logs.groupby('norm_path').size().reset_index(name='bot_hits')
        logs = pd.merge(logs.drop_duplicates('norm_path'), logs_counted, on='norm_path')

    # Aggregate GSC data
    gsc_page = gsc_df.groupby('page').agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).reset_index()
    gsc_page['norm_path'] = gsc_page['page'].apply(normalize_url_path)

    merged = pd.merge(logs, gsc_page, on='norm_path', how='outer')
    merged['bot_hits'] = merged['bot_hits'].fillna(0).astype(int)
    merged['total_clicks'] = merged['total_clicks'].fillna(0).astype(int)
    merged['total_impressions'] = merged['total_impressions'].fillna(0).astype(int)

    # Programmatic Waste: Bot hits > 5, but 0 Clicks and Impressions
    crawl_waste = merged[
        (merged['bot_hits'] >= 5) &
        (merged['total_clicks'] == 0) &
        (merged['total_impressions'] == 0)
    ].sort_values('bot_hits', ascending=False)

    return {
        'status': 'success',
        'crawl_waste': crawl_waste[['norm_path', 'bot_hits', 'total_clicks', 'total_impressions']].head(50),
        'total_waste_urls': len(crawl_waste)
    }
