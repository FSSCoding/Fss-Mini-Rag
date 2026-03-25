"""Tests for scrape_registry — JSONL logging, domain stats, whitelist/blacklist."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mini_rag.scrape_registry import (
    SCRAPE_LOG_FILE,
    _normalize_domain,
    add_to_blacklist,
    add_to_whitelist,
    auto_blacklist_check,
    check_domain,
    get_domain_stats,
    load_domain_lists,
    log_scrape,
    remove_from_blacklist,
    remove_from_whitelist,
    save_domain_lists,
)


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Redirect all registry files to tmp_path so tests don't touch real data."""
    monkeypatch.setattr("mini_rag.scrape_registry.SCRAPE_LOG_DIR", tmp_path)
    monkeypatch.setattr("mini_rag.scrape_registry.SCRAPE_LOG_FILE", tmp_path / "scrape-log.jsonl")
    monkeypatch.setattr("mini_rag.scrape_registry.DOMAIN_LISTS_FILE", tmp_path / "domain-lists.json")
    return tmp_path


# ─── Domain normalization ───


class TestNormalizeDomain:
    def test_strips_www(self):
        assert _normalize_domain("www.example.com") == "example.com"

    def test_lowercase(self):
        assert _normalize_domain("Example.COM") == "example.com"

    def test_strips_whitespace(self):
        assert _normalize_domain("  example.com  ") == "example.com"

    def test_www_and_case(self):
        assert _normalize_domain("WWW.Example.Com") == "example.com"

    def test_no_www(self):
        assert _normalize_domain("api.example.com") == "api.example.com"


# ─── JSONL logging ───


class TestLogScrape:
    def test_creates_log_file(self, isolated_registry):
        log_file = isolated_registry / "scrape-log.jsonl"
        assert not log_file.exists()
        log_scrape(url="https://example.com/page", extractor_name="GenericExtractor", success=True)
        assert log_file.exists()

    def test_appends_valid_json(self, isolated_registry):
        log_file = isolated_registry / "scrape-log.jsonl"
        log_scrape(url="https://example.com/a", extractor_name="fetch", success=True, word_count=100)
        log_scrape(url="https://example.com/b", extractor_name="fetch", success=False, error="Timeout")

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        assert entry1["success"] is True
        assert entry1["word_count"] == 100
        assert entry2["success"] is False
        assert entry2["error"] == "Timeout"

    def test_domain_extraction(self, isolated_registry):
        log_file = isolated_registry / "scrape-log.jsonl"
        log_scrape(url="https://www.example.com/page", extractor_name="test", success=True)
        entry = json.loads(log_file.read_text().strip())
        assert entry["domain"] == "example.com"  # www stripped

    def test_field_truncation(self, isolated_registry):
        log_file = isolated_registry / "scrape-log.jsonl"
        log_scrape(
            url="https://example.com",
            extractor_name="test",
            success=True,
            title="x" * 200,
            error="e" * 300,
            session_query="q" * 200,
        )
        entry = json.loads(log_file.read_text().strip())
        assert len(entry["title"]) == 120
        assert len(entry["error"]) == 200
        assert len(entry["session_query"]) == 100

    def test_all_fields_present(self, isolated_registry):
        log_file = isolated_registry / "scrape-log.jsonl"
        log_scrape(
            url="https://example.com/page",
            extractor_name="GenericExtractor",
            success=True,
            word_count=500,
            title="Test Page",
            source_type="web",
            http_status=200,
            content_length=5000,
            has_main_content=True,
            session_query="test query",
        )
        entry = json.loads(log_file.read_text().strip())
        expected_keys = {
            "ts", "url", "domain", "extractor", "success", "word_count",
            "title", "source_type", "http_status", "error", "content_length",
            "has_main_content", "session_query",
        }
        assert set(entry.keys()) == expected_keys

    def test_unicode_content(self, isolated_registry):
        log_file = isolated_registry / "scrape-log.jsonl"
        log_scrape(url="https://example.com", extractor_name="test", success=True, title="Datenübertragung über Äthernetze")
        entry = json.loads(log_file.read_text().strip())
        assert "Datenübertragung" in entry["title"]


# ─── Domain stats ───


