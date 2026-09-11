import time
import pandas as pd
from typing import Dict, Any, List
from googleapiclient.errors import HttpError

def inspect_single_url(service_v1, site_url: str, inspection_url: str, lang: str = "en") -> Dict[str, Any]:
    """
    Executes a live inspection request via Google Search Console URL Inspection API.
    Returns normalized dictionary with indexing, canonical, and crawl metadata.
    """
    if not service_v1:
        raise ValueError("Search Console v1 service not initialized.")

    payload = {
        'inspectionUrl': inspection_url,
        'siteUrl': site_url,
        'languageCode': lang
    }

    retries = 3
    backoff_delay = 2.0

    for attempt in range(retries):
        try:
            response = service_v1.urlInspection().index().inspect(body=payload).execute()
            result = response.get('inspectionResult', {})
            idx_res = result.get('indexStatusResult', {})
            mobile_res = result.get('mobileUsabilityResult', {})
            rich_res = result.get('richResultsResult', {})

            user_canon = idx_res.get('userCanonical', '')
            google_canon = idx_res.get('googleCanonical', '')
            verdict = idx_res.get('verdict', 'NEUTRAL')
            coverage_state = idx_res.get('coverageState', 'Unknown')
            indexing_state = idx_res.get('indexingState', 'Unknown')
            page_fetch_state = idx_res.get('pageFetchState', 'Unknown')
            robots_txt_state = idx_res.get('robotsTxtState', 'Unknown')
            crawled_as = idx_res.get('crawledAs', 'Unknown')
            last_crawl_time = idx_res.get('lastCrawlTime', 'Never')

            # Determine Canonical Mismatch
            is_mismatch = False
            if user_canon and google_canon:
                norm_user = user_canon.strip().rstrip('/')
                norm_google = google_canon.strip().rstrip('/')
                if norm_user != norm_google:
                    is_mismatch = True

            return {
                'url': inspection_url,
                'verdict': verdict,
                'coverage_state': coverage_state,
                'indexing_state': indexing_state,
                'page_fetch_state': page_fetch_state,
                'robots_txt_state': robots_txt_state,
                'user_canonical': user_canon or 'Not Declared',
                'google_canonical': google_canon or 'None',
                'canonical_mismatch': "⚠️ MISMATCH" if is_mismatch else "✅ MATCH",
                'last_crawl_time': last_crawl_time,
                'crawled_as': crawled_as,
                'mobile_verdict': mobile_res.get('verdict', 'N/A'),
                'rich_results_verdict': rich_res.get('verdict', 'N/A')
            }

        except HttpError as err:
            if err.resp.status_code in [429, 503]:
                sleep_sec = (backoff_delay ** attempt) + 0.5
                time.sleep(sleep_sec)
            else:
                return {
                    'url': inspection_url,
                    'verdict': 'ERROR',
                    'coverage_state': f"HTTP {err.resp.status_code}: {err._get_reason()}",
                    'indexing_state': 'ERROR',
                    'page_fetch_state': 'ERROR',
                    'robots_txt_state': 'UNKNOWN',
                    'user_canonical': 'N/A',
                    'google_canonical': 'N/A',
                    'canonical_mismatch': 'N/A',
                    'last_crawl_time': 'N/A',
                    'crawled_as': 'N/A',
                    'mobile_verdict': 'N/A',
                    'rich_results_verdict': 'N/A'
                }
        except Exception as e:
            return {
                'url': inspection_url,
                'verdict': 'ERROR',
                'coverage_state': str(e),
                'indexing_state': 'ERROR',
                'page_fetch_state': 'ERROR',
                'robots_txt_state': 'UNKNOWN',
                'user_canonical': 'N/A',
                'google_canonical': 'N/A',
                'canonical_mismatch': 'N/A',
                'last_crawl_time': 'N/A',
                'crawled_as': 'N/A',
                'mobile_verdict': 'N/A',
                'rich_results_verdict': 'N/A'
            }

    return {
        'url': inspection_url,
        'verdict': 'TIMEOUT',
        'coverage_state': 'Rate limit exceeded after retries',
        'indexing_state': 'ERROR',
        'page_fetch_state': 'ERROR',
        'robots_txt_state': 'UNKNOWN',
        'user_canonical': 'N/A',
        'google_canonical': 'N/A',
        'canonical_mismatch': 'N/A',
        'last_crawl_time': 'N/A',
        'crawled_as': 'N/A',
        'mobile_verdict': 'N/A',
        'rich_results_verdict': 'N/A'
    }

def inspect_bulk_urls(service_v1, site_url: str, urls_list: List[str], progress_callback=None) -> pd.DataFrame:
    """
    Iterates over a list of URLs and inspects them in bulk.
    Yields or reports progress and returns a consolidated DataFrame.
    """
    results = []
    total = len(urls_list)

    for idx, u in enumerate(urls_list):
        cleaned_url = u.strip()
        if not cleaned_url or not cleaned_url.startswith('http'):
            continue
        data = inspect_single_url(service_v1, site_url, cleaned_url)
        results.append(data)
        if progress_callback:
            progress_callback(idx + 1, total)
        # Gentle rate limit throttle
        time.sleep(0.3)

    return pd.DataFrame(results)
