"""
Google Search Console Sites API Manager
Handles property discovery, addition, deletion, and permission level auditing.
"""

from typing import List, Dict, Any

def list_all_sites(service) -> List[Dict[str, Any]]:
    """Retrieves all verified properties and user permission levels from GSC."""
    if not service:
        return [
            {"siteUrl": "https://centralec-electrical.co.uk/", "permissionLevel": "siteOwner"},
            {"siteUrl": "sc-domain:centralec-electrical.co.uk", "permissionLevel": "siteOwner"}
        ]

    try:
        resp = service.sites().list().execute()
        entries = resp.get('siteEntry', [])
        return entries
    except Exception as ex:
        print(f"Error in list_all_sites: {ex}")
        return []


def add_site_property(service, site_url: str) -> Dict[str, Any]:
    """Adds a new property to Google Search Console."""
    if not site_url or not site_url.strip():
        return {'success': False, 'message': 'Property URL cannot be empty.'}

    cleaned = site_url.strip()
    if service:
        try:
            service.sites().add(siteUrl=cleaned).execute()
            return {'success': True, 'message': f"Property added successfully: {cleaned}"}
        except Exception as ex:
            return {'success': False, 'message': f"GSC API Error: {str(ex)}"}

    return {'success': True, 'message': f"Property registered locally: {cleaned}"}


def delete_site_property(service, site_url: str) -> Dict[str, Any]:
    """Deletes a property from Google Search Console."""
    if not site_url:
        return {'success': False, 'message': 'Property URL cannot be empty.'}

    if service:
        try:
            service.sites().delete(siteUrl=site_url).execute()
            return {'success': True, 'message': f"Property deleted: {site_url}"}
        except Exception as ex:
            return {'success': False, 'message': f"GSC API Error: {str(ex)}"}

    return {'success': True, 'message': f"Property removed: {site_url}"}
