"""
crawler_auditor.py
On-Page Technical SEO Crawler & Core Web Vitals Auditor
100% Free - Zero Subscriptions, Python Multi-threaded Engine + Free Google PageSpeed API
"""

import re
import time
import requests
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

class PageSEOParser(HTMLParser):
    def __init__(self, page_url):
        super().__init__()
        self.page_url = page_url
        self.domain = urlparse(page_url).netloc
        self.in_title = False
        self.title = ""
        self.meta_desc = ""
        self.canonical = ""
        self.robots = ""
        self.og_title = ""
        self.og_desc = ""
        self.og_image = ""
        self.h1_tags = []
        self.h2_tags = []
        self.in_h1 = False
        self.in_h2 = False
        self.images_total = 0
        self.images_no_alt = 0
        self.internal_links = set()
        self.external_links = set()

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag == 'title':
            self.in_title = True
        elif tag == 'h1':
            self.in_h1 = True
        elif tag == 'h2':
            self.in_h2 = True
        elif tag == 'meta':
            name = attr_dict.get('name', '').lower()
            prop = attr_dict.get('property', '').lower()
            content = attr_dict.get('content', '')

            if name == 'description':
                self.meta_desc = content
            elif name == 'robots':
                self.robots = content
            elif prop == 'og:title':
                self.og_title = content
            elif prop == 'og:description':
                self.og_desc = content
            elif prop == 'og:image':
                self.og_image = content
        elif tag == 'link':
            rel = attr_dict.get('rel', '').lower()
            if 'canonical' in rel:
                self.canonical = attr_dict.get('href', '')
        elif tag == 'img':
            self.images_total += 1
            alt = attr_dict.get('alt', None)
            if alt is None or not alt.strip():
                self.images_no_alt += 1
        elif tag == 'a':
            href = attr_dict.get('href', '').strip()
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                full_url = urljoin(self.page_url, href).split('#')[0]
                parsed = urlparse(full_url)
                if parsed.scheme in ('http', 'https'):
                    if parsed.netloc == self.domain:
                        self.internal_links.add(full_url)
                    else:
                        self.external_links.add(full_url)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'title':
            self.in_title = False
        elif tag == 'h1':
            self.in_h1 = False
        elif tag == 'h2':
            self.in_h2 = False

    def handle_data(self, data):
        if self.in_title and not self.title:
            self.title += data.strip()
        elif self.in_h1:
            t = data.strip()
            if t:
                self.h1_tags.append(t)
        elif self.in_h2:
            t = data.strip()
            if t:
                self.h2_tags.append(t)

