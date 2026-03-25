"""
Scrape registry — JSONL log of every scrape attempt + domain whitelist/blacklist.

Tracks domain, URL, extractor used, success/failure, word count,
and content signals. Lives at ~/.config/fss-mini-rag/scrape-log.jsonl.
Domain lists at ~/.config/fss-mini-rag/domain-lists.json.
Designed to inform domain-specific adapter development.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SCRAPE_LOG_DIR = Path.home() / ".config" / "fss-mini-rag"
SCRAPE_LOG_FILE = SCRAPE_LOG_DIR / "scrape-log.jsonl"
DOMAIN_LISTS_FILE = SCRAPE_LOG_DIR / "domain-lists.json"

# Auto-blacklist thresholds
_AUTO_BLACKLIST_ROBOTS_THRESHOLD = 2  # blocked by robots.txt N times
_AUTO_BLACKLIST_FAIL_THRESHOLD = 5    # N consecutive failures


def log_scrape(
    url: str,
    extractor_name: str,
    success: bool,
    word_count: int = 0,
    title: str = "",
    source_type: str = "",
    http_status: Optional[int] = None,
    error: str = "",
    content_length: int = 0,
    has_main_content: bool = False,
    session_query: str = "",
    doc_metadata: Optional[Dict] = None,
) -> None:
    """Append a scrape result entry to the JSONL log."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    # Strip www. prefix for cleaner grouping
    if domain.startswith("www."):
        domain = domain[4:]

    entry = {
        "ts": datetime.now().isoformat(),
        "url": url,
        "domain": domain,
        "extractor": extractor_name,
        "success": success,
        "word_count": word_count,
        "title": title[:120],
        "source_type": source_type,
        "http_status": http_status,
        "error": error[:200] if error else "",
        "content_length": content_length,
        "has_main_content": has_main_content,
        "session_query": session_query[:100] if session_query else "",
    }
    if doc_metadata:
        entry["doc_metadata"] = {k: str(v)[:100] for k, v in doc_metadata.items() if v}

    try:
        SCRAPE_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SCRAPE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug(f"Failed to write scrape log: {e}")