class TestDomainStats:
    def test_empty_log(self):
        stats = get_domain_stats()
        assert stats == {}

    def test_single_domain(self, isolated_registry):
        log_scrape(url="https://example.com/a", extractor_name="Generic", success=True, word_count=100)
        log_scrape(url="https://example.com/b", extractor_name="Generic", success=True, word_count=200)
        log_scrape(url="https://example.com/c", extractor_name="Generic", success=False, error="Timeout")

        stats = get_domain_stats()
        assert "example.com" in stats
        s = stats["example.com"]
        assert s["total"] == 3
        assert s["success"] == 2
        assert s["fail"] == 1
        assert s["avg_words"] == 150
        assert "Timeout" in s["errors"]
        assert "Generic" in s["extractors"]

    def test_multiple_domains(self, isolated_registry):
        log_scrape(url="https://a.com/1", extractor_name="A", success=True, word_count=50)
        log_scrape(url="https://b.com/1", extractor_name="B", success=False, error="403")

        stats = get_domain_stats()
        assert len(stats) == 2
        assert stats["a.com"]["success"] == 1
        assert stats["b.com"]["fail"] == 1

    def test_errors_capped_at_five(self, isolated_registry):
        for i in range(10):
            log_scrape(url="https://fail.com/p", extractor_name="t", success=False, error=f"Error {i}")
        stats = get_domain_stats()
        assert len(stats["fail.com"]["errors"]) == 5

    def test_zero_success_avg_words(self, isolated_registry):
        log_scrape(url="https://fail.com/p", extractor_name="t", success=False)
        stats = get_domain_stats()
        assert stats["fail.com"]["avg_words"] == 0

    def test_corrupt_line_skipped(self, isolated_registry):
        log_file = isolated_registry / "scrape-log.jsonl"
        log_scrape(url="https://good.com/a", extractor_name="t", success=True, word_count=10)
        # Inject corrupt line
        with open(log_file, "a") as f:
            f.write("NOT VALID JSON\n")
        log_scrape(url="https://good.com/b", extractor_name="t", success=True, word_count=20)

        stats = get_domain_stats()
        assert stats["good.com"]["total"] == 2  # Corrupt line skipped


# ─── Whitelist / Blacklist CRUD ───


class TestDomainLists:
    def test_empty_lists(self):
        lists = load_domain_lists()
        assert lists["whitelist"] == {}
        assert lists["blacklist"] == {}

    def test_add_to_whitelist(self):
        add_to_whitelist("example.com", note="trusted")
        lists = load_domain_lists()
        assert "example.com" in lists["whitelist"]
        assert lists["whitelist"]["example.com"]["note"] == "trusted"

    def test_add_to_blacklist(self):
        add_to_blacklist("bad.com", reason="spam", auto=True)
        lists = load_domain_lists()
        assert "bad.com" in lists["blacklist"]
        assert lists["blacklist"]["bad.com"]["reason"] == "spam"
        assert lists["blacklist"]["bad.com"]["auto"] is True

    def test_whitelist_removes_from_blacklist(self):
        add_to_blacklist("example.com", reason="test")
        add_to_whitelist("example.com", note="actually ok")
        lists = load_domain_lists()
        assert "example.com" in lists["whitelist"]
        assert "example.com" not in lists["blacklist"]

    def test_blacklist_removes_from_whitelist(self):
        add_to_whitelist("example.com", note="trusted")
        add_to_blacklist("example.com", reason="changed mind")
        lists = load_domain_lists()
        assert "example.com" in lists["blacklist"]
        assert "example.com" not in lists["whitelist"]

    def test_remove_from_whitelist(self):
        add_to_whitelist("example.com")
        remove_from_whitelist("example.com")
        lists = load_domain_lists()
        assert "example.com" not in lists["whitelist"]

    def test_remove_from_blacklist(self):
        add_to_blacklist("example.com")
        remove_from_blacklist("example.com")
        lists = load_domain_lists()
        assert "example.com" not in lists["blacklist"]

    def test_remove_nonexistent_is_safe(self):
        remove_from_whitelist("never-added.com")
        remove_from_blacklist("never-added.com")
        lists = load_domain_lists()
        assert lists["whitelist"] == {}
        assert lists["blacklist"] == {}

    def test_domain_normalization_in_lists(self):
        add_to_whitelist("WWW.Example.COM")
        lists = load_domain_lists()
        assert "example.com" in lists["whitelist"]
        assert "WWW.Example.COM" not in lists["whitelist"]


