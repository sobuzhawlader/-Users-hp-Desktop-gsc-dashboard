"""
ai_meta_generator.py
AI High-CTR Meta Title & Description + JSON-LD Schema Studio
100% Free - Algorithmic Heuristic Copywriting Engine + Optional Gemini Free API + Google Schema Validator
"""

import re
import json
from datetime import datetime
import requests

CURRENT_YEAR = datetime.now().year

def generate_high_ctr_metadata(keyword: str, page_type: str = "blog", site_brand: str = "", gemini_api_key: str = None) -> list:
    """
    Generates high-CTR Title & Meta Description variations.
    Uses Algorithmic Heuristic Copywriting Engine (100% Free) or Gemini Free API if provided.
    """
    keyword_clean = keyword.strip().title()
    brand_suffix = f" | {site_brand.strip()}" if site_brand.strip() else ""

    # Check if user provided Gemini API Key
    if gemini_api_key and len(gemini_api_key.strip()) > 10:
        try:
            gemini_res = _generate_with_gemini(keyword_clean, page_type, site_brand, gemini_api_key)
            if gemini_res:
                return gemini_res
        except Exception:
            pass # fallback to local heuristic engine

    # Algorithmic High-CTR Copywriting Engine
    variations = []

    # Variation 1: High Click-Through & Power Hook
    v1_title = f"{keyword_clean}: The Definitive Guide [{CURRENT_YEAR}]{brand_suffix}"
    if len(v1_title) > 60 and brand_suffix:
        v1_title = f"{keyword_clean}: The Definitive Guide [{CURRENT_YEAR}]"
    v1_desc = f"Master {keyword_clean.lower()} with proven strategies, insider tips, and actionable steps. Boost your results today. Read the full expert breakdown!"
    variations.append({
        "style": "⚡ High CTR & Power Hook",
        "title": v1_title[:60],
        "title_length": len(v1_title[:60]),
        "description": v1_desc[:160],
        "desc_length": len(v1_desc[:160]),
        "ctr_formula": "Keyword + Bracket Year + High-Value Modifier"
    })

    # Variation 2: Actionable Step-by-Step Blueprint
    v2_title = f"How to Master {keyword_clean} in {CURRENT_YEAR} (Step-by-Step){brand_suffix}"
    if len(v2_title) > 60 and brand_suffix:
        v2_title = f"How to Master {keyword_clean} in {CURRENT_YEAR} (Step-by-Step)"
    v2_desc = f"Looking for practical solutions for {keyword_clean.lower()}? Follow our verified step-by-step tutorial designed to save you hours and maximize performance."
    variations.append({
        "style": "🎯 Actionable Step-by-Step",
        "title": v2_title[:60],
        "title_length": len(v2_title[:60]),
        "description": v2_desc[:160],
        "desc_length": len(v2_desc[:160]),
        "ctr_formula": "Problem Solver + Tutorial Hook + Parenthesis Clarifier"
    })

    # Variation 3: Commercial / Comparative Intent
    v3_title = f"Top 10 Best {keyword_clean} Tools & Strategies Reviewed{brand_suffix}"
    if len(v3_title) > 60 and brand_suffix:
        v3_title = f"Best {keyword_clean} Tools & Strategies Reviewed [{CURRENT_YEAR}]"
    v3_desc = f"Compare top-rated options for {keyword_clean.lower()}. Unbiased benchmarks, real user feedback, and pricing insights to make the right choice."
    variations.append({
        "style": "🏆 Comparison & Best List",
        "title": v3_title[:60],
        "title_length": len(v3_title[:60]),
        "description": v3_desc[:160],
        "desc_length": len(v3_desc[:160]),
        "ctr_formula": "Social Proof + Ranked Benchmark + Decision Enabler"
    })

    # Variation 4: Direct Benefit / Pain-Point Relief
    v4_title = f"{keyword_clean} Made Easy: Fast Results in {CURRENT_YEAR}{brand_suffix}"
    if len(v4_title) > 60 and brand_suffix:
        v4_title = f"{keyword_clean} Made Simple: Fast Results [{CURRENT_YEAR}]"
    v4_desc = f"Stop struggling with {keyword_clean.lower()}. Discover effortless, automated ways to achieve top performance with zero technical headaches."
    variations.append({
        "style": "💡 Pain-Point & Fast Relief",
        "title": v4_title[:60],
        "title_length": len(v4_title[:60]),
        "description": v4_desc[:160],
        "desc_length": len(v4_desc[:160]),
        "ctr_formula": "Friction Reduction + Speed Guarantee + Simplicity"
    })

    return variations

