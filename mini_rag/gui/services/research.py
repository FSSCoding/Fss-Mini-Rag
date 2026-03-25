"""Background research service for the GUI.

Wraps web search, scraping, and deep research backends
with event emission for UI updates.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from ..events import EventBus

logger = logging.getLogger(__name__)


def _log_scrape(
    project_path: str,
    url: str,
    success: bool,
    title: str = "",
    word_count: int = 0,
    error: str = "",
):
    """Append a scrape result to the JSONL log file.

    Log lives at <working_dir>/scrape-log.jsonl. Each line is a JSON object
    with: timestamp, url, domain, success, title, word_count, error.
    This enables future analysis of scrape patterns and adapter development.
    """
    try:
        log_path = Path(project_path) / "scrape-log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "url": url,
            "domain": urlparse(url).netloc,
            "success": success,
            "title": title[:200] if title else "",
            "word_count": word_count,
            "error": error[:500] if error else "",
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.debug(f"Failed to write scrape log: {e}")


class ResearchService:
    """Manages web search, scraping, and deep research operations."""

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._cancel = threading.Event()
        self._thread = None
        self.llm_url: str = "http://localhost:1234/v1"
        self.llm_model: str = "auto"
        self.scraper_user_agent: str = "FSS-Mini-RAG-Research/2.2"
        self.scraper_respect_robots: bool = True

    def _apply_scraper_settings(self, ws_config) -> None:
        """Apply GUI scraper settings to a WebScraperConfig instance."""
        ws_config.user_agent = self.scraper_user_agent
        ws_config.respect_robots = self.scraper_respect_robots

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def cancel(self):
        self._cancel.set()

    def web_search(self, query: str, engine_name: str = "duckduckgo",
                   max_results: int = 10):
        """Run web search in background thread."""
        self._cancel.clear()

        def _run():
            try:
                from mini_rag.search_engines import create_search_engine

                engine = create_search_engine(engine_name)
                results = engine.search(query, max_results=max_results)

                self.bus.emit("research:search_completed", {
                    "results": [
                        {"title": r.title, "url": r.url, "snippet": r.snippet}
                        for r in results
                    ],
                    "query": query,
                })
            except Exception as e:
                logger.error(f"Web search failed: {e}")
                self.bus.emit("research:error", {"error": f"Search failed: {e}"})

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def scrape_urls(self, urls: List[str], project_path: str, query: str):
        """Scrape multiple URLs into a research session."""
        self._cancel.clear()

        def _run():
            try:
                from mini_rag.config import WebScraperConfig
                from mini_rag.web_scraper import MiniWebScraper, ResearchSession

                session = ResearchSession.create(
                    Path(project_path), query=query,
                )
                ws_config = WebScraperConfig()
                self._apply_scraper_settings(ws_config)
                scraper = MiniWebScraper(ws_config)

                total = len(urls)
                failed_urls = []
                for i, url in enumerate(urls):
                    if self._cancel.is_set():
                        self.bus.emit("research:cancelled", {})
                        return

                    self.bus.emit("research:scrape_progress", {
                        "done": i, "total": total, "current_url": url,
                    })

                    error_msg = ""
                    try:
                        page = scraper.fetch(url)
                    except Exception as fetch_err:
                        page = None
                        error_msg = str(fetch_err)
                        _log_scrape(project_path, url, False, error=error_msg)

                    if page:
                        session.add_page(page)
                        _log_scrape(project_path, url, True,
                                    title=page.title, word_count=page.word_count)
                        self.bus.emit("research:page_scraped", {
                            "title": page.title,
                            "url": page.url,
                            "word_count": page.word_count,
                            "content": page.content,
                        })
                    else:
                        if not error_msg:
                            error_msg = "extraction failed or content too thin"
                        _log_scrape(project_path, url, False, error=error_msg)
                        failed_urls.append({"url": url, "error": error_msg})
                        self.bus.emit("research:page_failed", {
                            "url": url, "error": error_msg,
                        })

                self.bus.emit("research:scrape_completed", {
                    "session_dir": str(session.session_dir),
                    "pages_scraped": session.metadata.get("pages_scraped", 0),
                    "failed_urls": failed_urls,
                })

            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                self.bus.emit("research:error", {"error": f"Scrape failed: {e}"})

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def scrape_single(self, url: str, project_path: str, query: str = ""):
        """Scrape a single URL."""
        self.scrape_urls([url], project_path, query or url[:50])

    def deep_research(self, query: str, engine_name: str, project_path: str,
                      max_time_min: int = 60, max_rounds: int = 5,
                      disable_stall_detection: bool = False):
        """Run deep research engine in background."""
        self._cancel.clear()

        def _run():
            try:
                from mini_rag.config import (
                    ConfigManager, DeepResearchConfig, WebScraperConfig,
                )
                from mini_rag.deep_research import DeepResearchEngine
                from mini_rag.llm_synthesizer import LLMSynthesizer
                from mini_rag.search_engines import create_search_engine
                from mini_rag.web_scraper import MiniWebScraper, ResearchSession
                from mini_rag.gui.env_manager import get_key

                proj = Path(project_path)

                # Load project config if available
                try:
                    config = ConfigManager(proj).load_config()
                    ws_config = config.web_scraper
                    dr_config = config.deep_research
                    rag_config = config
                except Exception:
                    from mini_rag.config import RAGConfig
                    ws_config = WebScraperConfig()
                    dr_config = DeepResearchConfig()
                    rag_config = RAGConfig()

                # Override with GUI settings
                self._apply_scraper_settings(ws_config)
                dr_config.max_time_minutes = max_time_min
                dr_config.max_rounds = max_rounds

                # Initialize components
                llm = LLMSynthesizer(
                    base_url=self.llm_url,
                    model=self.llm_model if self.llm_model != "auto" else None,
                    provider="openai",
                    api_key=get_key("LLM_API_KEY") or get_key("OPENAI_API_KEY"),
                )

                session = ResearchSession.create(
                    proj, query=query, engine=engine_name,
                )
                search_eng = create_search_engine(engine_name)
                scraper = MiniWebScraper(ws_config)

                self.bus.emit("research:deep_started", {
                    "query": query,
                    "session_dir": str(session.session_dir),
                })

                # Direct progress callback — replaces polling monitor
                def _on_progress(data):
                    self.bus.emit("research:deep_progress", data)

                engine = DeepResearchEngine(
                    session=session,
                    config=dr_config,
                    rag_config=rag_config,
                    llm_call=llm._call_llm,
                    scraper=scraper,
                    search_engine=search_eng,
                    progress_callback=_on_progress,
                )

                # Build ranked fallback search engines: tavily > brave > duckduckgo
                ranked_fallbacks = ["tavily", "serper", "brave", "duckduckgo"]
                fallbacks = []
                for fb_name in ranked_fallbacks:
                    if fb_name == engine_name:
                        continue
                    try:
                        fb = create_search_engine(fb_name)
                        if type(fb).__name__ != type(search_eng).__name__:
                            fallbacks.append(fb)
                    except Exception:
                        pass
                engine._fallback_engines = fallbacks
                if fallbacks:
                    logger.info(f"Deep research fallback engines: {[type(f).__name__ for f in fallbacks]}")
                report = engine.run(
                    max_time_minutes=max_time_min,
                    max_rounds=max_rounds,
                    disable_stall_detection=disable_stall_detection,
                )

                # Read the report file
                report_path = session.agent_notes_dir / "research-report.md"
                report_md = ""
                if report_path.exists():
                    report_md = report_path.read_text(encoding="utf-8")

                self.bus.emit("research:deep_completed", {
                    "session_dir": str(session.session_dir),
                    "report_md": report_md,
                    "rounds": report.rounds_completed,
                    "time_minutes": report.total_time_minutes,
                    "pages_scraped": report.pages_scraped,
                    "confidence": report.confidence,
                })

            except Exception as e:
                logger.error(f"Deep research failed: {e}")
                self.bus.emit("research:error", {"error": f"Deep research failed: {e}"})

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def load_sessions(self, project_path: str) -> list:
        """Load existing research sessions (synchronous)."""
        try:
            from mini_rag.web_scraper import ResearchSession

            sessions = ResearchSession.list_sessions(Path(project_path))
            return [
                {
                    "name": s.session_dir.name,
                    "dir": str(s.session_dir),
                    "query": s.metadata.get("query", ""),
                    "pages": s.metadata.get("pages_scraped", 0),
                    "status": s.metadata.get("status", "unknown"),
                    "engine": s.metadata.get("engine", ""),
                    "deep": s.metadata.get("deep_research", False),
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            return []
