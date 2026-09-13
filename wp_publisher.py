"""
wp_publisher.py
WordPress REST API 1-Click Direct Publishing & Meta Auto-Fix Engine
100% Free - Uses Native WordPress Core Application Passwords (Zero Paid Plugins)
"""

import requests
import json
import base64

def get_wp_auth_header(username: str, app_password: str) -> dict:
    """Generates standard HTTP Basic Authentication header for WordPress REST API."""
    # Strip whitespace from app password
    clean_pw = app_password.replace(" ", "").strip()
    token = f"{username.strip()}:{clean_pw}"
    encoded = base64.b64encode(token.encode('utf-8')).decode('utf-8')
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }

def test_wp_connection(site_url: str, username: str, app_password: str) -> dict:
    """Tests connection to WordPress via /wp-json/wp/v2/users/me."""
    site_url = site_url.rstrip('/')
    if not site_url.startswith(('http://', 'https://')):
        site_url = 'https://' + site_url

    endpoint = f"{site_url}/wp-json/wp/v2/users/me"
    headers = get_wp_auth_header(username, app_password)

    try:
        resp = requests.get(endpoint, headers=headers, timeout=10)
        if resp.status_code == 200:
            user_data = resp.json()
            return {
                "success": True,
                "user_name": user_data.get("name", username),
                "roles": user_data.get("roles", ["editor"]),
                "site_url": site_url
            }
        else:
            return {
                "success": False,
                "error": f"WordPress returned HTTP {resp.status_code}: {resp.text[:150]}"
            }
    except Exception as ex:
        return {"success": False, "error": str(ex)}

def get_wp_posts(site_url: str, username: str, app_password: str, per_page: int = 15) -> list:
    """Fetches recent WordPress posts for SEO metadata inspection."""
    site_url = site_url.rstrip('/')
    if not site_url.startswith(('http://', 'https://')):
        site_url = 'https://' + site_url

    endpoint = f"{site_url}/wp-json/wp/v2/posts?per_page={per_page}&_fields=id,date,title,link,status,excerpt,meta"
    headers = get_wp_auth_header(username, app_password)

    try:
        resp = requests.get(endpoint, headers=headers, timeout=12)
        if resp.status_code == 200:
            posts = resp.json()
            formatted = []
            for p in posts:
                formatted.append({
                    "id": p.get("id"),
                    "title": p.get("title", {}).get("rendered", "Untitled"),
                    "link": p.get("link", ""),
                    "status": p.get("status", "publish"),
                    "date": p.get("date", "")[:10],
                    "excerpt": p.get("excerpt", {}).get("rendered", "")
                })
            return formatted
    except Exception:
        pass
    return []

def update_wp_post_metadata(site_url: str, username: str, app_password: str, post_id: int, new_title: str = None, new_description: str = None) -> dict:
    """
    Updates post title and meta description directly via WP REST API.
    Injects into standard excerpt + Yoast/RankMath meta fields.
    """
    site_url = site_url.rstrip('/')
    if not site_url.startswith(('http://', 'https://')):
        site_url = 'https://' + site_url

    endpoint = f"{site_url}/wp-json/wp/v2/posts/{post_id}"
    headers = get_wp_auth_header(username, app_password)

    payload = {}
    if new_title:
        payload["title"] = new_title.strip()
    if new_description:
        payload["excerpt"] = new_description.strip()
        # Also attempt custom meta fields for Yoast and RankMath
        payload["meta"] = {
            "_yoast_wpseo_title": new_title or "",
            "_yoast_wpseo_metadesc": new_description or "",
            "rank_math_title": new_title or "",
            "rank_math_description": new_description or ""
        }

    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=12)
        if resp.status_code in (200, 201):
            return {"success": True, "post_id": post_id, "data": resp.json()}
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as ex:
        return {"success": False, "error": str(ex)}

def publish_wp_article(site_url: str, username: str, app_password: str, title: str, content: str, status: str = "draft", tags: list = None) -> dict:
    """Creates a new post or SEO case study in WordPress."""
    site_url = site_url.rstrip('/')
    if not site_url.startswith(('http://', 'https://')):
        site_url = 'https://' + site_url

    endpoint = f"{site_url}/wp-json/wp/v2/posts"
    headers = get_wp_auth_header(username, app_password)

    payload = {
        "title": title.strip(),
        "content": content.strip(),
        "status": status.lower()
    }

    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            created = resp.json()
            return {
                "success": True,
                "post_id": created.get("id"),
                "link": created.get("link"),
                "status": created.get("status")
            }
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as ex:
        return {"success": False, "error": str(ex)}
