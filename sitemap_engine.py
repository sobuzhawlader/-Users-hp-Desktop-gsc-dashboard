import pandas as pd
from typing import Dict, Any, List

def list_sitemaps(service, site_url: str) -> pd.DataFrame:
    """
    Retrieves all submitted sitemaps and their current health/indexing status for a GSC property.
    """
    if not service:
        return pd.DataFrame()

    try:
        response = service.sitemaps().list(siteUrl=site_url).execute()
        sitemaps_list = response.get('sitemap', [])

        records = []
        for s in sitemaps_list:
            contents = s.get('contents', [])
            submitted_urls = 0
            indexed_urls = 0
            for c in contents:
                submitted_urls += int(c.get('submitted', 0))
                indexed_urls += int(c.get('indexed', 0))

            records.append({
                'sitemap_path': s.get('path', ''),
                'last_submitted': s.get('lastSubmitted', 'N/A'),
                'last_downloaded': s.get('lastDownloaded', 'N/A'),
                'is_pending': "⏳ Yes" if s.get('isPending') else "✅ Processed",
                'is_index': "Yes" if s.get('isSitemapsIndex') else "No",
                'errors': int(s.get('errors', 0)),
                'warnings': int(s.get('warnings', 0)),
                'submitted_urls': submitted_urls,
                'indexed_urls': indexed_urls
            })

        return pd.DataFrame(records)
    except Exception as e:
        print(f"Error listing sitemaps: {e}")
        return pd.DataFrame()

def submit_sitemap(service, site_url: str, feedpath: str) -> Dict[str, Any]:
    """Submits a new sitemap URL to Google Search Console."""
    if not service:
        return {'success': False, 'message': 'GSC service not connected.'}

    cleaned_path = feedpath.strip()
    if not cleaned_path:
        return {'success': False, 'message': 'Sitemap URL cannot be empty.'}

    try:
        service.sitemaps().submit(siteUrl=site_url, feedpath=cleaned_path).execute()
        return {'success': True, 'message': f"Sitemap successfully submitted to {site_url}: {cleaned_path}"}
    except Exception as e:
        return {'success': False, 'message': f"Submission failed: {str(e)}"}

def delete_sitemap(service, site_url: str, feedpath: str) -> Dict[str, Any]:
    """Deletes an existing sitemap from Google Search Console."""
    if not service:
        return {'success': False, 'message': 'GSC service not connected.'}

    try:
        service.sitemaps().delete(siteUrl=site_url, feedpath=feedpath.strip()).execute()
        return {'success': True, 'message': f"Sitemap deleted: {feedpath}"}
    except Exception as e:
        return {'success': False, 'message': f"Deletion failed: {str(e)}"}
