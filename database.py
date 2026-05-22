import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = 'gsc_data.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS search_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_url TEXT,
        date TEXT,
        query TEXT,
        page TEXT,
        country TEXT,
        device TEXT,
        clicks INTEGER,
        impressions INTEGER,
        ctr REAL,
        position REAL,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_url TEXT UNIQUE,
        added_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_url TEXT,
        alert_type TEXT,
        message TEXT,
        created_at TEXT,
        is_read INTEGER DEFAULT 0
    )''')
    
    conn.commit()
    conn.close()
    print("Database initialized!")

def save_data(df, site_url):
    conn = sqlite3.connect(DB_FILE)
    df['site_url'] = site_url
    df['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df.to_sql('search_data', conn, if_exists='append', index=False)
    conn.close()
    print(f"Saved {len(df)} rows for {site_url}")

def load_data(site_url=None, start_date=None, end_date=None):
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT * FROM search_data WHERE 1=1"
    params = []
    
    if site_url:
        query += " AND site_url = ?"
        params.append(site_url)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def save_alert(site_url, alert_type, message):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO alerts (site_url, alert_type, message, created_at)
                 VALUES (?, ?, ?, ?)''',
              (site_url, alert_type, message, 
               datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def load_alerts(site_url=None):
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT * FROM alerts WHERE is_read = 0"
    if site_url:
        query += f" AND site_url = '{site_url}'"
    query += " ORDER BY created_at DESC LIMIT 50"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

if __name__ == '__main__':
    init_db()