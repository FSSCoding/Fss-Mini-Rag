"""Tests for web_scraper — MiniWebScraper, ResearchSession, domain checks."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mini_rag.config import WebScraperConfig
from mini_rag.extractors import ScrapedPage
from mini_rag.web_scraper import MiniWebScraper, ResearchSession, _slugify_session


# ─── Session slugify ───


class TestSlugifySession:
    def test_basic(self):
        assert _slugify_session("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify_session("What is AI?") == "what-is-ai"

    def test_max_length(self):
        result = _slugify_session("a" * 100, max_length=10)
        assert len(result) <= 10

    def test_empty_fallback(self):
        assert _slugify_session("!!!") == "session"


# ─── ResearchSession ───


class TestResearchSession:
    def test_create_session(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test query")
        assert session.session_dir.exists()
        assert (session.session_dir / "session.json").exists()
        assert (session.session_dir / "sources").exists()
        assert (session.session_dir / "notes").exists()
        assert (session.session_dir / "agent-notes").exists()

    def test_session_metadata(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="my query", engine="tavily")
        assert session.metadata["query"] == "my query"
        assert session.metadata["engine"] == "tavily"
        assert session.metadata["status"] == "active"
        assert session.metadata["pages_scraped"] == 0

    def test_session_dir_naming(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test query")
        dir_name = session.session_dir.name
        # Should start with date prefix
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}-", dir_name)

    def test_collision_handling(self, tmp_path):
        s1 = ResearchSession.create(tmp_path, query="same")
        s2 = ResearchSession.create(tmp_path, query="same")
        assert s1.session_dir != s2.session_dir
        assert s1.session_dir.exists()
        assert s2.session_dir.exists()

    def test_add_page(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test")
        page = ScrapedPage(
            url="https://example.com",
            title="Test Page",
            content="Content here",
            scraped_at="2024-01-01T00:00:00",
            word_count=2,
        )
        filepath = session.add_page(page)
        assert filepath.exists()
        assert "https://example.com" in session.metadata["urls_visited"]
        assert session.metadata["pages_scraped"] == 1

    def test_has_visited(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test")
        page = ScrapedPage(
            url="https://example.com/visited",
            title="Page",
            content="C",
            scraped_at="2024-01-01T00:00:00",
            word_count=1,
        )
        assert not session.has_visited("https://example.com/visited")
        session.add_page(page)
        assert session.has_visited("https://example.com/visited")

    def test_load_session(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="load test")
        session.metadata["pages_scraped"] = 5
        session.save_metadata()

        loaded = ResearchSession.load(session.session_dir)
        assert loaded is not None
        assert loaded.metadata["query"] == "load test"
        assert loaded.metadata["pages_scraped"] == 5

    def test_load_nonexistent_returns_none(self, tmp_path):
        assert ResearchSession.load(tmp_path / "nonexistent") is None

    def test_list_sessions(self, tmp_path):
        ResearchSession.create(tmp_path, query="first")
        ResearchSession.create(tmp_path, query="second")
        sessions = ResearchSession.list_sessions(tmp_path, output_dir="mini-research")
        assert len(sessions) == 2

    def test_list_sessions_empty(self, tmp_path):
        sessions = ResearchSession.list_sessions(tmp_path, output_dir="mini-research")
        assert sessions == []

    def test_complete_session(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test")
        session.complete()
        assert session.metadata["status"] == "complete"
        assert "completed" in session.metadata

    def test_add_agent_note(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test")
        filepath = session.add_agent_note("analysis.md", "# Analysis\nContent")
        assert filepath.exists()
        assert filepath.read_text() == "# Analysis\nContent"

    def test_get_all_source_files(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test")
        page = ScrapedPage(
            url="https://example.com",
            title="Source File",
            content="Content body text",
            scraped_at="2024-01-01T00:00:00",
            word_count=3,
        )
        session.add_page(page)
        sources = session.get_all_source_files()
        assert len(sources) == 1
        assert sources[0].suffix == ".md"

    def test_set_phase(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test")
        session.set_phase("scraping")
        assert session.metadata["phase"] == "scraping"

    def test_three_bucket_directories(self, tmp_path):
        session = ResearchSession.create(tmp_path, query="test")
        assert session.sources_dir.exists()
        assert session.notes_dir.exists()
        assert session.agent_notes_dir.exists()


# ─── MiniWebScraper ───


@pytest.fixture
def scraper_config():
    return WebScraperConfig(
        respect_robots=True,
        timeout=5,
        delay_between_requests=0.01,
        min_content_length=50,
    )


@pytest.fixture(autouse=True)
def isolated_scraper_registry(tmp_path, monkeypatch):
    """Prevent tests from writing to real scrape registry."""
    monkeypatch.setattr("mini_rag.scrape_registry.SCRAPE_LOG_DIR", tmp_path)
    monkeypatch.setattr("mini_rag.scrape_registry.SCRAPE_LOG_FILE", tmp_path / "scrape-log.jsonl")
    monkeypatch.setattr("mini_rag.scrape_registry.DOMAIN_LISTS_FILE", tmp_path / "domain-lists.json")
    return tmp_path


class TestMiniWebScraper:
    def test_blacklisted_domain_skipped(self, scraper_config):
        from mini_rag.scrape_registry import add_to_blacklist
        add_to_blacklist("blocked.com", reason="test block")

        scraper = MiniWebScraper(scraper_config)
        result = scraper.fetch("https://blocked.com/page")
        assert result is None

    def test_robots_blocked_logged(self, scraper_config):
        scraper = MiniWebScraper(scraper_config)

        with patch.object(scraper, "_check_robots", return_value=False):
            result = scraper.fetch("https://robots-blocked.com/page")

        assert result is None

    def test_successful_fetch(self, scraper_config):
        scraper = MiniWebScraper(scraper_config)

        mock_response = MagicMock()
        mock_response.content = b"""<html><head><title>Good Page</title></head>
        <body><article>
        <p>Substantial content here with enough words to pass the minimum threshold.
        Multiple sentences ensure adequate word count for the extraction process.</p>
        </article></body></html>"""
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper, "_check_robots", return_value=True):
            with patch("mini_rag.rate_limiter.retry_with_backoff", return_value=mock_response):
                result = scraper.fetch("https://example.com/good")

        assert result is not None
        assert result.title == "Good Page"

    def test_timeout_returns_none(self, scraper_config):
        import requests
        scraper = MiniWebScraper(scraper_config)

        with patch.object(scraper, "_check_robots", return_value=True):
            with patch("mini_rag.rate_limiter.retry_with_backoff", side_effect=requests.exceptions.Timeout):
                result = scraper.fetch("https://slow.com/page")

        assert result is None

    def test_http_error_returns_none(self, scraper_config):
        import requests
        scraper = MiniWebScraper(scraper_config)
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch.object(scraper, "_check_robots", return_value=True):
            with patch(
                "mini_rag.rate_limiter.retry_with_backoff",
                side_effect=requests.exceptions.HTTPError(response=mock_resp),
            ):
                result = scraper.fetch("https://forbidden.com/page")

        assert result is None

    def test_thin_page_filtered(self, scraper_config):
        scraper = MiniWebScraper(scraper_config)

        mock_response = MagicMock()
        mock_response.content = b"<html><body><p>Hi</p></body></html>"
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        # Patch extract_content to return a thin page
        thin_page = ScrapedPage(
            url="https://thin.com", title="Thin", content="Hi",
            scraped_at="2024-01-01T00:00:00", word_count=1,
        )

        with patch.object(scraper, "_check_robots", return_value=True):
            with patch("mini_rag.rate_limiter.retry_with_backoff", return_value=mock_response):
                with patch("mini_rag.web_scraper.extract_content", return_value=thin_page):
                    result = scraper.fetch("https://thin.com/page")

        assert result is None


class TestScrapeUrls:
    def test_scrape_multiple(self, tmp_path, scraper_config):
        scraper = MiniWebScraper(scraper_config)
        session = ResearchSession.create(tmp_path, query="multi test")

        pages = []
        for i in range(3):
            pages.append(ScrapedPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content for page {i}",
                scraped_at="2024-01-01T00:00:00",
                word_count=20,
            ))

        call_count = 0

        def mock_fetch(url):
            nonlocal call_count
            page = pages[call_count] if call_count < len(pages) else None
            call_count += 1
            return page

        with patch.object(scraper, "fetch", side_effect=mock_fetch):
            result = scraper.scrape_urls(
                [f"https://example.com/page{i}" for i in range(3)],
                session, max_pages=10,
            )

        assert len(result) == 3
        assert session.metadata["pages_scraped"] == 3

    def test_respects_max_pages(self, tmp_path, scraper_config):
        scraper = MiniWebScraper(scraper_config)
        session = ResearchSession.create(tmp_path, query="limit test")

        def mock_fetch(url):
            return ScrapedPage(
                url=url, title="Page", content="C",
                scraped_at="2024-01-01T00:00:00", word_count=1,
            )

        with patch.object(scraper, "fetch", side_effect=mock_fetch):
            result = scraper.scrape_urls(
                [f"https://example.com/{i}" for i in range(10)],
                session, max_pages=3,
            )

        assert len(result) == 3

    def test_skips_visited_urls(self, tmp_path, scraper_config):
        scraper = MiniWebScraper(scraper_config)
        session = ResearchSession.create(tmp_path, query="dedup test")

        # Pre-visit a URL
        page = ScrapedPage(
            url="https://example.com/already",
            title="Already Visited",
            content="C",
            scraped_at="2024-01-01T00:00:00",
            word_count=1,
        )
        session.add_page(page)

        fetch_called_with = []

        def mock_fetch(url):
            fetch_called_with.append(url)
            return ScrapedPage(
                url=url, title="New", content="C",
                scraped_at="2024-01-01T00:00:00", word_count=1,
            )

        with patch.object(scraper, "fetch", side_effect=mock_fetch):
            scraper.scrape_urls(
                ["https://example.com/already", "https://example.com/new"],
                session, max_pages=10,
            )

        # Should only fetch the new URL
        assert "https://example.com/already" not in fetch_called_with
        assert "https://example.com/new" in fetch_called_with


# ─── Config application ───


class TestWebScraperConfig:
    def test_default_values(self):
        config = WebScraperConfig()
        assert config.respect_robots is True
        assert "FSS-Mini-RAG" in config.user_agent
        assert config.max_pages == 20
        assert config.timeout == 15

    def test_custom_values(self):
        config = WebScraperConfig(
            user_agent="Custom/1.0 (test@example.com)",
            respect_robots=False,
            max_pages=50,
        )
        assert config.user_agent == "Custom/1.0 (test@example.com)"
        assert config.respect_robots is False
        assert config.max_pages == 50
