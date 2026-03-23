"""
Web scraper and research session manager for Mini RAG.

Handles URL fetching with rate limiting, robots.txt compliance,
session directory management, and orchestration of the
search → scrape → save pipeline.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from .config import WebScraperConfig
from .extractors import ScrapedPage, extract_content, save_scraped_page

logger = logging.getLogger(__name__)


def _slugify_session(text: str, max_length: int = 40) -> str:
    """Create a filesystem-safe session name from query text."""
    import re

    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_length] or "session"


class ResearchSession:
    """Manages a single research session's state and output.

    Each session gets a directory under {project}/mini-research/
    with three-bucket structure:
      sources/      — downloaded web pages, PDFs (never modified except dedup)
      notes/        — user's own files
      agent-notes/  — AI-generated analysis, gap reports, summaries

    Backward-compatible: flat sessions (no subdirs) still work.
    """

    # Bucket subdirectories
    SOURCES_DIR = "sources"
    NOTES_DIR = "notes"
    AGENT_NOTES_DIR = "agent-notes"

    def __init__(self, session_dir: Path, query: str, engine: str = "duckduckgo"):
        self.session_dir = session_dir
        self.query = query
        self.metadata: Dict = {
            "query": query,
            "created": datetime.now().isoformat(),
            "status": "active",
            "engine": engine,
            "urls_visited": [],
            "pages_scraped": 0,
            "pages_pruned": 0,
            "rounds": 0,
            "deep_research": False,
            "phase": "idle",
            "time_elapsed_minutes": 0,
        }

        # Load existing metadata if resuming
        meta_path = self.session_dir / "session.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    self.metadata = json.load(f)
                self.metadata["status"] = "active"
            except Exception:
                pass  # Start fresh if corrupt

    @classmethod
    def create(
        cls, project_path: Path, query: str, output_dir: str = "mini-research",
        engine: str = "duckduckgo", name: Optional[str] = None,
    ) -> "ResearchSession":
        """Create a new research session with a dated directory."""
        base_dir = project_path / output_dir
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        session_name = name or _slugify_session(query)
        dir_name = f"{date_prefix}-{session_name}"

        session_dir = base_dir / dir_name
        # Handle collision
        counter = 1
        while session_dir.exists():
            session_dir = base_dir / f"{dir_name}-{counter}"
            counter += 1

        session_dir.mkdir(parents=True, exist_ok=True)
        # Create bucket subdirectories
        (session_dir / cls.SOURCES_DIR).mkdir(exist_ok=True)
        (session_dir / cls.NOTES_DIR).mkdir(exist_ok=True)
        (session_dir / cls.AGENT_NOTES_DIR).mkdir(exist_ok=True)
        session = cls(session_dir, query, engine)
        session.save_metadata()
        return session

    @classmethod
    def load(cls, session_dir: Path) -> Optional["ResearchSession"]:
        """Load an existing session from its directory."""
        meta_path = session_dir / "session.json"
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, "r") as f:
                metadata = json.load(f)
            session = cls(session_dir, metadata.get("query", ""), metadata.get("engine", "duckduckgo"))
            session.metadata = metadata
            return session
        except Exception as e:
            logger.error(f"Failed to load session from {session_dir}: {e}")
            return None

    @classmethod
    def list_sessions(cls, project_path: Path, output_dir: str = "mini-research") -> List["ResearchSession"]:
        """List all research sessions in the project."""
        base_dir = project_path / output_dir
        if not base_dir.exists():
            return []

        sessions = []
        for d in sorted(base_dir.iterdir(), reverse=True):
            if d.is_dir() and (d / "session.json").exists():
                session = cls.load(d)
                if session:
                    sessions.append(session)
        return sessions

    def save_metadata(self):
        """Save session metadata to session.json."""
        meta_path = self.session_dir / "session.json"
        with open(meta_path, "w") as f:
            json.dump(self.metadata, f, indent=2)

    @property
    def sources_dir(self) -> Path:
        """Directory for downloaded web content."""
        d = self.session_dir / self.SOURCES_DIR
        d.mkdir(exist_ok=True)
        return d

    @property
    def notes_dir(self) -> Path:
        """Directory for user's own files."""
        d = self.session_dir / self.NOTES_DIR
        d.mkdir(exist_ok=True)
        return d

    @property
    def agent_notes_dir(self) -> Path:
        """Directory for AI-generated analysis."""
        d = self.session_dir / self.AGENT_NOTES_DIR
        d.mkdir(exist_ok=True)
        return d

    def add_page(self, page: ScrapedPage) -> Path:
        """Save a scraped page to sources/ and update metadata."""
        filepath = save_scraped_page(page, self.sources_dir)
        self.metadata["urls_visited"].append(page.url)
        self.metadata["pages_scraped"] += 1
        self.save_metadata()
        return filepath

    def add_agent_note(self, filename: str, content: str) -> Path:
        """Write an agent-generated note to agent-notes/."""
        filepath = self.agent_notes_dir / filename
        filepath.write_text(content, encoding="utf-8")
        self.save_metadata()
        return filepath

    def get_all_source_files(self) -> List[Path]:
        """Get all source files (scraped content)."""
        sources = self.sources_dir
        if sources.exists():
            return sorted(f for f in sources.iterdir() if f.is_file() and f.suffix == ".md")
        # Backward compat: flat sessions have .md files directly in session_dir
        return sorted(
            f for f in self.session_dir.iterdir()
            if f.is_file() and f.suffix == ".md" and f.name != "session.json"
        )

    def set_phase(self, phase: str):
        """Update the current research phase in metadata."""
        self.metadata["phase"] = phase
        self.save_metadata()

    def has_visited(self, url: str) -> bool:
        """Check if a URL has already been visited in this session."""
        return url in self.metadata.get("urls_visited", [])

    def complete(self):
        """Mark session as complete."""
        self.metadata["status"] = "complete"
        self.metadata["completed"] = datetime.now().isoformat()
        self.save_metadata()


