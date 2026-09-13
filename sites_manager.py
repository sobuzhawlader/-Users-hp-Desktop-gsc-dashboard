"""
Google Search Console Sites API Manager
Handles property discovery, addition, deletion, and permission level auditing.
"""

from typing import List, Dict, Any

def list_all_sites(service) -> List[Dict[str, Any]]:
    """Retrieves all verified properties and user permission levels from GSC."""
    if not service:
        return []

    try:
        resp = service.sites().list().execute()
        entries = resp.get('siteEntry', [])
        return entries
    except Exception as ex:
        print(f"Error in list_all_sites: {ex}")
        return []


def add_site_property(service, site_url: str) -> Dict[str, Any]:
    """Adds a new property to Google Search Console."""
    if not site_url or not site_url.strip():
        return {'success': False, 'message': 'Property URL cannot be empty.'}

    cleaned = site_url.strip()
    if service:
        try:
            service.sites().add(siteUrl=cleaned).execute()
            return {'success': True, 'message': f"Property added successfully: {cleaned}"}
        except Exception as ex:
            return {'success': False, 'message': f"GSC API Error: {str(ex)}"}

    return {'success': True, 'message': f"Property registered locally: {cleaned}"}


def delete_site_property(service, site_url: str) -> Dict[str, Any]:
    """Deletes a property from Google Search Console."""
    if not site_url:
        return {'success': False, 'message': 'Property URL cannot be empty.'}

    if service:
        try:
            service.sites().delete(siteUrl=site_url).execute()
            return {'success': True, 'message': f"Property deleted: {site_url}"}
        except Exception as ex:
            return {'success': False, 'message': f"GSC API Error: {str(ex)}"}

    return {'success': True, 'message': f"Property removed: {site_url}"}


import time

_PORTFOLIO_CACHE = {}

def clear_portfolio_cache():
    """Clears the multi-site portfolio in-memory cache."""
    global _PORTFOLIO_CACHE
    _PORTFOLIO_CACHE.clear()

