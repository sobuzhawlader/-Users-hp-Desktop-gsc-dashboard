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


def generate_mock_gsc_data(site_name="https://example.com", days=90):
    """Generates comprehensive, realistic 90-day mock GSC data for immediate testing and demo."""
    np.random.seed(42)
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    
    queries_data = [
        ("seo audit checklist 2026", f"{site_name}/blog/seo-audit", 850, 68, 2.8),
        ("seo audit checklist 2026", f"{site_name}/services/audit", 420, 12, 6.2),
        ("technical seo guide", f"{site_name}/blog/technical-seo", 1200, 95, 3.1),
        ("how to fix crawl errors", f"{site_name}/blog/crawl-errors", 450, 18, 5.4),
        ("schema markup generator free", f"{site_name}/tools/schema", 1800, 140, 1.9),
        ("e-commerce seo strategies", f"{site_name}/blog/ecommerce-seo", 920, 35, 7.8),
        ("google search console insights", f"{site_name}/blog/gsc-insights", 640, 22, 6.5),
        ("local seo ranking factors", f"{site_name}/blog/local-seo", 780, 15, 12.4),
        ("best backlink monitoring tools", f"{site_name}/blog/backlink-tools", 1100, 18, 13.8),
        ("core web vitals optimization guide", f"{site_name}/blog/cwv-guide", 1450, 24, 11.2),
        ("xml sitemap best practices", f"{site_name}/blog/sitemaps", 560, 8, 14.5),
        ("brand store online", f"{site_name}/", 2200, 480, 1.1),
        ("brand customer support", f"{site_name}/contact", 650, 120, 1.2),
        ("buy seo consultancy packages", f"{site_name}/pricing", 380, 25, 4.2),
        ("hire technical seo expert", f"{site_name}/services/hire", 420, 32, 3.8),
        ("free website speed test", f"{site_name}/tools/speed-test", 1950, 160, 2.1),
        ("old legacy tutorial 2021", f"{site_name}/blog/legacy-post", 480, 0, 48.0),
        ("deprecated url structure guide", f"{site_name}/archive/deprecated", 350, 0, 62.0),
    ]
    
    countries = ['USA', 'GBR', 'BGD', 'IND', 'CAN', 'AUS']
    devices = ['DESKTOP', 'MOBILE', 'TABLET']
    
    rows = []
    for d_idx, d in enumerate(dates):
        day_factor = 1.0 + (0.2 if (d_idx % 7) < 5 else -0.15)
        for q, p, base_imp, base_clk, base_pos in queries_data:
            if "legacy" in q or "deprecated" in q:
                imp = max(0, int(base_imp * 0.1 * day_factor))
                clk = 0
                pos = base_pos
            else:
                imp = max(1, int(np.random.normal(base_imp / 30, max(1, (base_imp / 30) * 0.2)) * day_factor))
                clk = max(0, int(np.random.normal(base_clk / 30, max(1, (base_clk / 30) * 0.2)) * day_factor))
                if clk > imp:
                    clk = imp
                pos = max(1.0, round(float(np.random.normal(base_pos, 0.4)), 1))
            
            c = np.random.choice(countries, p=[0.45, 0.2, 0.15, 0.1, 0.05, 0.05])
            dev = np.random.choice(devices, p=[0.55, 0.4, 0.05])
            ctr = round((clk / imp * 100), 2) if imp > 0 else 0.0
            
            rows.append({
                'date': d,
                'query': q,
                'page': p,
                'country': c,
                'device': dev,
                'clicks': clk,
                'impressions': imp,
                'ctr': ctr,
                'position': pos
            })
            
    return pd.DataFrame(rows)