# ─── check_domain ───


class TestCheckDomain:
    def test_neutral_domain(self):
        status, reason = check_domain("https://neutral.com/page")
        assert status == "allowed"
        assert reason == ""

    def test_whitelisted_domain(self):
        add_to_whitelist("trusted.com")
        status, reason = check_domain("https://trusted.com/page")
        assert status == "allowed"

    def test_blacklisted_domain(self):
        add_to_blacklist("blocked.com", reason="robots.txt")
        status, reason = check_domain("https://blocked.com/page")
        assert status == "blocked"
        assert "robots.txt" in reason

    def test_www_stripping_in_check(self):
        add_to_blacklist("example.com", reason="test")
        status, _ = check_domain("https://www.example.com/page")
        assert status == "blocked"


# ─── Auto-blacklist ───


class TestAutoBlacklist:
    def test_auto_blacklist_robots(self, isolated_registry):
        # Simulate 2+ robots.txt blocks
        log_scrape(url="https://robots-site.com/a", extractor_name="fetch", success=False, error="Blocked by robots.txt")
        log_scrape(url="https://robots-site.com/b", extractor_name="fetch", success=False, error="Blocked by robots.txt")

        auto_blacklist_check("robots-site.com")

        lists = load_domain_lists()
        assert "robots-site.com" in lists["blacklist"]
        assert lists["blacklist"]["robots-site.com"]["auto"] is True
        assert "robots.txt" in lists["blacklist"]["robots-site.com"]["reason"]

    def test_auto_blacklist_consecutive_failures(self, isolated_registry):
        for i in range(5):
            log_scrape(url=f"https://dead-site.com/{i}", extractor_name="fetch", success=False, error="HTTP 503")

        auto_blacklist_check("dead-site.com")

        lists = load_domain_lists()
        assert "dead-site.com" in lists["blacklist"]
        assert "5 consecutive" in lists["blacklist"]["dead-site.com"]["reason"]

    def test_no_auto_blacklist_with_successes(self, isolated_registry):
        for i in range(4):
            log_scrape(url=f"https://flaky.com/{i}", extractor_name="fetch", success=False, error="timeout")
        log_scrape(url="https://flaky.com/ok", extractor_name="fetch", success=True, word_count=100)

        auto_blacklist_check("flaky.com")

        lists = load_domain_lists()
        assert "flaky.com" not in lists["blacklist"]

    def test_no_auto_blacklist_whitelisted(self, isolated_registry):
        add_to_whitelist("protected.com", note="always allow")
        for i in range(5):
            log_scrape(url=f"https://protected.com/{i}", extractor_name="fetch", success=False, error="Blocked by robots.txt")

        auto_blacklist_check("protected.com")

        lists = load_domain_lists()
        assert "protected.com" not in lists["blacklist"]
        assert "protected.com" in lists["whitelist"]

    def test_no_double_blacklist(self, isolated_registry):
        add_to_blacklist("already.com", reason="manual")
        log_scrape(url="https://already.com/a", extractor_name="fetch", success=False, error="Blocked by robots.txt")
        log_scrape(url="https://already.com/b", extractor_name="fetch", success=False, error="Blocked by robots.txt")

        auto_blacklist_check("already.com")

        lists = load_domain_lists()
        # Should keep original reason, not overwrite
        assert lists["blacklist"]["already.com"]["reason"] == "manual"


# ─── Atomic save safety ───


class TestAtomicSave:
    def test_save_domain_lists_atomic(self, isolated_registry):
        """Verify atomic write: no .tmp left behind."""
        add_to_whitelist("safe.com")
        tmp_file = (isolated_registry / "domain-lists.json").with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_save_survives_reload(self, isolated_registry):
        add_to_whitelist("a.com", note="note-a")
        add_to_blacklist("b.com", reason="reason-b")
        lists = load_domain_lists()
        assert lists["whitelist"]["a.com"]["note"] == "note-a"
        assert lists["blacklist"]["b.com"]["reason"] == "reason-b"

    def test_corrupt_domain_lists_returns_empty(self, isolated_registry):
        lists_file = isolated_registry / "domain-lists.json"
        lists_file.write_text("NOT JSON{{{")
        lists = load_domain_lists()
        assert lists["whitelist"] == {}
        assert lists["blacklist"] == {}