def get_domain_stats() -> dict:
    """Read the scrape log and return per-domain statistics.

    Returns dict keyed by domain with counts for total, success, fail,
    avg word count, and which extractors were used.
    """
    if not SCRAPE_LOG_FILE.exists():
        return {}

    stats: dict = {}
    try:
        with open(SCRAPE_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                domain = entry.get("domain", "unknown")
                if domain not in stats:
                    stats[domain] = {
                        "total": 0,
                        "success": 0,
                        "fail": 0,
                        "total_words": 0,
                        "extractors": set(),
                        "errors": [],
                    }

                s = stats[domain]
                s["total"] += 1
                if entry.get("success"):
                    s["success"] += 1
                    s["total_words"] += entry.get("word_count", 0)
                else:
                    s["fail"] += 1
                    err = entry.get("error", "")
                    if err and err not in s["errors"]:
                        s["errors"].append(err)

                s["extractors"].add(entry.get("extractor", "unknown"))

        # Convert sets to lists for JSON serialization
        for domain in stats:
            stats[domain]["extractors"] = sorted(stats[domain]["extractors"])
            if stats[domain]["success"] > 0:
                stats[domain]["avg_words"] = (
                    stats[domain]["total_words"] // stats[domain]["success"]
                )
            else:
                stats[domain]["avg_words"] = 0
            # Keep only last 5 unique errors
            stats[domain]["errors"] = stats[domain]["errors"][-5:]

    except Exception as e:
        logger.error(f"Failed to read scrape log: {e}")

    return stats


# ─── Domain whitelist / blacklist ───


def _normalize_domain(domain: str) -> str:
    """Normalize a domain for consistent storage."""
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def load_domain_lists() -> Dict[str, dict]:
    """Load domain whitelist/blacklist from disk.

    Returns:
        {
            "whitelist": {"example.com": {"added": "...", "note": "..."}},
            "blacklist": {"bad.com": {"added": "...", "reason": "...", "auto": True}},
        }
    """
    default: Dict[str, dict] = {"whitelist": {}, "blacklist": {}}
    if not DOMAIN_LISTS_FILE.exists():
        return default
    try:
        with open(DOMAIN_LISTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "whitelist": data.get("whitelist", {}),
            "blacklist": data.get("blacklist", {}),
        }
    except Exception as e:
        logger.error(f"Failed to load domain lists: {e}")
        return default


def save_domain_lists(lists: Dict[str, dict]) -> None:
    """Save domain whitelist/blacklist to disk using atomic write."""
    import os

    SCRAPE_LOG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = DOMAIN_LISTS_FILE.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(lists, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(DOMAIN_LISTS_FILE)
    except Exception as e:
        logger.error(f"Failed to save domain lists: {e}")
        tmp_path.unlink(missing_ok=True)


def add_to_whitelist(domain: str, note: str = "") -> None:
    """Add a domain to the whitelist (and remove from blacklist if present)."""
    domain = _normalize_domain(domain)
    lists = load_domain_lists()
    lists["whitelist"][domain] = {
        "added": datetime.now().isoformat(),
        "note": note,
    }
    lists["blacklist"].pop(domain, None)
    save_domain_lists(lists)


def add_to_blacklist(domain: str, reason: str = "", auto: bool = False) -> None:
    """Add a domain to the blacklist (and remove from whitelist if present)."""
    domain = _normalize_domain(domain)
    lists = load_domain_lists()
    lists["blacklist"][domain] = {
        "added": datetime.now().isoformat(),
        "reason": reason,
        "auto": auto,
    }
    lists["whitelist"].pop(domain, None)
    save_domain_lists(lists)


def remove_from_whitelist(domain: str) -> None:
    """Remove a domain from the whitelist."""
    domain = _normalize_domain(domain)
    lists = load_domain_lists()
    lists["whitelist"].pop(domain, None)
    save_domain_lists(lists)


def remove_from_blacklist(domain: str) -> None:
    """Remove a domain from the blacklist."""
    domain = _normalize_domain(domain)
    lists = load_domain_lists()
    lists["blacklist"].pop(domain, None)
    save_domain_lists(lists)


def check_domain(url: str) -> Tuple[str, str]:
    """Check if a URL's domain is whitelisted, blacklisted, or neutral.

    Returns:
        ("allowed", "") — whitelisted or no listing
        ("blocked", reason) — blacklisted with reason
    """
    parsed = urlparse(url)
    domain = _normalize_domain(parsed.netloc)
    lists = load_domain_lists()

    if domain in lists["blacklist"]:
        entry = lists["blacklist"][domain]
        return "blocked", entry.get("reason", "Blacklisted")

    # Whitelisted or neutral — both allowed
    return "allowed", ""


def auto_blacklist_check(domain: str) -> None:
    """Check if a domain should be auto-blacklisted based on scrape history.

    Called after each failed scrape. Auto-blacklists if:
    - Blocked by robots.txt >= threshold times
    - Consecutive failures >= threshold
    """
    domain = _normalize_domain(domain)
    lists = load_domain_lists()

    # Don't auto-blacklist whitelisted domains
    if domain in lists["whitelist"]:
        return
    # Already blacklisted
    if domain in lists["blacklist"]:
        return

    stats = get_domain_stats()
    ds = stats.get(domain)
    if not ds:
        return

    errors = ds.get("errors", [])
    has_robots_error = any("robots.txt" in e.lower() for e in errors)

    # Check robots.txt blocks — use fail count when robots.txt is the error
    # (errors list is deduplicated, so count failures instead)
    robots_blocks = ds["fail"] if has_robots_error and ds["success"] == 0 else 0
    if robots_blocks >= _AUTO_BLACKLIST_ROBOTS_THRESHOLD:
        add_to_blacklist(
            domain,
            reason=f"Auto-blocked: robots.txt denied access ({robots_blocks} times)",
            auto=True,
        )
        logger.info(f"Auto-blacklisted {domain}: robots.txt blocks")
        return

    # Check overall failure rate (only if enough attempts)
    if ds["total"] >= _AUTO_BLACKLIST_FAIL_THRESHOLD and ds["success"] == 0:
        add_to_blacklist(
            domain,
            reason=f"Auto-blocked: {ds['fail']} consecutive failures, 0 successes",
            auto=True,
        )
        logger.info(f"Auto-blacklisted {domain}: all {ds['fail']} attempts failed")