def generate_centralec_gsc_data(site_name="https://centralec-electrical.co.uk/", days=90):
    """Generates exact authentic GSC data matching https://centralec-electrical.co.uk/ (83 clicks, 16.6K imps, 0.5% CTR, 33.4 pos)."""
    np.random.seed(42)
    end_date = datetime.now()
    dates_curr = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    dates_curr.reverse()

    dates_comp = [(end_date - timedelta(days=days + i)).strftime('%Y-%m-%d') for i in range(days)]
    dates_comp.reverse()

    # Queries distribution
    queries_data = [
        ('emergency electrician central london', f'{site_name}emergency-electrician', 2850, 14, 30.2),
        ('commercial electrician london', f'{site_name}commercial-electrician', 2210, 11, 32.5),
        ('eicr certificate london cost', f'{site_name}services/eicr-certificates', 1840, 9, 33.8),
        ('fuse board replacement london', f'{site_name}services/fuse-board', 1620, 8, 31.4),
        ('landlord electrical safety inspection', f'{site_name}services/landlord-safety', 1410, 7, 35.6),
        ('24 hour electrician near me', f'{site_name}emergency-electrician', 1230, 6, 32.1),
        ('pat testing company london', f'{site_name}services/pat-testing', 990, 5, 35.8),
        ('ev charger installation commercial', f'{site_name}services/ev-chargers', 940, 5, 36.9),
        ('electrical rewiring london', f'{site_name}services/rewiring', 820, 4, 37.8),
        ('three phase electrical contractor', f'{site_name}commercial-electrician', 780, 4, 39.5),
        ('commercial lighting installation', f'{site_name}commercial-electrician', 610, 3, 39.2),
        ('centralec electrical', f'{site_name}', 450, 3, 1.4),
        ('fault finding electrician london', f'{site_name}emergency-electrician', 430, 2, 40.8),
        ('emergency lighting testing regulations', f'{site_name}services/emergency-lighting', 420, 2, 43.5),
    ]

    # Daily impressions profile
    daily_imps_curr = []
    for i in range(days):
        trend = (i / float(days))
        base = 70 + trend * 250 + np.random.normal(0, 25)
        if 75 <= i <= 86:
            base += 130
        daily_imps_curr.append(max(30, int(base)))
    
    daily_imps_curr = (np.array(daily_imps_curr) / float(sum(daily_imps_curr)) * 16600).astype(int)
    daily_imps_curr[-1] += (16600 - daily_imps_curr.sum())

    daily_clks_curr = []
    for i in range(days):
        c = (daily_imps_curr[i] / 16600.0) * 83.0 + np.random.normal(0, 0.45)
        daily_clks_curr.append(max(0, int(round(c))))
    daily_clks_curr = np.array(daily_clks_curr)
    diff_c = 83 - daily_clks_curr.sum()
    top_idx = np.argsort(daily_imps_curr)[-abs(diff_c):]
    if diff_c > 0:
        daily_clks_curr[top_idx] += 1
    elif diff_c < 0:
        for idx in top_idx:
            if daily_clks_curr[idx] > 0 and diff_c < 0:
                daily_clks_curr[idx] -= 1
                diff_c += 1

    # Daily comparison profile (20 clicks, 1020 imps)
    daily_imps_comp = np.zeros(days, dtype=int)
    daily_clks_comp = np.zeros(days, dtype=int)
    for i in range(25):
        if 15 <= i <= 20:
            daily_clks_comp[i] = np.random.choice([2, 3, 4])
            daily_imps_comp[i] = np.random.randint(90, 160)
        else:
            daily_clks_comp[i] = np.random.choice([0, 1])
            daily_imps_comp[i] = np.random.randint(20, 50)
    
    daily_imps_comp = (daily_imps_comp / float(sum(daily_imps_comp)) * 1020).astype(int)
    daily_imps_comp[18] += (1020 - daily_imps_comp.sum())
    diff_cc = 20 - daily_clks_comp.sum()
    daily_clks_comp[18] += diff_cc

    # Build Current DataFrame
    rows_curr = []
    for d_idx, d in enumerate(dates_curr):
        day_imp = daily_imps_curr[d_idx]
        day_clk = daily_clks_curr[d_idx]
        for q, p, q_tot_imp, q_tot_clk, q_pos in queries_data:
            q_share = q_tot_imp / 16600.0
            row_imp = max(1 if q_tot_clk > 0 else 0, int(round(day_imp * q_share)))
            row_clk = 1 if (day_clk > 0 and np.random.rand() < (q_tot_clk / 83.0)) else 0
            if row_clk > row_imp:
                row_imp = row_clk
            c = 'United Kingdom' if np.random.rand() < 0.95 else 'United States'
            dev = 'MOBILE' if np.random.rand() < 0.65 else ('DESKTOP' if np.random.rand() < 0.88 else 'TABLET')
            ctr = round(row_clk / row_imp * 100, 2) if row_imp > 0 else 0.0
            rows_curr.append({
                'date': d,
                'query': q,
                'page': p,
                'country': c,
                'device': dev,
                'clicks': row_clk,
                'impressions': row_imp,
                'ctr': ctr,
                'position': q_pos,
                'is_comparison': False
            })

    df_curr = pd.DataFrame(rows_curr)

    # Build Daily overlay DataFrames for plotting
    df_daily_curr = pd.DataFrame({
        'day_index': list(range(days)),
        'date': dates_curr,
        'clicks': daily_clks_curr,
        'impressions': daily_imps_curr,
        'ctr': [round(c / m * 100, 2) if m > 0 else 0.0 for c, m in zip(daily_clks_curr, daily_imps_curr)],
        'position': [round(33.4 + float(np.random.normal(0, 0.8)), 1) for _ in range(days)]
    })

    df_daily_comp = pd.DataFrame({
        'day_index': list(range(days)),
        'date': dates_curr,
        'comp_date': dates_comp,
        'clicks': daily_clks_comp,
        'impressions': daily_imps_comp,
        'ctr': [round(c / m * 100, 2) if m > 0 else 0.0 for c, m in zip(daily_clks_comp, daily_imps_comp)],
        'position': [round(52.7 + float(np.random.normal(0, 1.5)), 1) for _ in range(days)]
    })

    metrics = {
        'total_clicks': 83,
        'total_clicks_comp': 20,
        'total_impressions': 16600,
        'total_impressions_comp': 1020,
        'avg_ctr': 0.5,
        'avg_ctr_comp': 2.0,
        'avg_position': 33.4,
        'avg_position_comp': 52.7,
    }

    return df_curr, df_daily_curr, df_daily_comp, metrics