def _generate_with_gemini(keyword: str, page_type: str, site_brand: str, api_key: str) -> list:
    """Invokes Google Gemini Free Tier API for high-converting SEO copy."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key.strip()}"
    prompt = f"""You are an elite enterprise SEO copywriter.
Generate 3 distinct high-CTR Title and Meta Description options for the keyword: "{keyword}".
Brand name (optional): "{site_brand}".
Rules:
- Title must be between 45 and 60 characters.
- Meta Description must be between 140 and 155 characters.
- Include emotional hooks, brackets, or numbers to maximize CTR.
Output ONLY a JSON array with schema:
[
  {{"style": "Style Name", "title": "Title Here", "description": "Meta description here", "ctr_formula": "Brief explanation"}}
]"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, json=payload, timeout=12)
    if resp.status_code == 200:
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        # extract json array
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            for item in data:
                item["title_length"] = len(item.get("title", ""))
                item["desc_length"] = len(item.get("description", ""))
            return data
    return None

def generate_schema_jsonld(schema_type: str, data: dict) -> str:
    """
    Generates Google-valid JSON-LD markup.
    Supported types: FAQPage, Article, HowTo, Product, LocalBusiness, BreadcrumbList, Organization
    """
    schema_type = schema_type.strip()

    if schema_type == "FAQPage":
        # expects data['qa_pairs'] = [('question', 'answer'), ...]
        qa_list = data.get('qa_pairs', [])
        entities = []
        for q, a in qa_list:
            if q.strip() and a.strip():
                entities.append({
                    "@type": "Question",
                    "name": q.strip(),
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": a.strip()
                    }
                })
        schema_obj = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": entities
        }

    elif schema_type in ("Article", "BlogPosting"):
        schema_obj = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "headline": data.get("headline", ""),
            "description": data.get("description", ""),
            "image": data.get("image", "https://example.com/cover.jpg"),
            "author": {
                "@type": "Person",
                "name": data.get("author_name", "Author")
            },
            "publisher": {
                "@type": "Organization",
                "name": data.get("publisher_name", "Publisher"),
                "logo": {
                    "@type": "ImageObject",
                    "url": data.get("publisher_logo", "https://example.com/logo.png")
                }
            },
            "datePublished": data.get("date_published", datetime.now().strftime("%Y-%m-%d")),
            "dateModified": datetime.now().strftime("%Y-%m-%d")
        }

    elif schema_type == "HowTo":
        steps_raw = data.get("steps", [])
        step_entities = []
        for i, (s_name, s_text) in enumerate(steps_raw, start=1):
            if s_name.strip():
                step_entities.append({
                    "@type": "HowToStep",
                    "position": i,
                    "name": s_name.strip(),
                    "text": s_text.strip()
                })
        schema_obj = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": data.get("name", "How to..."),
            "description": data.get("description", ""),
            "step": step_entities
        }

    elif schema_type == "Product":
        schema_obj = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": data.get("name", ""),
            "image": data.get("image", ""),
            "description": data.get("description", ""),
            "brand": {
                "@type": "Brand",
                "name": data.get("brand", "")
            },
            "offers": {
                "@type": "Offer",
                "url": data.get("url", ""),
                "priceCurrency": data.get("currency", "USD"),
                "price": str(data.get("price", "0.00")),
                "availability": "https://schema.org/InStock"
            }
        }
        if data.get("rating_value"):
            schema_obj["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": str(data.get("rating_value")),
                "reviewCount": str(data.get("review_count", 1))
            }

    elif schema_type == "LocalBusiness":
        schema_obj = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": data.get("name", ""),
            "image": data.get("image", ""),
            "telephone": data.get("telephone", ""),
            "url": data.get("url", ""),
            "address": {
                "@type": "PostalAddress",
                "streetAddress": data.get("street", ""),
                "addressLocality": data.get("city", ""),
                "postalCode": data.get("postal_code", ""),
                "addressCountry": data.get("country", "")
            },
            "openingHours": data.get("opening_hours", "Mo-Fr 09:00-18:00")
        }

    elif schema_type == "BreadcrumbList":
        crumbs = data.get("breadcrumbs", []) # list of (name, url)
        items = []
        for i, (c_name, c_url) in enumerate(crumbs, start=1):
            items.append({
                "@type": "ListItem",
                "position": i,
                "name": c_name,
                "item": c_url
            })
        schema_obj = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items
        }

    else: # Default Organization / WebSite
        schema_obj = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": data.get("name", ""),
            "url": data.get("url", ""),
            "logo": data.get("logo", ""),
            "sameAs": data.get("social_urls", [])
        }

    return json.dumps(schema_obj, indent=2, ensure_ascii=False)
