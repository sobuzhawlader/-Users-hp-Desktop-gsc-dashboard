import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from auth_gsc import get_gsc_service
from database import save_data, init_db

# Supported official GSC search types
SEARCH_TYPES = ['web', 'image', 'video', 'news', 'discover', 'googleNews']

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_gsc_data_cached(
    _service,
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: Optional[List[str]] = None,
    search_type: str = 'web',
    data_state: str = 'final',
    aggregation_type: str = 'auto',
    dimension_filters: Optional[List[Dict[str, Any]]] = None
) -> pd.DataFrame:
    """Internal cached GSC API query executor."""
    if not _service:
        return pd.DataFrame()

    # Discover and GoogleNews do NOT support the 'query' dimension
    if search_type in ['discover', 'googleNews']:
        if dimensions is None:
            dims = ['date', 'page', 'country', 'device']
        else:
            dims = [d for d in dimensions if d != 'query']
    elif dimensions is None:
        dims = ['date', 'query', 'page', 'country', 'device']
    else:
        dims = list(dimensions)

    all_rows = []
    start_row = 0
    row_limit = 25000

    while True:
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dims,
            'rowLimit': row_limit,
            'startRow': start_row,
            'type': search_type if search_type in SEARCH_TYPES else 'web',
            'dataState': data_state if data_state in ['all', 'final'] else 'final',
            'aggregationType': aggregation_type if aggregation_type in ['auto', 'byPage', 'byProperty'] else 'auto'
        }

        # Apply dimension filter groups if specified (e.g. query regex, page contains)
        if dimension_filters:
            request_body['dimensionFilterGroups'] = [{
                'filters': dimension_filters
            }]

        try:
            response = _service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()

            rows = response.get('rows', [])
            if not rows:
                break

            for row in rows:
                data = {}
                keys = row.get('keys', [])
                for i, dim in enumerate(dims):
                    if i < len(keys):
                        data[dim] = keys[i]
                    else:
                        data[dim] = ''

                data['clicks'] = int(row.get('clicks', 0))
                data['impressions'] = int(row.get('impressions', 0))
                data['ctr'] = round(row.get('ctr', 0) * 100, 2)
                data['position'] = round(row.get('position', 0), 2)
                all_rows.append(data)

            start_row += row_limit

            # GSC API hard pagination limit is 100,000 rows
            if len(rows) < row_limit or start_row >= 100000:
                break

        except Exception as e:
            print(f"Error fetching GSC data (search_type={search_type}): {e}")
            break

    df = pd.DataFrame(all_rows)
    return df


def fetch_gsc_data(
    service=None,
    site_url: str = "",
    start_date: str = "",
    end_date: str = "",
    dimensions: Optional[List[str]] = None,
    search_type: str = 'web',
    data_state: str = 'final',
    aggregation_type: str = 'auto',
    dimension_filters: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Fetches search analytics data from GSC API with high-performance caching:
    - Dimensions: date, query, page, country, device, searchAppearance
    - Search Types: web, image, video, news, discover, googleNews
    - Data State: 'all' (includes fresh unfinalized/hourly data) or 'final'
    - RE2 Regex and dimension filters
    - Complete pagination up to 100,000 rows
    """
    actual_service = service if service is not None else kwargs.get('_service')
    if not actual_service:
        return pd.DataFrame()

    return _fetch_gsc_data_cached(
        _service=actual_service,
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimensions,
        search_type=search_type,
        data_state=data_state,
        aggregation_type=aggregation_type,
        dimension_filters=dimension_filters
    )


def fetch_discover_data(service, site_url: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetches Google Discover feed performance (impressions and clicks)."""
    return fetch_gsc_data(
        service=service,
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=['date', 'page', 'country'],
        search_type='discover'
    )


def fetch_fresh_data(service, site_url: str, days: int = 3) -> pd.DataFrame:
    """Fetches unfinalized/fresh GSC data up to the current day (dataState='all')."""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    return fetch_gsc_data(
        service=service,
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        data_state='all'
    )


def fetch_search_appearance(service, site_url: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetches performance broken down by rich results / search appearance."""
    return fetch_gsc_data(
        service=service,
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=['searchAppearance', 'date'],
        search_type='web'
    )


def fetch_last_days(service, site_url: str, days: int = 30, search_type: str = 'web') -> pd.DataFrame:
    """Convenience helper to fetch standard period."""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    return fetch_gsc_data(service, site_url, start_date, end_date, search_type=search_type)


def fetch_and_save(site_url: str, days: int = 30) -> pd.DataFrame:
    """Automated fetcher for scheduled syncs."""
    init_db()
    service = get_gsc_service(None)
    if not service:
        print("No active GSC service.")
        return pd.DataFrame()
    df = fetch_last_days(service, site_url, days)
    if not df.empty:
        save_data(df, site_url)
        print(f"Done! Saved {len(df)} rows.")
    return df