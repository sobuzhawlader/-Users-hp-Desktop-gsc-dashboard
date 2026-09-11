import pandas as pd
from datetime import datetime, timedelta
from auth_gsc import get_gsc_service
from database import save_data, init_db

def fetch_gsc_data(service, site_url, start_date, end_date, dimensions=None):
    """
    Fetches search analytics data from GSC API with pagination.
    Includes date, query, page, country, device for deep analysis.
    """
    if dimensions is None:
        dimensions = ['date', 'query', 'page', 'country', 'device']

    all_rows = []
    start_row = 0
    row_limit = 25000

    while True:
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': row_limit,
            'startRow': start_row
        }

        try:
            response = service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()

            rows = response.get('rows', [])
            if not rows:
                break

            for row in rows:
                data = {}
                keys = row.get('keys', [])
                for i, dim in enumerate(dimensions):
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
            print(f"Fetched {len(all_rows)} rows so far...")

            # GSC API pagination limit is 100,000 rows
            if len(rows) < row_limit or start_row >= 100000:
                break

        except Exception as e:
            print(f"Error fetching GSC data: {e}")
            break

    df = pd.DataFrame(all_rows)
    print(f"Total rows fetched: {len(df)}")
    return df

def fetch_last_days(service, site_url, days=30):
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    return fetch_gsc_data(service, site_url, start_date, end_date)

def fetch_and_save(site_url, days=30):
    init_db()
    service = get_gsc_service()
    if not service:
        print("No active GSC service.")
        return pd.DataFrame()
    print(f"Fetching data for {site_url}...")
    df = fetch_last_days(service, site_url, days)
    if not df.empty:
        save_data(df, site_url)
        print(f"Done! Saved {len(df)} rows.")
    return df

def get_date_range(period='last_30'):
    today = datetime.now()
    if period == 'last_7':
        start = today - timedelta(days=7)
    elif period == 'last_30':
        start = today - timedelta(days=30)
    elif period == 'last_90':
        start = today - timedelta(days=90)
    elif period == 'last_6_months':
        start = today - timedelta(days=180)
    elif period == 'last_12_months':
        start = today - timedelta(days=365)
    else:
        start = today - timedelta(days=30)
    return start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')