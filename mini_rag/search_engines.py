"""
Web search engine integrations for Mini RAG research.

Supports multiple search engines with a unified interface.
DuckDuckGo is the default (no API key required).
Tavily and Brave require API keys.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Protocol

import requests

logger = logging.getLogger(__name__)

# Optional: duckduckgo-search package
try:
    from duckduckgo_search import DDGS

    DDGS_AVAILABLE = True
except ImportError:
    DDGS = None
    DDGS_AVAILABLE = False


@dataclass
class WebSearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str


class SearchEngine(Protocol):
    """Protocol for web search engines."""

    def search(self, query: str, max_results: int = 10) -> List[WebSearchResult]: ...


class DuckDuckGoSearch:
    """DuckDuckGo search with package + HTML fallback.

    Primary: uses duckduckgo-search package (if installed)
    Fallback: scrapes DuckDuckGo HTML directly via requests
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

    def search(self, query: str, max_results: int = 10) -> List[WebSearchResult]:
        """Search DuckDuckGo. Tries package first, falls back to HTML scraping."""
        if DDGS_AVAILABLE:
            results = self._search_with_package(query, max_results)
            if results:
                return results
            logger.debug("DDGS package returned no results, trying HTML fallback")

        return self._search_html_fallback(query, max_results)

    def _search_with_package(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Search using the duckduckgo-search package."""
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

            results = []
            for r in raw_results:
                results.append(WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", r.get("link", "")),
                    snippet=r.get("body", r.get("snippet", "")),
                ))
            return results

        except Exception as e:
            logger.warning(f"DuckDuckGo package search failed: {e}")
            return []

    def _search_html_fallback(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Scrape DuckDuckGo HTML search results directly.

        This is the fallback when duckduckgo-search is not installed or fails.
        Less reliable but works with zero dependencies beyond requests.
        """
        try:
            resp = self._session.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                timeout=15,
            )
            resp.raise_for_status()

            # Parse with bs4 if available, otherwise regex
            try:
                from bs4 import BeautifulSoup

                return self._parse_ddg_with_bs4(resp.text, max_results)
            except ImportError:
                return self._parse_ddg_with_regex(resp.text, max_results)

        except Exception as e:
            logger.warning(f"DuckDuckGo HTML fallback failed: {e}")
            return []

    def _parse_ddg_with_bs4(self, html: str, max_results: int) -> List[WebSearchResult]:
        """Parse DuckDuckGo HTML results with BeautifulSoup."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        results = []

        for result_div in soup.select(".result")[:max_results]:
            link = result_div.select_one(".result__a")
            snippet_el = result_div.select_one(".result__snippet")

            if link and link.get("href"):
                url = link["href"]
                # DDG wraps URLs in a redirect — extract the actual URL
                if "uddg=" in url:
                    from urllib.parse import parse_qs, urlparse

                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    url = params.get("uddg", [url])[0]

                results.append(WebSearchResult(
                    title=link.get_text(strip=True),
                    url=url,
                    snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                ))

        return results

    def _parse_ddg_with_regex(self, html: str, max_results: int) -> List[WebSearchResult]:
        """Parse DuckDuckGo HTML results with regex (last resort fallback)."""
        results = []

        # Match result links: <a class="result__a" href="...">title</a>
        pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
        )
        snippet_pattern = re.compile(
            r'class="result__snippet"[^>]*>([^<]+)<'
        )

        links = pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (url, title) in enumerate(links[:max_results]):
            # Extract actual URL from DDG redirect
            if "uddg=" in url:
                from urllib.parse import parse_qs, urlparse

                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                url = params.get("uddg", [url])[0]

            snippet = snippets[i] if i < len(snippets) else ""

            results.append(WebSearchResult(
                title=title.strip(),
                url=url,
                snippet=snippet.strip(),
            ))

        return results


class TavilySearch:
    """Tavily search engine (requires API key)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 10) -> List[WebSearchResult]:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for r in data.get("results", []):
                results.append(WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                ))
            return results

        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []


class BraveSearch:
    """Brave search engine (requires API key)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 10) -> List[WebSearchResult]:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self.api_key,
                },
                params={"q": query, "count": max_results},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for r in data.get("web", {}).get("results", []):
                results.append(WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("description", ""),
                ))
            return results

        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return []


def create_search_engine(
    engine: str = "duckduckgo",
    tavily_api_key: Optional[str] = None,
    brave_api_key: Optional[str] = None,
) -> SearchEngine:
    """Factory: create a search engine from config."""
    if engine == "tavily":
        if not tavily_api_key:
            logger.warning("Tavily API key not set, falling back to DuckDuckGo")
            return DuckDuckGoSearch()
        return TavilySearch(tavily_api_key)

    if engine == "brave":
        if not brave_api_key:
            logger.warning("Brave API key not set, falling back to DuckDuckGo")
            return DuckDuckGoSearch()
        return BraveSearch(brave_api_key)

    return DuckDuckGoSearch()
