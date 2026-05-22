import pandas as pd
from datetime import datetime, timedelta
from auth_gsc import get_gsc_service
from database import save_data, init_db

def fetch_gsc_data(service, site_url, start_date, end_date, dimensions=['query', 'page', 'country', 'device']):
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
                for i, dim in enumerate(dimensions):
                    data[dim] = row['keys'][i]
                data['clicks'] = row.get('clicks', 0)
                data['impressions'] = row.get('impressions', 0)
                data['ctr'] = round(row.get('ctr', 0) * 100, 2)
                data['position'] = round(row.get('position', 0), 2)
                all_rows.append(data)

            start_row += row_limit
            print(f"Fetched {len(all_rows)} rows so far...")

            if len(rows) < row_limit:
                break

        except Exception as e:
            print(f"Error fetching data: {e}")
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

if __name__ == '__main__':
    service = get_gsc_service()
    from auth_gsc import get_sites
    sites = get_sites(service)
    if sites:
        print(f"Fetching data for: {sites[0]}")
        df = fetch_last_days(service, sites[0], days=30)
        print(df.head())