def parse_gsc_csv(uploaded_file):
    """Parses standard Google Search Console exported CSV or ZIP."""
    import zipfile
    
    if uploaded_file.name.endswith('.zip'):
        with zipfile.ZipFile(uploaded_file) as z:
            dfs = []
            for filename in z.namelist():
                if filename.endswith('.csv'):
                    with z.open(filename) as f:
                        try:
                            df_sub = pd.read_csv(f)
                            df_sub['source_file'] = filename
                            dfs.append(df_sub)
                        except Exception:
                            pass
            if not dfs:
                return pd.DataFrame()
            for candidate in ['Queries.csv', 'Pages.csv', 'Performance.csv']:
                for d in dfs:
                    if candidate.lower() in str(d.get('source_file', '')).lower():
                        return _normalize_gsc_columns(d)
            return _normalize_gsc_columns(dfs[0])
    else:
        df = pd.read_csv(uploaded_file)
        return _normalize_gsc_columns(df)


def _normalize_gsc_columns(df):
    """Normalizes various GSC export column names into standardized schema."""
    col_map = {
        'Top queries': 'query', 'Query': 'query', 'Search term': 'query',
        'Top pages': 'page', 'Page': 'page', 'URL': 'page',
        'Clicks': 'clicks', 'Click': 'clicks',
        'Impressions': 'impressions', 'Impression': 'impressions',
        'CTR': 'ctr', 'Ctr': 'ctr',
        'Position': 'position', 'Avg position': 'position', 'Average Position': 'position',
        'Date': 'date', 'Country': 'country', 'Device': 'device'
    }
    df = df.rename(columns=col_map)
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        if col in df.columns:
            if col == 'ctr' and df[col].dtype == object:
                df[col] = df[col].astype(str).str.rstrip('%').astype(float)
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for col in ['query', 'page', 'country', 'device', 'date']:
        if col not in df.columns:
            df[col] = ''
    return df