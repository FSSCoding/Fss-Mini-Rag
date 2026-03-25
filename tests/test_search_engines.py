"""Tests for search engines — factory, result mapping, HTML parsing."""

from unittest.mock import MagicMock, patch

import pytest

from mini_rag.search_engines import (
    BraveSearch,
    DuckDuckGoSearch,
    SerperSearch,
    TavilySearch,
    WebSearchResult,
    create_search_engine,
)


# ─── Factory / auto-selection ───


class TestCreateSearchEngine:
    def test_default_is_duckduckgo(self):
        engine = create_search_engine()
        assert isinstance(engine, DuckDuckGoSearch)

    def test_explicit_duckduckgo(self):
        engine = create_search_engine("duckduckgo")
        assert isinstance(engine, DuckDuckGoSearch)

    def test_tavily_with_key(self):
        engine = create_search_engine("tavily", tavily_api_key="test-key")
        assert isinstance(engine, TavilySearch)

    def test_tavily_without_key_falls_back(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        engine = create_search_engine("tavily")
        assert isinstance(engine, DuckDuckGoSearch)

    def test_brave_with_key(self):
        engine = create_search_engine("brave", brave_api_key="test-key")
        assert isinstance(engine, BraveSearch)

    def test_brave_without_key_falls_back(self, monkeypatch):
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        engine = create_search_engine("brave")
        assert isinstance(engine, DuckDuckGoSearch)

    def test_serper_with_key(self):
        engine = create_search_engine("serper", serper_api_key="test-key")
        assert isinstance(engine, SerperSearch)

    def test_serper_without_key_falls_back(self, monkeypatch):
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        engine = create_search_engine("serper")
        assert isinstance(engine, DuckDuckGoSearch)

    def test_auto_prefers_tavily(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tk")
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        engine = create_search_engine("auto")
        assert isinstance(engine, TavilySearch)

    def test_auto_prefers_serper_over_brave(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("SERPER_API_KEY", "sk")
        monkeypatch.setenv("BRAVE_API_KEY", "bk")
        engine = create_search_engine("auto")
        assert isinstance(engine, SerperSearch)

    def test_auto_falls_to_duckduckgo(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        engine = create_search_engine("auto")
        assert isinstance(engine, DuckDuckGoSearch)

    def test_env_var_fallback(self, monkeypatch):
        monkeypatch.setenv("BRAVE_API_KEY", "from-env")
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        engine = create_search_engine("brave")
        assert isinstance(engine, BraveSearch)


# ─── WebSearchResult ───


class TestWebSearchResult:
    def test_dataclass(self):
        r = WebSearchResult(title="Title", url="https://example.com", snippet="text")
        assert r.title == "Title"
        assert r.url == "https://example.com"
        assert r.snippet == "text"


# ─── DuckDuckGo HTML parsing ───


class TestDuckDuckGoHTMLParsing:
    @pytest.fixture
    def engine(self):
        return DuckDuckGoSearch()

    def test_parse_with_regex(self, engine):
        html = '''
        <div class="result">
            <a class="result__a" href="https://example.com/page1">Result One</a>
            <a class="result__snippet">This is the snippet for result one</a>
        </div>
        <div class="result">
            <a class="result__a" href="https://example.com/page2">Result Two</a>
            <a class="result__snippet">This is snippet two</a>
        </div>
        '''
        results = engine._parse_ddg_with_regex(html, max_results=10)
        assert len(results) == 2
        assert results[0].title == "Result One"
        assert results[0].url == "https://example.com/page1"

    def test_parse_with_regex_max_results(self, engine):
        html = '''
        <a class="result__a" href="https://a.com">A</a>
        <a class="result__snippet">SA</a>
        <a class="result__a" href="https://b.com">B</a>
        <a class="result__snippet">SB</a>
        <a class="result__a" href="https://c.com">C</a>
        <a class="result__snippet">SC</a>
        '''
        results = engine._parse_ddg_with_regex(html, max_results=2)
        assert len(results) == 2

    def test_parse_ddg_redirect_url(self, engine):
        """DDG wraps URLs in redirects — parser should extract actual URL."""
        from urllib.parse import quote
        actual_url = "https://example.com/real-page"
        ddg_url = f"https://duckduckgo.com/l/?uddg={quote(actual_url)}&rut=abc"
        html = f'<a class="result__a" href="{ddg_url}">Title</a><a class="result__snippet">Snip</a>'
        results = engine._parse_ddg_with_regex(html, max_results=10)
        assert len(results) == 1
        assert results[0].url == actual_url


# ─── Tavily result mapping ───


class TestTavilySearch:
    def test_result_mapping(self):
        engine = TavilySearch(api_key="test")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"title": "T1", "url": "https://a.com", "content": "Body 1"},
                {"title": "T2", "url": "https://b.com", "content": "Body 2"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("mini_rag.search_engines.requests.post", return_value=mock_response):
            with patch("mini_rag.search_engines.retry_with_backoff", side_effect=lambda fn, **kw: fn()):
                results = engine.search("test query", max_results=5)

        assert len(results) == 2
        assert results[0].title == "T1"
        assert results[1].url == "https://b.com"


# ─── Brave result mapping ───


class TestBraveSearch:
    def test_result_mapping(self):
        engine = BraveSearch(api_key="test")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {"title": "B1", "url": "https://brave1.com", "description": "Desc 1"},
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("mini_rag.search_engines.requests.get", return_value=mock_response):
            with patch("mini_rag.search_engines.retry_with_backoff", side_effect=lambda fn, **kw: fn()):
                results = engine.search("test", max_results=5)

        assert len(results) == 1
        assert results[0].title == "B1"
        assert results[0].snippet == "Desc 1"


# ─── Serper result mapping ───


class TestSerperSearch:
    def test_result_mapping(self):
        engine = SerperSearch(api_key="test")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "organic": [
                {"title": "S1", "link": "https://serp1.com", "snippet": "Google result"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("mini_rag.search_engines.requests.post", return_value=mock_response):
            with patch("mini_rag.search_engines.retry_with_backoff", side_effect=lambda fn, **kw: fn()):
                results = engine.search("test", max_results=5)

        assert len(results) == 1
        assert results[0].url == "https://serp1.com"
        assert results[0].snippet == "Google result"


# ─── Error handling ───


class TestSearchEngineErrors:
    def test_tavily_error_returns_empty(self):
        engine = TavilySearch(api_key="bad-key")
        with patch("mini_rag.search_engines.retry_with_backoff", side_effect=Exception("API error")):
            results = engine.search("test")
        assert results == []

    def test_brave_error_returns_empty(self):
        engine = BraveSearch(api_key="bad-key")
        with patch("mini_rag.search_engines.retry_with_backoff", side_effect=Exception("API error")):
            results = engine.search("test")
        assert results == []

    def test_serper_error_returns_empty(self):
        engine = SerperSearch(api_key="bad-key")
        with patch("mini_rag.search_engines.retry_with_backoff", side_effect=Exception("API error")):
            results = engine.search("test")
        assert results == []
