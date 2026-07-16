"""
IW-04 DuckDuckGoSearch — DuckDuckGo Search sans tracking
Iron Warrior #4 — Privacy-first, pas de log.
Aucun équivalent dédié sur RapidAPI.
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
sys.path.insert(0, '/home/user/iron_warriors/shared')
from base import (
    create_app, fetch_html, SearchResult, SERPResponse,
    clean_text, get_timestamp, measure_latency
)
import time

app = create_app("IW-04 DuckDuckGoSearch", "DuckDuckGo search — privacy-first, no tracking")

@app.get("/search", response_model=SERPResponse)
async def ddg_search(
    q: str = Query(..., description="Search query"),
    num: int = Query(10, ge=1, le=50),
    region: str = Query("wt-wt", description="Region (wt-wt=global, us-en, fr-fr...)"),
):
    start = time.time()
    # DDG HTML endpoint (no JS required)
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}&kl={region}"
    try:
        html = await fetch_html(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"DDG fetch failed: {e}")

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()

    # DDG results — div.result
    for div in soup.find_all('div', class_='result'):
        title_tag = div.find('a', class_='result__a')
        snippet_tag = div.find('a', class_='result__snippet') or div.find('div', class_='result__snippet')
        if title_tag and title_tag.get('href'):
            href = title_tag['href']
            # DDG wraps URLs in redirect
            if 'uddg=' in href:
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                href = params.get('uddg', [href])[0]
            if href in seen:
                continue
            seen.add(href)
            results.append(SearchResult(
                title=clean_text(title_tag.get_text()),
                url=href,
                snippet=clean_text(snippet_tag.get_text()) if snippet_tag else "",
                position=len(results) + 1,
            ))
            if len(results) >= num:
                break

    return SERPResponse(
        query=q, engine="duckduckgo",
        results=results,
        timestamp=get_timestamp(), latency_ms=measure_latency(start),
    )