class MiniWebScraper:
    """Tier-1 web fetcher using requests.

    Handles rate limiting, robots.txt compliance, timeouts, and
    content extraction via the extractors module.
    """

    # Common system CA bundle paths (tried in order for SSL fallback)
    _SYSTEM_CA_PATHS = [
        "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu
        "/etc/pki/tls/certs/ca-bundle.crt",    # RHEL/CentOS
        "/etc/ssl/ca-bundle.pem",               # OpenSUSE
        "/etc/ssl/cert.pem",                     # macOS/BSD
    ]

    def __init__(self, config: WebScraperConfig):
        self.config = config
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": config.user_agent})
        self._robots_cache: Dict[str, RobotFileParser] = {}
        self._last_request_time: float = 0
        self._ca_bundle: Optional[str] = self._find_ca_bundle()

        # Rate limiting and retry
        from .rate_limiter import get_limiter, get_retry_config
        self._limiter = get_limiter(
            "scraper", calls_per_minute=60.0 / max(config.delay_between_requests, 0.1),
        )
        self._retry_config = get_retry_config("scraper")

    def _find_ca_bundle(self) -> Optional[str]:
        """Find a working CA bundle, trying env var then system paths."""
        import os

        # Check environment variable first
        env_bundle = os.environ.get("REQUESTS_CA_BUNDLE")
        if env_bundle and Path(env_bundle).exists():
            return env_bundle

        # Try a quick HTTPS request to see if default SSL works
        try:
            requests.head("https://example.com", timeout=5)
            return None  # Default works fine
        except requests.exceptions.SSLError:
            pass
        except Exception:
            return None  # Non-SSL error, default is fine

        # Default SSL broken — find system CA bundle
        for ca_path in self._SYSTEM_CA_PATHS:
            if Path(ca_path).exists():
                logger.info(f"Using system CA bundle: {ca_path}")
                return ca_path

        logger.warning("No working CA bundle found — HTTPS requests may fail")
        return None

    def _rate_limit(self):
        """Enforce delay between requests."""
        elapsed = time.time() - self._last_request_time
        remaining = self.config.delay_between_requests - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_time = time.time()

    def _check_robots(self, url: str) -> bool:
        """Check if we're allowed to fetch this URL per robots.txt."""
        if not self.config.respect_robots:
            return True

        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        if robots_url not in self._robots_cache:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception:
                # If we can't read robots.txt, allow access
                return True
            self._robots_cache[robots_url] = rp

        return self._robots_cache[robots_url].can_fetch(
            self.config.user_agent, url
        )

    def fetch(self, url: str) -> Optional[ScrapedPage]:
        """Fetch a single URL, extract content, return ScrapedPage.

        Uses rate limiting and retry with backoff for transient errors.
        Returns None if the page can't be fetched, is blocked by robots.txt,
        or has insufficient content.
        """
        from .rate_limiter import retry_with_backoff

        # Robots check
        if not self._check_robots(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return None

        def _do_fetch():
            verify = self._ca_bundle if self._ca_bundle else True
            resp = self._session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=True,
                verify=verify,
            )
            resp.raise_for_status()
            return resp

        try:
            resp = retry_with_backoff(
                _do_fetch,
                config=self._retry_config,
                rate_limiter=self._limiter,
            )

            content_type = resp.headers.get("Content-Type", "text/html")
            page = extract_content(url, resp.content, content_type)

            if page and page.word_count < (self.config.min_content_length // 5):
                logger.debug(f"Skipping thin page ({page.word_count} words): {url}")
                return None

            return page

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url}")
            return None
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if hasattr(e, "response") and e.response else "?"
            logger.warning(f"HTTP error {status} for {url}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def scrape_urls(
        self,
        urls: List[str],
        session: ResearchSession,
        max_pages: Optional[int] = None,
        depth: int = 0,
    ) -> List[ScrapedPage]:
        """Scrape multiple URLs, saving results to a research session.

        Args:
            urls: URLs to scrape
            session: Research session to save results to
            max_pages: Override max pages (default: from config)
            depth: Follow links N levels deep (0 = no following)

        Returns:
            List of successfully scraped pages
        """
        limit = max_pages or self.config.max_pages
        scraped = []
        to_visit = list(urls)
        current_depth = 0

        while to_visit and len(scraped) < limit:
            next_level = []

            for url in to_visit:
                if len(scraped) >= limit:
                    break
                if session.has_visited(url):
                    continue

                page = self.fetch(url)
                if page:
                    session.add_page(page)
                    scraped.append(page)
                    logger.info(
                        f"[{len(scraped)}/{limit}] Scraped: {page.title[:60]}"
                    )

                    # Collect links for next depth level
                    if current_depth < depth:
                        next_level.extend(page.links)

            current_depth += 1
            if current_depth > depth:
                break
            to_visit = next_level

        return scraped