def crawl_single_page(url: str, timeout: int = 8) -> dict:
    """Fetches and parses a single URL for technical SEO metrics."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 GSC-Terminal-Crawler/2.0'
    }
    start_t = time.time()
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        latency_ms = int((time.time() - start_t) * 1000)
        status_code = resp.status_code
        content_type = resp.headers.get('content-type', '').lower()

        if 'text/html' not in content_type:
            return {
                'url': url,
                'status_code': status_code,
                'latency_ms': latency_ms,
                'content_type': content_type,
                'title': '',
                'title_len': 0,
                'meta_desc': '',
                'desc_len': 0,
                'h1_count': 0,
                'h1_text': '',
                'canonical': '',
                'robots': '',
                'images_no_alt': 0,
                'issues': ['Non-HTML Content'],
                'internal_links': set()
            }

        parser = PageSEOParser(resp.url)
        parser.feed(resp.text[:250000]) # parse first 250KB

        issues = []
        if status_code >= 400:
            issues.append(f"HTTP Error {status_code}")
        if not parser.title:
            issues.append("Missing Title")
        elif len(parser.title) < 30:
            issues.append("Short Title (<30 chars)")
        elif len(parser.title) > 65:
            issues.append("Long Title (>65 chars)")

        if not parser.meta_desc:
            issues.append("Missing Meta Description")
        elif len(parser.meta_desc) < 70:
            issues.append("Short Meta Description (<70 chars)")
        elif len(parser.meta_desc) > 165:
            issues.append("Long Meta Description (>165 chars)")

        if len(parser.h1_tags) == 0:
            issues.append("Missing H1")
        elif len(parser.h1_tags) > 1:
            issues.append(f"Multiple H1s ({len(parser.h1_tags)})")

        if parser.images_no_alt > 0:
            issues.append(f"{parser.images_no_alt} Images Missing ALT")

        if 'noindex' in parser.robots.lower():
            issues.append("NoIndex Directive")

        return {
            'url': url,
            'final_url': resp.url,
            'status_code': status_code,
            'latency_ms': latency_ms,
            'title': parser.title,
            'title_len': len(parser.title),
            'meta_desc': parser.meta_desc,
            'desc_len': len(parser.meta_desc),
            'h1_count': len(parser.h1_tags),
            'h1_text': parser.h1_tags[0] if parser.h1_tags else '',
            'canonical': parser.canonical,
            'robots': parser.robots,
            'og_title': parser.og_title,
            'og_image': parser.og_image,
            'images_total': parser.images_total,
            'images_no_alt': parser.images_no_alt,
            'issues': issues,
            'issue_count': len(issues),
            'internal_links': parser.internal_links
        }
    except Exception as ex:
        return {
            'url': url,
            'status_code': 0,
            'latency_ms': int((time.time() - start_t) * 1000),
            'title': '',
            'title_len': 0,
            'meta_desc': '',
            'desc_len': 0,
            'h1_count': 0,
            'h1_text': '',
            'canonical': '',
            'robots': '',
            'images_no_alt': 0,
            'issues': [f"Connection Failed: {str(ex)[:40]}"],
            'issue_count': 1,
            'internal_links': set()
        }

def crawl_website(start_url: str, max_pages: int = 25, max_workers: int = 5) -> pd.DataFrame:
    """
    Crawls internal website URLs starting from root up to max_pages.
    Returns structured DataFrame of technical SEO diagnostics.
    """
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url

    visited = set()
    queue = [start_url]
    results = []

    domain = urlparse(start_url).netloc

    while queue and len(visited) < max_pages:
        batch_urls = []
        while queue and len(batch_urls) < max_workers and (len(visited) + len(batch_urls)) < max_pages:
            next_url = queue.pop(0)
            if next_url not in visited and next_url not in batch_urls:
                batch_urls.append(next_url)

        if not batch_urls:
            break

        with ThreadPoolExecutor(max_workers=len(batch_urls)) as executor:
            future_to_url = {executor.submit(crawl_single_page, u): u for u in batch_urls}
            for future in as_completed(future_to_url):
                res = future.result()
                visited.add(res['url'])
                results.append(res)
                
                # Discover new internal URLs
                for link in res.get('internal_links', set()):
                    if link not in visited and link not in queue and urlparse(link).netloc == domain:
                        # Avoid crawling feeds, wp-admin, or assets
                        if not any(skip in link.lower() for skip in ['/feed', '/wp-admin', '/wp-content', '.jpg', '.png', '.pdf', '.css', '.js']):
                            queue.append(link)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    # Convert sets or lists to string representation for table view
    df['issues_display'] = df['issues'].apply(lambda x: ", ".join(x) if x else "✅ Clean")
    return df

def audit_core_web_vitals(url: str, strategy: str = "mobile", api_key: str = None) -> dict:
    """
    Fetches real-time Core Web Vitals & Lighthouse Scores via Google PageSpeed Insights API.
    100% Free - Up to 25,000 requests/day without billing.
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy={strategy}"
    endpoint += "&category=PERFORMANCE&category=SEO&category=ACCESSIBILITY&category=BEST_PRACTICES"
    if api_key:
        endpoint += f"&key={api_key}"

    try:
        resp = requests.get(endpoint, timeout=25)
        if resp.status_code != 200:
            return {"success": False, "error": f"PageSpeed API returned HTTP {resp.status_code}"}

        data = resp.json()
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})

        scores = {
            "performance": int((categories.get("performance", {}).get("score", 0) or 0) * 100),
            "seo": int((categories.get("seo", {}).get("score", 0) or 0) * 100),
            "accessibility": int((categories.get("accessibility", {}).get("score", 0) or 0) * 100),
            "best_practices": int((categories.get("best-practices", {}).get("score", 0) or 0) * 100)
        }

        # Core Web Vitals Metrics
        metrics = {
            "lcp": audits.get("largest-contentful-paint", {}).get("displayValue", "N/A"),
            "cls": audits.get("cumulative-layout-shift", {}).get("displayValue", "N/A"),
            "fcp": audits.get("first-contentful-paint", {}).get("displayValue", "N/A"),
            "speed_index": audits.get("speed-index", {}).get("displayValue", "N/A"),
            "tbt": audits.get("total-blocking-time", {}).get("displayValue", "N/A"),
        }

        # Top diagnostic opportunities
        opportunities = []
        for key in ["render-blocking-resources", "unused-css-rules", "unused-javascript", "modern-image-formats", "offscreen-images"]:
            item = audits.get(key, {})
            if item and item.get("score", 1.0) is not None and item.get("score", 1.0) < 0.9:
                opportunities.append({
                    "title": item.get("title", key),
                    "savings": item.get("displayValue", "Opportunity"),
                    "description": item.get("description", "")
                })

        return {
            "success": True,
            "url": url,
            "strategy": strategy,
            "scores": scores,
            "metrics": metrics,
            "opportunities": opportunities[:5]
        }
    except Exception as ex:
        return {"success": False, "error": str(ex)}
