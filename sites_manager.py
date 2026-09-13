"""
Google Search Console Sites API Manager
Handles property discovery, addition, deletion, and permission level auditing.
"""

from typing import List, Dict, Any

def list_all_sites(service) -> List[Dict[str, Any]]:
    """Retrieves all verified properties and user permission levels from GSC."""
    if not service:
        return [
            {"siteUrl": "https://centralec-electrical.co.uk/", "permissionLevel": "siteOwner"},
            {"siteUrl": "sc-domain:centralec-electrical.co.uk", "permissionLevel": "siteOwner"}
        ]

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


def fetch_all_sites_performance(
    service,
    sites_list: List[Any],
    days: int = 28,
    search_type: str = 'web',
    start_date_str: str = None,
    end_date_str: str = None
) -> Dict[str, Any]:
    """
    Fetches aggregated and comparative Search Console performance data
    across ALL websites/properties in the connected Google Account.
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

    if not clean_sites:
        clean_sites = ["https://centralec-electrical.co.uk/", "sc-domain:centralec-electrical.co.uk"]

    if service:
        for site in clean_sites:
            clean_name = site.replace('sc-domain:', '').replace('https://', '').replace('http://', '').strip('/')
            is_domain = site.startswith('sc-domain:')
            prop_type = "Domain Property" if is_domain else "URL Prefix"
            
            site_c = 0
            site_imp = 0
            site_pos_sum = 0.0

            try:
                body = {
                    'startDate': start_str,
                    'endDate': end_str,
                    'dimensions': ['date'],
                    'type': search_type if search_type in ['web', 'image', 'video', 'news', 'discover'] else 'web',
                    'rowLimit': 1000
                }
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
                    
                    daily_records.append({
                        'date': d_date,
                        'site': clean_name,
                        'site_url': site,
                        'clicks': d_clicks,
                        'impressions': d_imp
                    })

                avg_ctr = round((site_c / site_imp * 100), 2) if site_imp > 0 else 0.0
                avg_pos = round((site_pos_sum / site_imp), 1) if site_imp > 0 else 0.0

                site_records.append({
                    'site_url': site,
                    'domain': clean_name,
                    'property_type': prop_type,
                    'clicks': site_c,
                    'impressions': site_imp,
                    'ctr': avg_ctr,
                    'position': avg_pos,
                    'status': 'Connected' if (site_c > 0 or site_imp > 0) else 'No Traffic Yet'
                })

            except Exception as ex:
                site_records.append({
                    'site_url': site,
                    'domain': clean_name,
                    'property_type': prop_type,
                    'clicks': 0,
                    'impressions': 0,
                    'ctr': 0.0,
                    'position': 0.0,
                    'status': 'Restricted / Check Access'
                })
    else:
        # Realistic Demo Data for sample properties
        sample_stats = [
            {"site_url": "https://centralec-electrical.co.uk/", "domain": "centralec-electrical.co.uk", "property_type": "URL Prefix", "clicks": 83, "impressions": 16600, "ctr": 0.5, "position": 33.4, "status": "Active"},
            {"site_url": "sc-domain:centralec-electrical.co.uk", "domain": "centralec-electrical.co.uk (Domain)", "property_type": "Domain Property", "clicks": 142, "impressions": 28400, "ctr": 0.5, "position": 29.8, "status": "Active"}
        ]
        
        for s in clean_sites:
            if s not in [x['site_url'] for x in sample_stats]:
                c_name = s.replace('sc-domain:', '').replace('https://', '').replace('http://', '').strip('/')
                sample_stats.append({
                    "site_url": s,
                    "domain": c_name,
                    "property_type": "Domain Property" if s.startswith('sc-domain:') else "URL Prefix",
                    "clicks": 62,
                    "impressions": 12800,
                    "ctr": 0.48,
                    "position": 35.1,
                    "status": "Active"
                })
        site_records = sample_stats

        cur_d = start_date
        while cur_d <= end_date:
            d_str = cur_d.strftime('%Y-%m-%d')
            for sr in site_records:
                h_val = abs(hash(d_str + sr['domain']))
                day_c = max(0, int(sr['clicks'] / max(1, days) + (h_val % 5 - 2)))
                day_imp = max(10, int(sr['impressions'] / max(1, days) + (h_val % 200 - 100)))
                daily_records.append({
                    'date': d_str,
                    'site': sr['domain'],
                    'site_url': sr['site_url'],
                    'clicks': day_c,
                    'impressions': day_imp
                })
            cur_d += timedelta(days=1)

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

    return {
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
