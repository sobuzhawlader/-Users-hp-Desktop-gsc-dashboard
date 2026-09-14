"""
keyword_clustering.py
Semantic Keyword Clustering Engine (NLP Topic Silos & Content Gaps)
100% Free - Pure Python & NumPy NLP Vectorization, No Paid APIs
"""

import re
from collections import Counter
import pandas as pd
import numpy as np

STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 
    'any', 'are', 'aren', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 
    'below', 'between', 'both', 'but', 'by', 'can', 'could', 'did', 'do', 'does', 
    'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 
    'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 
    'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'isn', 'it', 'its', 
    'itself', 'just', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 
    'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 
    'ourselves', 'out', 'over', 'own', 's', 'same', 'she', 'should', 'so', 'some', 
    'such', 't', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 
    'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 
    'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 
    'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'you', 'your', 'yours'
}

def clean_tokens(text: str) -> list:
    """Tokenizes text into meaningful root keywords."""
    words = re.findall(r'\b[a-zA-Z0-9]{2,}\b', str(text).lower())
    return [w for w in words if w not in STOP_WORDS]

def cluster_keywords(df: pd.DataFrame, min_cluster_size: int = 2) -> tuple:
    """
    Groups GSC search queries into semantic topic clusters using NLP token co-occurrence.
    Returns: (summary_df, detailed_df)
    """
    if df.empty or 'query' not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    # Aggregate by query first in case rows are split
    df_c = df.copy()
    has_pos = 'position' in df_c.columns and 'impressions' in df_c.columns
    if has_pos:
        df_c['_pos_imp'] = df_c['position'] * df_c['impressions']
    
    agg_dict = {
        'clicks': 'sum',
        'impressions': 'sum',
    }
    if has_pos:
        agg_dict['_pos_imp'] = 'sum'
    if 'page' in df_c.columns:
        agg_dict['page'] = lambda x: x.iloc[0] if not x.empty else ""

    q_df = df_c.groupby('query').agg(agg_dict).reset_index()
    q_df['tokens'] = q_df['query'].apply(clean_tokens)
    q_df['ctr'] = np.where(q_df['impressions'] > 0, ((q_df['clicks'] / q_df['impressions']) * 100).round(2), 0.0)
    if has_pos:
        q_df['position'] = np.where(q_df['impressions'] > 0, (q_df['_pos_imp'] / q_df['impressions']).round(1), 0.0)
        q_df.drop(columns=['_pos_imp'], inplace=True)
    else:
        q_df['position'] = 0.0

    # 1. Mine most frequent bigrams and unigrams to form Cluster Themes
    token_freq = Counter()
    bigram_freq = Counter()

    for tokens in q_df['tokens']:
        for t in tokens:
            token_freq[t] += 1
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            bigram_freq[bigram] += 1

    # Candidate theme anchors (bigrams with count >= 2, or high-freq unigrams)
    theme_candidates = [b for b, c in bigram_freq.most_common(50) if c >= min_cluster_size]
    theme_candidates += [u for u, c in token_freq.most_common(50) if c >= min_cluster_size]

    # Assign each query to the best fitting candidate theme
    assigned_clusters = []
    for _, row in q_df.iterrows():
        tokens = set(row['tokens'])
        q_text = row['query'].lower()

        assigned_theme = None
        for cand in theme_candidates:
            cand_tokens = set(cand.split())
            if cand in q_text or cand_tokens.issubset(tokens):
                assigned_theme = cand.title()
                break

        if not assigned_theme and row['tokens']:
            assigned_theme = row['tokens'][0].title()
        elif not assigned_theme:
            assigned_theme = "General Search"

        assigned_clusters.append(assigned_theme)

    q_df['cluster'] = assigned_clusters

    # Filter small orphaned clusters if desired, or merge singletons
    cluster_counts = q_df['cluster'].value_counts()
    q_df['cluster'] = q_df['cluster'].apply(
        lambda c: c if cluster_counts.get(c, 0) >= min_cluster_size else "Other Niche Queries"
    )

    # Build Summary DataFrame
    summary_records = []
    for cluster_name, group in q_df.groupby('cluster'):
        total_queries = len(group)
        tot_clicks = int(group['clicks'].sum())
        tot_impr = int(group['impressions'].sum())
        if 'position' in group.columns and tot_impr > 0:
            avg_pos = round(float((group['position'] * group['impressions']).sum() / tot_impr), 1)
        else:
            avg_pos = round(group['position'].mean(), 1) if 'position' in group.columns else 0.0
        avg_ctr = round((tot_clicks / tot_impr * 100), 2) if tot_impr > 0 else 0.0

        # Dominant URL if page exists
        dominant_url = ""
        if 'page' in group.columns:
            top_page_series = group.sort_values(by='impressions', ascending=False)['page']
            if not top_page_series.empty:
                dominant_url = top_page_series.iloc[0]

        # Top 3 queries
        top_queries = group.sort_values(by='impressions', ascending=False)['query'].head(3).tolist()

        # Content Gaps: queries in cluster with high impressions (> median) but poor rank (> 10)
        median_imp = group['impressions'].median()
        gaps = group[(group['impressions'] >= median_imp) & (group['position'] > 10.0)]
        gap_keywords = gaps['query'].head(3).tolist()

        summary_records.append({
            'Cluster Theme': cluster_name,
            'Total Keywords': total_queries,
            'Total Clicks': tot_clicks,
            'Total Impressions': tot_impr,
            'Avg CTR %': avg_ctr,
            'Avg Position': avg_pos,
            'Dominant URL': dominant_url,
            'Top Keywords': ", ".join(top_queries),
            'Content Gap Opportunities': ", ".join(gap_keywords) if gap_keywords else "No immediate gaps"
        })

    summary_df = pd.DataFrame(summary_records)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(by=['Total Impressions', 'Total Clicks'], ascending=[False, False])

    detailed_df = q_df[['cluster', 'query', 'clicks', 'impressions', 'ctr', 'position'] + (['page'] if 'page' in q_df.columns else [])]
    detailed_df = detailed_df.sort_values(by=['cluster', 'impressions'], ascending=[True, False])

    return summary_df, detailed_df