def fetch_all_sites_performance(
    service,
    sites_list: List[Any],
    days: int = 28,
    search_type: str = 'web',
    start_date_str: str = None,
    end_date_str: str = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetches aggregated and comparative Search Console performance data
    across ALL websites/properties in the connected Google Account.
    Runs API queries concurrently via ThreadPoolExecutor for high-speed parallel loading.
    Returns:
    - summary: aggregated clicks, impressions, avg CTR, avg position
    - df_sites: comparative table ranking each site by clicks
    - df_daily: daily timeseries for multi-site trend visualization
    """
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    if start_date_str and end_date_str:
        start_str = start_date_str
        end_str = end_date_str
    else:
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

    site_records = []
    daily_records = []

    # Filter out empty or placeholder entries and accept dict or str
    clean_sites = []
    for s in sites_list:
        site_str = s.get('siteUrl', '') if isinstance(s, dict) else str(s)
        if site_str and site_str not in clean_sites and "Custom Property" not in site_str and not site_str.startswith("🧪") and "Consolidated" not in site_str:
            clean_sites.append(site_str)

    if not clean_sites or not service:
        return {
            'summary': {
                'total_clicks': 0,
                'total_impressions': 0,
                'avg_ctr': 0.0,
                'avg_position': 0.0,
                'total_sites': 0
            },
            'df_sites': pd.DataFrame(),
            'df_daily': pd.DataFrame()
        }

    # Check In-Memory TTL Cache (15 min)
    creds = getattr(service, '_credentials', None) if service else None
    cache_token = getattr(creds, 'token', '') or (str(id(service)) if service else 'offline')
    cache_key = f"{cache_token}_{tuple(sorted(clean_sites))}_{start_str}_{end_str}_{search_type}"

    if not force_refresh and cache_key in _PORTFOLIO_CACHE:
        cached_ts, cached_res = _PORTFOLIO_CACHE[cache_key]
        if time.time() - cached_ts < 900:  # 15 minutes TTL
            return cached_res

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_site_worker(site):
        clean_name = site.replace('sc-domain:', '').replace('https://', '').replace('http://', '').strip('/')
        is_domain = site.startswith('sc-domain:')
        prop_type = "Domain Property" if is_domain else "URL Prefix"
        
        site_c = 0
        site_imp = 0
        site_pos_sum = 0.0
        worker_daily = []

        try:
            body = {
                'startDate': start_str,
                'endDate': end_str,
                'dimensions': ['date'],
                'type': search_type if search_type in ['web', 'image', 'video', 'news', 'discover'] else 'web',
                'rowLimit': 1000
            }
            
            # Use thread-isolated transport to avoid httplib2 socket collisions in concurrent execution
            if creds:
                try:
                    import httplib2
                    from google_auth_httplib2 import AuthorizedHttp
                    thread_http = AuthorizedHttp(creds, http=httplib2.Http())
                    resp = service.searchanalytics().query(siteUrl=site, body=body).execute(http=thread_http)
                except Exception:
                    resp = service.searchanalytics().query(siteUrl=site, body=body).execute()
            else:
                resp = service.searchanalytics().query(siteUrl=site, body=body).execute()

            rows = resp.get('rows', [])
            for r in rows:
                d_clicks = r.get('clicks', 0)
                d_imp = r.get('impressions', 0)
                d_pos = r.get('position', 0.0)
                d_date = r.get('keys', [''])[0]
                
                site_c += d_clicks
                site_imp += d_imp
                site_pos_sum += (d_pos * d_imp)
                
                worker_daily.append({
                    'date': d_date,
                    'site': clean_name,
                    'site_url': site,
                    'clicks': d_clicks,
                    'impressions': d_imp
                })

            avg_ctr = round((site_c / site_imp * 100), 2) if site_imp > 0 else 0.0
            avg_pos = round((site_pos_sum / site_imp), 1) if site_imp > 0 else 0.0

            record = {
                'site_url': site,
                'domain': clean_name,
                'property_type': prop_type,
                'clicks': site_c,
                'impressions': site_imp,
                'ctr': avg_ctr,
                'position': avg_pos,
                'status': 'Connected' if (site_c > 0 or site_imp > 0) else 'No Traffic Yet'
            }
            return record, worker_daily

        except Exception as ex:
            record = {
                'site_url': site,
                'domain': clean_name,
                'property_type': prop_type,
                'clicks': 0,
                'impressions': 0,
                'ctr': 0.0,
                'position': 0.0,
                'status': 'Restricted / Check Access'
            }
            return record, []

    max_workers = min(15, max(1, len(clean_sites)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_site = {executor.submit(_fetch_site_worker, s): s for s in clean_sites}
        for future in as_completed(future_to_site):
            try:
                s_rec, s_daily = future.result()
                site_records.append(s_rec)
                daily_records.extend(s_daily)
            except Exception as ex:
                print(f"Error fetching site performance worker: {ex}")

    df_sites = pd.DataFrame(site_records)
    if not df_sites.empty:
        total_p_clicks = int(df_sites['clicks'].sum())
        total_p_imps = int(df_sites['impressions'].sum())
        avg_p_ctr = round((total_p_clicks / total_p_imps * 100), 2) if total_p_imps > 0 else 0.0
        
        if total_p_imps > 0 and 'position' in df_sites.columns:
            weighted_pos = (df_sites['position'] * df_sites['impressions']).sum() / total_p_imps
            avg_p_pos = round(float(weighted_pos), 1)
        else:
            avg_p_pos = 0.0

        df_sites['traffic_share'] = np.where(total_p_clicks > 0, (df_sites['clicks'] / total_p_clicks * 100).round(1), 0.0)
        df_sites = df_sites.sort_values('clicks', ascending=False).reset_index(drop=True)
        df_sites.insert(0, 'Rank', df_sites.index + 1)
    else:
        total_p_clicks = 0
        total_p_imps = 0
        avg_p_ctr = 0.0
        avg_p_pos = 0.0

    df_daily = pd.DataFrame(daily_records)

    res = {
        'summary': {
            'total_clicks': total_p_clicks,
            'total_impressions': total_p_imps,
            'avg_ctr': avg_p_ctr,
            'avg_position': avg_p_pos,
            'total_sites': len(df_sites)
        },
        'df_sites': df_sites,
        'df_daily': df_daily
    }

    # Save to memory cache
    _PORTFOLIO_CACHE[cache_key] = (time.time(), res)
    return res
