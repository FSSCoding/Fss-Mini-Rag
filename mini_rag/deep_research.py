"""
Deep research engine for Mini RAG.

Runs iterative research cycles: analyze → search → scrape → prune → report.
Supports time-budgeted unattended operation and folder-only analysis mode.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from .config import DeepResearchConfig, RAGConfig
from .web_scraper import MiniWebScraper, ResearchSession

logger = logging.getLogger(__name__)
console = Console()


# ──────────────────────────────────────────────────────────
# Session Metrics — analytics layer
# ──────────────────────────────────────────────────────────


@dataclass
class FileRecord:
    """Registry entry for a single file in the corpus."""

    path: str  # Relative to session dir
    url: str = ""
    title: str = ""
    char_count: int = 0
    word_count: int = 0
    token_estimate: int = 0  # chars // 4
    source_type: str = "web"  # web, pdf, arxiv, github
    scraped_at: str = ""
    round_added: int = 0
    relevance_score: float = 0.0  # 0-1, computed by analyzer
    duplicate_of: str = ""  # filename if marked as duplicate
    is_pruned: bool = False

    def to_dict(self) -> Dict:
        return {
            "path": self.path, "url": self.url, "title": self.title,
            "char_count": self.char_count, "word_count": self.word_count,
            "token_estimate": self.token_estimate, "source_type": self.source_type,
            "scraped_at": self.scraped_at, "round_added": self.round_added,
            "relevance_score": self.relevance_score, "duplicate_of": self.duplicate_of,
            "is_pruned": self.is_pruned,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "FileRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RoundSnapshot:
    """Metrics snapshot for a single research round."""

    round_num: int = 0
    started_at: str = ""
    duration_minutes: float = 0
    phase_times: Dict[str, float] = field(default_factory=dict)
    pages_attempted: int = 0
    pages_scraped: int = 0
    pages_pruned: int = 0
    chars_added: int = 0
    tokens_added: int = 0
    queries_used: List[str] = field(default_factory=list)
    confidence: str = "LOW"
    gaps_count: int = 0
    topics_covered_count: int = 0
    llm_calls: int = 0
    llm_failures: int = 0
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    scrape_attempts: int = 0
    scrape_successes: int = 0
    scrape_failures_by_reason: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "round_num": self.round_num, "started_at": self.started_at,
            "duration_minutes": self.duration_minutes, "phase_times": self.phase_times,
            "pages_attempted": self.pages_attempted, "pages_scraped": self.pages_scraped,
            "pages_pruned": self.pages_pruned, "chars_added": self.chars_added,
            "tokens_added": self.tokens_added, "queries_used": self.queries_used,
            "confidence": self.confidence, "gaps_count": self.gaps_count,
            "topics_covered_count": self.topics_covered_count,
            "llm_calls": self.llm_calls, "llm_failures": self.llm_failures,
            "llm_tokens_in": self.llm_tokens_in, "llm_tokens_out": self.llm_tokens_out,
            "scrape_attempts": self.scrape_attempts, "scrape_successes": self.scrape_successes,
            "scrape_failures_by_reason": self.scrape_failures_by_reason,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "RoundSnapshot":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SessionMetrics:
    """Comprehensive analytics for a research session.

    Persists to metrics.json alongside session.json.
    Provides the data foundation for intelligent decision-making:
    - File registry with per-file stats and relevance
    - Per-round snapshots with deltas
    - LLM call tracking (count, tokens, failures)
    - Scrape stats (attempted vs succeeded, by domain)
    - Corpus growth curve (cumulative tokens per round)
    - Confidence history
    """

    def __init__(self, session: ResearchSession):
        self.session = session
        self._path = session.session_dir / "metrics.json"

        # Core state
        self.file_registry: Dict[str, FileRecord] = {}  # keyed by relative path
        self.round_snapshots: List[RoundSnapshot] = []
        self.current_round: Optional[RoundSnapshot] = None

        # Cumulative LLM stats
        self.total_llm_calls: int = 0
        self.total_llm_failures: int = 0
        self.total_llm_tokens_in: int = 0
        self.total_llm_tokens_out: int = 0

        # Scrape stats by domain
        self.domain_stats: Dict[str, Dict[str, int]] = {}  # domain → {attempts, successes, failures}

        # Confidence history
        self.confidence_history: List[Dict[str, str]] = []  # [{round, confidence, gaps_count}]

        # Load existing
        self._load()

    def _load(self):
        """Load metrics from disk if they exist."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
            self.file_registry = {
                k: FileRecord.from_dict(v) for k, v in data.get("file_registry", {}).items()
            }
            self.round_snapshots = [
                RoundSnapshot.from_dict(r) for r in data.get("round_snapshots", [])
            ]
            self.total_llm_calls = data.get("total_llm_calls", 0)
            self.total_llm_failures = data.get("total_llm_failures", 0)
            self.total_llm_tokens_in = data.get("total_llm_tokens_in", 0)
            self.total_llm_tokens_out = data.get("total_llm_tokens_out", 0)
            self.domain_stats = data.get("domain_stats", {})
            self.confidence_history = data.get("confidence_history", [])
        except Exception as e:
            logger.warning(f"Could not load metrics: {e}")

    def save(self):
        """Persist metrics to disk."""
        data = {
            "file_registry": {k: v.to_dict() for k, v in self.file_registry.items()},
            "round_snapshots": [r.to_dict() for r in self.round_snapshots],
            "total_llm_calls": self.total_llm_calls,
            "total_llm_failures": self.total_llm_failures,
            "total_llm_tokens_in": self.total_llm_tokens_in,
            "total_llm_tokens_out": self.total_llm_tokens_out,
            "domain_stats": self.domain_stats,
            "confidence_history": self.confidence_history,
            "summary": self.get_summary(),
        }
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)

    # ── Round lifecycle ──

    def begin_round(self, round_num: int):
        """Start tracking a new round."""
        self.current_round = RoundSnapshot(
            round_num=round_num,
            started_at=datetime.now().isoformat(),
        )

    def end_round(self, duration_minutes: float):
        """Finalize current round and archive it."""
        if not self.current_round:
            return
        self.current_round.duration_minutes = round(duration_minutes, 2)
        self.round_snapshots.append(self.current_round)
        self.current_round = None
        self.save()

    def record_phase_time(self, phase: str, duration_minutes: float):
        """Record time spent in a phase for the current round."""
        if self.current_round:
            self.current_round.phase_times[phase] = (
                self.current_round.phase_times.get(phase, 0) + round(duration_minutes, 3)
            )

    # ── File registry ──

    def register_file(
        self, filepath: Path, url: str = "", title: str = "",
        source_type: str = "web", round_added: int = 0,
    ):
        """Register a file in the corpus with its stats."""
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            char_count = len(text)
            word_count = len(text.split())
        except Exception:
            char_count = 0
            word_count = 0

        rel_path = str(filepath.relative_to(self.session.session_dir))
        record = FileRecord(
            path=rel_path,
            url=url,
            title=title or filepath.stem,
            char_count=char_count,
            word_count=word_count,
            token_estimate=char_count // 4,
            source_type=source_type,
            scraped_at=datetime.now().isoformat(),
            round_added=round_added,
        )
        self.file_registry[rel_path] = record

        # Update current round
        if self.current_round:
            self.current_round.chars_added += char_count
            self.current_round.tokens_added += char_count // 4
            self.current_round.pages_scraped += 1

        self.save()
        return record

    def mark_pruned(self, filepath: Path, duplicate_of: str = ""):
        """Mark a file as pruned in the registry."""
        rel_path = str(filepath.relative_to(self.session.session_dir))
        if rel_path in self.file_registry:
            self.file_registry[rel_path].is_pruned = True
            self.file_registry[rel_path].duplicate_of = duplicate_of
        if self.current_round:
            self.current_round.pages_pruned += 1

    def set_relevance(self, filepath: Path, score: float):
        """Set relevance score for a file."""
        rel_path = str(filepath.relative_to(self.session.session_dir))
        if rel_path in self.file_registry:
            self.file_registry[rel_path].relevance_score = round(score, 3)

    # ── LLM tracking ──

    def record_llm_call(self, tokens_in: int = 0, tokens_out: int = 0, success: bool = True):
        """Record an LLM call with token counts."""
        self.total_llm_calls += 1
        self.total_llm_tokens_in += tokens_in
        self.total_llm_tokens_out += tokens_out

        if self.current_round:
            self.current_round.llm_calls += 1
            self.current_round.llm_tokens_in += tokens_in
            self.current_round.llm_tokens_out += tokens_out

        if not success:
            self.total_llm_failures += 1
            if self.current_round:
                self.current_round.llm_failures += 1

    # ── Scrape tracking ──

    def record_scrape_attempt(self, url: str, success: bool, failure_reason: str = ""):
        """Record a scrape attempt with outcome."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        if domain not in self.domain_stats:
            self.domain_stats[domain] = {"attempts": 0, "successes": 0, "failures": 0}

        self.domain_stats[domain]["attempts"] += 1
        if success:
            self.domain_stats[domain]["successes"] += 1
        else:
            self.domain_stats[domain]["failures"] += 1

        if self.current_round:
            self.current_round.scrape_attempts += 1
            if success:
                self.current_round.scrape_successes += 1
            elif failure_reason:
                self.current_round.scrape_failures_by_reason[failure_reason] = (
                    self.current_round.scrape_failures_by_reason.get(failure_reason, 0) + 1
                )

    # ── Confidence tracking ──

    def record_confidence(self, round_num: int, confidence: str, gaps_count: int, topics_count: int):
        """Record confidence level for trend analysis."""
        self.confidence_history.append({
            "round": round_num,
            "confidence": confidence,
            "gaps_count": gaps_count,
            "topics_covered": topics_count,
            "timestamp": datetime.now().isoformat(),
        })
        if self.current_round:
            self.current_round.confidence = confidence
            self.current_round.gaps_count = gaps_count
            self.current_round.topics_covered_count = topics_count

    # ── Analytics queries ──

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics for reporting."""
        active_files = [f for f in self.file_registry.values() if not f.is_pruned]
        pruned_files = [f for f in self.file_registry.values() if f.is_pruned]

        return {
            "total_files": len(self.file_registry),
            "active_files": len(active_files),
            "pruned_files": len(pruned_files),
            "total_chars": sum(f.char_count for f in active_files),
            "total_words": sum(f.word_count for f in active_files),
            "total_tokens": sum(f.token_estimate for f in active_files),
            "rounds_completed": len(self.round_snapshots),
            "total_llm_calls": self.total_llm_calls,
            "total_llm_failures": self.total_llm_failures,
            "total_llm_tokens": self.total_llm_tokens_in + self.total_llm_tokens_out,
            "scrape_success_rate": self._scrape_success_rate(),
            "corpus_growth": self._corpus_growth_curve(),
            "confidence_trend": self._confidence_trend(),
            "failing_domains": self._failing_domains(),
            "avg_round_minutes": self._avg_round_duration(),
        }

    def get_active_files(self) -> List[FileRecord]:
        """Get all non-pruned files, sorted by relevance."""
        return sorted(
            [f for f in self.file_registry.values() if not f.is_pruned],
            key=lambda f: f.relevance_score,
            reverse=True,
        )

    def corpus_is_stalling(self, min_tokens_per_round: int = 500) -> bool:
        """Check if research is producing diminishing returns.

        Returns True if the last 2 rounds each added fewer than min_tokens_per_round.
        """
        if len(self.round_snapshots) < 2:
            return False
        last_two = self.round_snapshots[-2:]
        return all(r.tokens_added < min_tokens_per_round for r in last_two)

    def should_skip_domain(self, domain: str, failure_threshold: int = 3) -> bool:
        """Check if a domain has failed too many times and should be skipped."""
        stats = self.domain_stats.get(domain, {})
        return stats.get("failures", 0) >= failure_threshold and stats.get("successes", 0) == 0

    def _scrape_success_rate(self) -> float:
        """Overall scrape success rate across all domains."""
        total_attempts = sum(d.get("attempts", 0) for d in self.domain_stats.values())
        total_successes = sum(d.get("successes", 0) for d in self.domain_stats.values())
        if total_attempts == 0:
            return 0.0
        return round(total_successes / total_attempts, 3)

    def _corpus_growth_curve(self) -> List[Dict[str, Any]]:
        """Cumulative token count per round — shows growth trajectory."""
        curve = []
        cumulative = 0
        for snap in self.round_snapshots:
            cumulative += snap.tokens_added
            curve.append({
                "round": snap.round_num,
                "tokens_added": snap.tokens_added,
                "cumulative_tokens": cumulative,
            })
        return curve

    def _confidence_trend(self) -> List[str]:
        """Confidence values across rounds."""
        return [c["confidence"] for c in self.confidence_history]

    def _failing_domains(self) -> List[str]:
        """Domains with 0 successes and multiple failures."""
        return [
            domain for domain, stats in self.domain_stats.items()
            if stats.get("failures", 0) >= 2 and stats.get("successes", 0) == 0
        ]

    def _avg_round_duration(self) -> float:
        """Average round duration in minutes."""
        if not self.round_snapshots:
            return 0.0
        return round(
            sum(r.duration_minutes for r in self.round_snapshots) / len(self.round_snapshots), 2
        )


# ──────────────────────────────────────────────────────────
# Prompt Templates
# ──────────────────────────────────────────────────────────
# All LLM prompts are defined here as templates for easy editing.
# Parameters are substituted with .format() at call time.


PROMPT_GAP_ANALYSIS = """\
You are a research analyst evaluating a corpus of documents on a specific topic.

RESEARCH TOPIC: {topic}

CURRENT CORPUS SUMMARY (excerpts from {num_sources} source documents):

{corpus_summary}

---

Analyze what this corpus covers well and what is missing. Respond in EXACTLY this format:

COVERED: [comma-separated list of subtopics that are well-covered]
GAPS: [comma-separated list of important subtopics that are missing or weak]
QUERIES: [3-5 specific web search queries that would fill the most important gaps, one per line]
CONFIDENCE: [LOW/MEDIUM/HIGH — how complete is this corpus on the topic]

Be specific. Name actual concepts, theories, authors, or data points — not vague categories.\
"""

PROMPT_QUERY_GENERATION = """\
Given these research gaps on the topic "{topic}":

{gaps}

Generate {num_queries} specific web search queries that would find information to fill these gaps.
One query per line. No numbering, no bullets, no explanations. Just the search queries.\
"""

PROMPT_SIMILARITY_CHECK = """\
Compare these two document excerpts. Respond with exactly one word:
DUPLICATE — essentially the same content from different sources
RELATED — overlapping topic but meaningfully different information
UNRELATED — different topics entirely

DOCUMENT A:
{doc_a}

DOCUMENT B:
{doc_b}

Your response (one word only):\
"""

PROMPT_CORPUS_ASSESSMENT = """\
You are reviewing a research corpus on: {topic}

Here are brief summaries of {num_sources} source documents:

{source_list}

Write a brief research assessment (3-5 paragraphs) covering:
1. What the corpus covers well
2. Key gaps or missing perspectives
3. Any contradictions or inconsistencies between sources
4. Suggested next steps for this research

Be specific and cite document titles where relevant.\
"""


# ──────────────────────────────────────────────────────────
# Research Phase State Machine
# ──────────────────────────────────────────────────────────


class ResearchPhase(str, Enum):
    """Phases of the deep research cycle."""

    IDLE = "idle"
    ANALYZE = "analyze"
    SEARCH = "search"
    SCRAPE = "scrape"
    PRUNE = "prune"
    REPORT = "report"
    COMPLETE = "complete"


# ──────────────────────────────────────────────────────────
# Time Budget
# ──────────────────────────────────────────────────────────


class TimeBudget:
    """Tracks time budget for deep research sessions.

    Estimates round duration from history and decides when to
    trigger the final roundup before the deadline.
    """

    DEFAULT_ROUND_ESTIMATE_MINUTES = 10.0
    SAFETY_MARGIN = 1.5  # Multiply estimated round time by this

    def __init__(self, max_minutes: int = 0, roundup_buffer_minutes: int = 5):
        self.max_minutes = max_minutes  # 0 = unlimited
        self.roundup_buffer = roundup_buffer_minutes
        self.start_time = time.time()
        self.round_durations: List[float] = []  # Minutes per round

    def elapsed_minutes(self) -> float:
        return (time.time() - self.start_time) / 60.0

    def remaining_minutes(self) -> float:
        if self.max_minutes <= 0:
            return float("inf")
        return max(0, self.max_minutes - self.elapsed_minutes())

    def estimated_round_minutes(self) -> float:
        """Estimate how long the next round will take."""
        if not self.round_durations:
            return self.DEFAULT_ROUND_ESTIMATE_MINUTES
        # Use average of last 3 rounds with safety margin
        recent = self.round_durations[-3:]
        avg = sum(recent) / len(recent)
        return avg * self.SAFETY_MARGIN

    def should_roundup(self) -> bool:
        """True if we should start the final roundup (not enough time for another round)."""
        if self.max_minutes <= 0:
            return False
        remaining = self.remaining_minutes()
        needed = self.estimated_round_minutes() + self.roundup_buffer
        return remaining < needed

    def record_round(self, duration_minutes: float):
        """Record how long a round took for future estimation."""
        self.round_durations.append(duration_minutes)

    def is_expired(self) -> bool:
        """True if we've exceeded the time budget entirely."""
        if self.max_minutes <= 0:
            return False
        return self.elapsed_minutes() >= self.max_minutes


# ──────────────────────────────────────────────────────────
# Research Report
# ──────────────────────────────────────────────────────────


@dataclass
class ResearchReport:
    """Comprehensive report of a deep research session."""

    rounds_completed: int = 0
    total_time_minutes: float = 0
    time_per_phase: Dict[str, float] = field(default_factory=dict)
    searches_performed: int = 0
    search_queries_used: List[str] = field(default_factory=list)
    pages_found: int = 0
    pages_scraped: int = 0
    pages_pruned: int = 0
    total_chars: int = 0
    estimated_tokens: int = 0
    topics_covered: List[str] = field(default_factory=list)
    gaps_remaining: List[str] = field(default_factory=list)
    corroborations: List[str] = field(default_factory=list)
    inconsistencies: List[str] = field(default_factory=list)
    confidence: str = "LOW"
    # Metrics-sourced fields
    llm_calls: int = 0
    llm_failures: int = 0
    llm_total_tokens: int = 0
    scrape_success_rate: float = 0.0
    failing_domains: List[str] = field(default_factory=list)
    corpus_growth: List[Dict[str, Any]] = field(default_factory=list)
    confidence_trend: List[str] = field(default_factory=list)

    def to_markdown(self, query: str) -> str:
        """Generate a markdown research report."""
        lines = [
            f"# Research Report: {query}",
            f"",
            f"**Generated:** {datetime.now().isoformat()[:19]}",
            f"**Rounds:** {self.rounds_completed}",
            f"**Duration:** {self.total_time_minutes:.1f} minutes",
            f"**Confidence:** {self.confidence}",
            f"",
            f"## Statistics",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Searches performed | {self.searches_performed} |",
            f"| Pages found | {self.pages_found} |",
            f"| Pages scraped | {self.pages_scraped} |",
            f"| Pages pruned | {self.pages_pruned} |",
            f"| Total characters | {self.total_chars:,} |",
            f"| Estimated tokens | {self.estimated_tokens:,} |",
            f"| LLM calls | {self.llm_calls} ({self.llm_failures} failed) |",
            f"| LLM tokens used | {self.llm_total_tokens:,} |",
            f"| Scrape success rate | {self.scrape_success_rate:.0%} |",
            f"",
        ]

        if self.confidence_trend and len(self.confidence_trend) > 1:
            lines.append(f"**Confidence trend:** {' → '.join(self.confidence_trend)}\n")

        if self.corpus_growth:
            lines.append("## Corpus Growth\n")
            lines.append("| Round | Tokens added | Cumulative |")
            lines.append("|-------|-------------|------------|")
            for g in self.corpus_growth:
                lines.append(
                    f"| {g['round']} | {g['tokens_added']:,} | {g['cumulative_tokens']:,} |"
                )
            lines.append("")

        if self.time_per_phase:
            lines.append("## Time per Phase\n")
            for phase, mins in self.time_per_phase.items():
                lines.append(f"- **{phase}:** {mins:.1f} min")
            lines.append("")

        if self.search_queries_used:
            lines.append("## Search Queries Used\n")
            for q in self.search_queries_used:
                lines.append(f"- {q}")
            lines.append("")

        if self.topics_covered:
            lines.append("## Topics Covered\n")
            for t in self.topics_covered:
                lines.append(f"- {t}")
            lines.append("")

        if self.gaps_remaining:
            lines.append("## Gaps Remaining\n")
            for g in self.gaps_remaining:
                lines.append(f"- {g}")
            lines.append("")

        if self.corroborations:
            lines.append("## Corroborated Findings\n")
            lines.append("*Claims found in multiple sources (stronger evidence):*\n")
            for c in self.corroborations:
                lines.append(f"- {c}")
            lines.append("")

        if self.inconsistencies:
            lines.append("## Inconsistencies Found\n")
            lines.append("*Contradictions between sources (needs resolution):*\n")
            for i in self.inconsistencies:
                lines.append(f"- {i}")
            lines.append("")

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# Context Manager — manages what goes to the LLM
# ──────────────────────────────────────────────────────────


class ContextManager:
    """Manages context window budget for LLM calls.

    Ensures we never exceed the model's context window by
    truncating and summarizing content as needed.
    """

    def __init__(self, max_tokens: int = 16384):
        self.max_tokens = max_tokens

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from character count (chars / 4)."""
        return len(text) // 4

    def budget_for_prompt(self, prompt_template: str, **kwargs) -> int:
        """Calculate remaining token budget after the prompt template."""
        template_tokens = self.estimate_tokens(prompt_template)
        # Reserve 20% for the response
        response_reserve = int(self.max_tokens * 0.20)
        return self.max_tokens - template_tokens - response_reserve

    def truncate_to_budget(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within a token budget."""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        # Truncate with indicator
        return text[: max_chars - 20] + "\n\n[... truncated]"

    def build_corpus_summary(
        self, source_files: List[Path], max_tokens: int
    ) -> str:
        """Build a corpus summary that fits within the token budget.

        Reads source files and excerpts them proportionally to fit.
        """
        if not source_files:
            return "(no sources yet)"

        # Calculate per-file budget
        per_file_tokens = max(200, max_tokens // len(source_files))
        per_file_chars = per_file_tokens * 4

        parts = []
        for filepath in source_files:
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
                # Skip frontmatter
                if text.startswith("---"):
                    end = text.find("---", 3)
                    if end > 0:
                        text = text[end + 3:].strip()

                # Get title from first heading
                title = filepath.stem
                for line in text.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                # Excerpt
                excerpt = text[:per_file_chars]
                if len(text) > per_file_chars:
                    excerpt = excerpt.rsplit(" ", 1)[0] + " [...]"

                parts.append(f"### {title}\n\n{excerpt}")

            except Exception as e:
                logger.debug(f"Could not read {filepath}: {e}")

        return "\n\n---\n\n".join(parts)


# ──────────────────────────────────────────────────────────
# Research Analyzer — the ANALYZE phase
# ──────────────────────────────────────────────────────────


@dataclass
class AnalysisResult:
    """Result of analyzing the current corpus."""

    covered_topics: List[str] = field(default_factory=list)
    gap_topics: List[str] = field(default_factory=list)
    follow_up_queries: List[str] = field(default_factory=list)
    confidence: str = "LOW"
    raw_response: str = ""


class ResearchAnalyzer:
    """Analyzes a research corpus using LLM to identify gaps and generate queries."""

    def __init__(self, llm_call, context_manager: ContextManager):
        """
        Args:
            llm_call: Callable that takes (prompt: str, temperature: float) -> Optional[str]
            context_manager: ContextManager for token budgeting
        """
        self._call_llm = llm_call
        self.ctx = context_manager

    def analyze(self, session: ResearchSession, topic: str) -> AnalysisResult:
        """Analyze the corpus and identify gaps.

        Returns structured analysis with covered topics, gaps, and follow-up queries.
        """
        source_files = session.get_all_source_files()

        if not source_files:
            return AnalysisResult(
                gap_topics=[topic],
                follow_up_queries=[topic],
                confidence="LOW",
            )

        # Build corpus summary within token budget
        budget = self.ctx.budget_for_prompt(PROMPT_GAP_ANALYSIS)
        corpus_summary = self.ctx.build_corpus_summary(source_files, budget)

        prompt = PROMPT_GAP_ANALYSIS.format(
            topic=topic,
            num_sources=len(source_files),
            corpus_summary=corpus_summary,
        )

        response = self._call_llm(prompt, 0.3)
        if not response:
            logger.warning("LLM returned no response for gap analysis")
            return AnalysisResult(
                gap_topics=[topic],
                follow_up_queries=[topic],
                confidence="LOW",
            )

        return self._parse_analysis(response)

    def generate_queries(self, topic: str, gaps: List[str], num_queries: int = 5) -> List[str]:
        """Generate web search queries from identified gaps."""
        if not gaps:
            return [topic]

        prompt = PROMPT_QUERY_GENERATION.format(
            topic=topic,
            gaps="\n".join(f"- {g}" for g in gaps),
            num_queries=num_queries,
        )

        response = self._call_llm(prompt, 0.5)
        if not response:
            return [topic]

        queries = [
            line.strip() for line in response.strip().split("\n")
            if line.strip() and not line.strip().startswith(("#", "-", "*"))
        ]
        # Strip any numbering like "1. " or "1) "
        import re
        queries = [re.sub(r"^\d+[\.\)]\s*", "", q) for q in queries]

        return queries[:num_queries] if queries else [topic]

    def assess_corpus(self, session: ResearchSession, topic: str) -> str:
        """Generate a full prose assessment of the corpus. Used for final report."""
        source_files = session.get_all_source_files()
        if not source_files:
            return "No sources to assess."

        budget = self.ctx.budget_for_prompt(PROMPT_CORPUS_ASSESSMENT)

        # Build brief source list (title + word count)
        source_list_parts = []
        for f in source_files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                wc = len(text.split())
                title = f.stem.replace("-", " ").title()
                source_list_parts.append(f"- **{title}** ({wc} words)")
            except Exception:
                pass

        source_list = "\n".join(source_list_parts)
        if self.ctx.estimate_tokens(source_list) > budget // 2:
            source_list = self.ctx.truncate_to_budget(source_list, budget // 2)

        prompt = PROMPT_CORPUS_ASSESSMENT.format(
            topic=topic,
            num_sources=len(source_files),
            source_list=source_list,
        )

        return self._call_llm(prompt, 0.3) or "Assessment could not be generated."

    def _parse_analysis(self, response: str) -> AnalysisResult:
        """Parse structured LLM response into AnalysisResult."""
        result = AnalysisResult(raw_response=response)

        for line in response.split("\n"):
            line = line.strip()
            if line.upper().startswith("COVERED:"):
                items = line.split(":", 1)[1].strip()
                result.covered_topics = [t.strip() for t in items.split(",") if t.strip()]
            elif line.upper().startswith("GAPS:"):
                items = line.split(":", 1)[1].strip()
                result.gap_topics = [t.strip() for t in items.split(",") if t.strip()]
            elif line.upper().startswith("CONFIDENCE:"):
                conf = line.split(":", 1)[1].strip().upper()
                if conf in ("LOW", "MEDIUM", "HIGH"):
                    result.confidence = conf
            elif line.upper().startswith("QUERIES:"):
                # Queries may be on the same line or following lines
                q = line.split(":", 1)[1].strip()
                if q:
                    # Handle comma-separated queries (possibly quoted)
                    # e.g. "query one", "query two", "query three"
                    import re as _re
                    quoted = _re.findall(r'"([^"]+)"', q)
                    if quoted:
                        result.follow_up_queries.extend(quoted)
                    elif "," in q and len(q) > 50:
                        # Long comma-separated line — split on commas
                        result.follow_up_queries.extend(
                            part.strip().strip('"\'') for part in q.split(",") if part.strip()
                        )
                    else:
                        result.follow_up_queries.append(q)
            elif result.follow_up_queries is not None and line and not line.startswith(("COVERED", "GAPS", "CONFIDENCE")):
                # Continuation lines after QUERIES:
                if any(line.upper().startswith(k) for k in ("COVERED", "GAPS", "CONFIDENCE")):
                    continue
                # Looks like a query line
                cleaned = line.lstrip("- •*0123456789.) ")
                if cleaned and len(cleaned) > 5:
                    result.follow_up_queries.append(cleaned)

        return result


# ──────────────────────────────────────────────────────────
# Corpus Pruner — the PRUNE phase
# ──────────────────────────────────────────────────────────


class CorpusPruner:
    """Deduplicates and evaluates source consistency.

    v1 approach:
    - Character-level similarity for fast dedup (>90% = duplicate)
    - LLM confirmation for borderline cases (70-90%)
    - Corroboration detection via keyword overlap
    - NEVER deletes non-duplicate sources, only flags
    """

    DUPLICATE_THRESHOLD = 0.90  # Above this = definite duplicate
    BORDERLINE_LOW = 0.70  # Below this = definitely not duplicate

    def __init__(self, llm_call=None):
        """
        Args:
            llm_call: Optional callable for borderline similarity checks.
                      If None, borderline cases are kept (conservative).
        """
        self._call_llm = llm_call

    def prune(self, session: ResearchSession) -> Dict[str, Any]:
        """Run pruning on session sources.

        Returns dict with stats and findings.
        """
        source_files = session.get_all_source_files()
        if len(source_files) < 2:
            return {"duplicates": [], "corroborations": [], "flagged": [], "removed": []}

        # Load content (first 2000 chars normalized for comparison)
        file_contents = {}
        for f in source_files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                # Strip frontmatter
                if text.startswith("---"):
                    end = text.find("---", 3)
                    if end > 0:
                        text = text[end + 3:]
                file_contents[f] = self._normalize(text[:2000])
            except Exception:
                pass

        duplicates = []
        corroborations = []
        flagged = []

        # Pairwise comparison
        files = list(file_contents.keys())
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                sim = self._similarity(file_contents[files[i]], file_contents[files[j]])

                if sim >= self.DUPLICATE_THRESHOLD:
                    duplicates.append((files[i].name, files[j].name, sim))
                elif sim >= self.BORDERLINE_LOW:
                    # Borderline — check with LLM if available
                    if self._call_llm:
                        verdict = self._llm_similarity_check(
                            file_contents[files[i]][:500],
                            file_contents[files[j]][:500],
                        )
                        if verdict == "DUPLICATE":
                            duplicates.append((files[i].name, files[j].name, sim))
                        elif verdict == "RELATED":
                            corroborations.append((files[i].name, files[j].name))
                    else:
                        # Conservative: flag as related
                        corroborations.append((files[i].name, files[j].name))

        # Remove true duplicates (keep the first/older file)
        removed = []
        for name_a, name_b, sim in duplicates:
            dup_path = session.sources_dir / name_b
            if dup_path.exists():
                dup_path.unlink()
                removed.append(name_b)
                session.metadata["pages_pruned"] = session.metadata.get("pages_pruned", 0) + 1
                logger.info(f"Removed duplicate: {name_b} (sim={sim:.2f} with {name_a})")

        session.save_metadata()

        return {
            "duplicates": [(a, b, f"{s:.2f}") for a, b, s in duplicates],
            "corroborations": corroborations,
            "flagged": flagged,
            "removed": removed,
        }

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        import re
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s]", "", text)
        return text.strip()

    def _similarity(self, text_a: str, text_b: str) -> float:
        """Character-level similarity between two normalized texts.

        Uses Jaccard similarity on character trigrams for speed.
        """
        if not text_a or not text_b:
            return 0.0

        trigrams_a = set(text_a[i:i + 3] for i in range(len(text_a) - 2))
        trigrams_b = set(text_b[i:i + 3] for i in range(len(text_b) - 2))

        if not trigrams_a or not trigrams_b:
            return 0.0

        intersection = trigrams_a & trigrams_b
        union = trigrams_a | trigrams_b
        return len(intersection) / len(union)

    def _llm_similarity_check(self, doc_a: str, doc_b: str) -> str:
        """Ask LLM to classify similarity between two excerpts."""
        prompt = PROMPT_SIMILARITY_CHECK.format(doc_a=doc_a, doc_b=doc_b)
        response = self._call_llm(prompt, 0.1)
        if response:
            word = response.strip().split()[0].upper()
            if word in ("DUPLICATE", "RELATED", "UNRELATED"):
                return word
        return "RELATED"  # Conservative fallback


# ──────────────────────────────────────────────────────────
# Deep Research Engine — the orchestrator
# ──────────────────────────────────────────────────────────


class DeepResearchEngine:
    """Orchestrates iterative deep research cycles.

    Runs: ANALYZE → SEARCH → SCRAPE → ANALYZE → PRUNE → REPORT
    within a time budget, producing a comprehensive research corpus.
    """

    def __init__(
        self,
        session: ResearchSession,
        config: DeepResearchConfig,
        rag_config: RAGConfig,
        llm_call,
        scraper: MiniWebScraper,
        search_engine,
    ):
        self.session = session
        self.config = config
        self.rag_config = rag_config
        self._call_llm = llm_call
        self.scraper = scraper
        self.search_engine = search_engine

        context_window = rag_config.llm.context_window if rag_config.llm else 16384
        self.ctx = ContextManager(max_tokens=context_window)
        self.metrics = SessionMetrics(session)
        self.analyzer = ResearchAnalyzer(self._tracked_llm_call, self.ctx)
        self.pruner = CorpusPruner(self._tracked_llm_call)
        self.report = ResearchReport()

        # Rate limiters
        from .rate_limiter import get_limiter, get_retry_config, retry_with_backoff
        self._llm_limiter = get_limiter("llm")
        self._llm_retry = get_retry_config("llm")

    def _tracked_llm_call(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
        """Wrapper around LLM call with rate limiting, retry, and metrics."""
        from .rate_limiter import retry_with_backoff

        tokens_in = len(prompt) // 4

        def _do_call():
            return self._call_llm(prompt, temperature)

        try:
            response = retry_with_backoff(
                _do_call,
                config=self._llm_retry,
                rate_limiter=self._llm_limiter,
            )
        except Exception as e:
            logger.warning(f"LLM call failed after retries: {e}")
            self.metrics.record_llm_call(tokens_in=tokens_in, tokens_out=0, success=False)
            return None

        tokens_out = len(response) // 4 if response else 0
        self.metrics.record_llm_call(
            tokens_in=tokens_in, tokens_out=tokens_out, success=response is not None,
        )
        return response

    def run(
        self,
        max_time_minutes: int = 0,
        max_rounds: int = 5,
    ) -> ResearchReport:
        """Run the deep research loop.

        Args:
            max_time_minutes: Time budget (0 = use max_rounds only)
            max_rounds: Maximum research cycles

        Returns:
            ResearchReport with comprehensive stats
        """
        budget = TimeBudget(
            max_minutes=max_time_minutes or self.config.max_time_minutes,
            roundup_buffer_minutes=self.config.roundup_buffer_minutes,
        )
        rounds = max_rounds or self.config.max_rounds
        topic = self.session.query

        self.session.metadata["deep_research"] = True
        self.session.save_metadata()

        console.print(f"\n[bold cyan]Deep Research:[/bold cyan] {topic}")
        if budget.max_minutes > 0:
            console.print(f"Time budget: {budget.max_minutes} minutes  Max rounds: {rounds}")
        else:
            console.print(f"Max rounds: {rounds}")
        console.print()

        try:
            for round_num in range(1, rounds + 1):
                round_start = time.time()

                # Check time budget
                if budget.should_roundup() or budget.is_expired():
                    console.print(
                        f"\n[yellow]Time budget: {budget.remaining_minutes():.0f}min remaining "
                        f"— starting final roundup[/yellow]"
                    )
                    break

                # Round header with time and corpus stats
                elapsed = budget.elapsed_minutes()
                remaining = budget.remaining_minutes()
                corpus_summary = self.metrics.get_summary()
                time_str = f"{elapsed:.0f}m elapsed"
                if budget.max_minutes > 0:
                    time_str += f", {remaining:.0f}m remaining"
                corpus_str = (
                    f"{corpus_summary['active_files']} files, "
                    f"~{corpus_summary['total_tokens']:,} tokens"
                )

                console.print(f"[bold]━━━ Round {round_num}/{rounds} ━━━[/bold]  "
                              f"[dim]({time_str} | {corpus_str})[/dim]")
                self.session.metadata["rounds"] = round_num
                self.metrics.begin_round(round_num)

                # Check if research is stalling
                if self.metrics.corpus_is_stalling():
                    console.print(
                        "  [yellow]Research is stalling (minimal new content) "
                        "— triggering final roundup[/yellow]"
                    )
                    break

                # ── ANALYZE ──
                phase_start = time.time()
                self.session.set_phase(ResearchPhase.ANALYZE.value)
                src_count = len(self.session.get_all_source_files())
                console.print(f"  [cyan]ANALYZE:[/cyan] Evaluating corpus ({src_count} sources)...")

                analysis = self.analyzer.analyze(self.session, topic)

                console.print(f"    Covered: {len(analysis.covered_topics)} topics")
                console.print(f"    Gaps: {len(analysis.gap_topics)} identified")
                console.print(f"    Confidence: {analysis.confidence}")

                self.report.topics_covered = analysis.covered_topics
                self.report.gaps_remaining = analysis.gap_topics
                self.report.confidence = analysis.confidence
                self.metrics.record_confidence(
                    round_num, analysis.confidence,
                    len(analysis.gap_topics), len(analysis.covered_topics),
                )
                phase_duration = (time.time() - phase_start) / 60.0
                self._record_phase_time("analyze", phase_start)
                self.metrics.record_phase_time("analyze", phase_duration)

                # Write analysis to agent-notes
                self.session.add_agent_note(
                    f"analysis-round-{round_num}.md",
                    f"# Analysis — Round {round_num}\n\n"
                    f"**Covered:** {', '.join(analysis.covered_topics)}\n\n"
                    f"**Gaps:** {', '.join(analysis.gap_topics)}\n\n"
                    f"**Confidence:** {analysis.confidence}\n\n"
                    f"**Follow-up queries:**\n"
                    + "\n".join(f"- {q}" for q in analysis.follow_up_queries)
                )

                # If high confidence and no gaps, we're done
                if analysis.confidence == "HIGH" and not analysis.gap_topics:
                    console.print("  [green]Corpus is comprehensive — stopping research[/green]")
                    break

                # ── SEARCH ──
                phase_start = time.time()
                self.session.set_phase(ResearchPhase.SEARCH.value)

                queries = analysis.follow_up_queries
                if not queries:
                    queries = self.analyzer.generate_queries(topic, analysis.gap_topics)

                console.print(f"  [cyan]SEARCH:[/cyan] {len(queries)} queries")
                for q in queries:
                    console.print(f"    → {q[:60]}")

                all_urls = []
                for query in queries:
                    results = self.search_engine.search(query, max_results=5)
                    urls = [r.url for r in results if not self.session.has_visited(r.url)]
                    all_urls.extend(urls)
                    self.report.searches_performed += 1
                    self.report.search_queries_used.append(query)
                    self.report.pages_found += len(results)
                    if self.metrics.current_round:
                        self.metrics.current_round.queries_used.append(query)
                        self.metrics.current_round.pages_attempted += len(urls)

                # Deduplicate URLs and skip failing domains
                from urllib.parse import urlparse as _urlparse
                seen = set()
                unique_urls = []
                skipped_domains = 0
                for u in all_urls:
                    if u in seen:
                        continue
                    seen.add(u)
                    domain = _urlparse(u).netloc
                    if self.metrics.should_skip_domain(domain):
                        skipped_domains += 1
                        continue
                    unique_urls.append(u)

                if skipped_domains:
                    console.print(f"    Skipped {skipped_domains} URLs from failing domains")
                console.print(f"    Found {len(unique_urls)} new URLs")
                phase_duration = (time.time() - phase_start) / 60.0
                self._record_phase_time("search", phase_start)
                self.metrics.record_phase_time("search", phase_duration)

                # ── SCRAPE ──
                phase_start = time.time()
                self.session.set_phase(ResearchPhase.SCRAPE.value)
                console.print(f"  [cyan]SCRAPE:[/cyan] Fetching content...")

                scrape_limit = min(
                    len(unique_urls),
                    self.config.max_total_pages - self.session.metadata.get("pages_scraped", 0),
                )
                pages = self.scraper.scrape_urls(
                    unique_urls, self.session, max_pages=scrape_limit,
                )

                # Register scraped files and track attempts
                for url in unique_urls[:scrape_limit]:
                    scraped = any(p.url == url for p in pages)
                    self.metrics.record_scrape_attempt(
                        url, success=scraped,
                        failure_reason="" if scraped else "extraction_failed",
                    )

                for page in pages:
                    console.print(
                        f"    [green]+[/green] [{page.source_type}] "
                        f"{page.title[:55]} — {page.word_count:,} words"
                    )
                    # Register in metrics
                    for f in self.session.sources_dir.iterdir():
                        if f.is_file() and f.suffix == ".md":
                            try:
                                text = f.read_text(encoding="utf-8", errors="replace")
                                if page.url in text:
                                    self.metrics.register_file(
                                        f, url=page.url, title=page.title,
                                        source_type=page.source_type, round_added=round_num,
                                    )
                                    break
                            except Exception:
                                pass

                self.report.pages_scraped += len(pages)
                console.print(f"    Scraped {len(pages)}/{len(unique_urls[:scrape_limit])} pages")
                phase_duration = (time.time() - phase_start) / 60.0
                self._record_phase_time("scrape", phase_start)
                self.metrics.record_phase_time("scrape", phase_duration)

                # ── PRUNE (every other round or last round) ──
                if round_num % 2 == 0 or round_num == rounds:
                    phase_start = time.time()
                    self.session.set_phase(ResearchPhase.PRUNE.value)
                    console.print(f"  [cyan]PRUNE:[/cyan] Checking for duplicates...")

                    prune_result = self.pruner.prune(self.session)

                    # Track pruned files in metrics
                    for removed_name in prune_result.get("removed", []):
                        removed_path = self.session.sources_dir / removed_name
                        dup_source = ""
                        for a, b, _ in prune_result.get("duplicates", []):
                            if b == removed_name:
                                dup_source = a
                                break
                        self.metrics.mark_pruned(removed_path, duplicate_of=dup_source)

                    self.report.pages_pruned += len(prune_result.get("removed", []))
                    self.report.corroborations = [
                        f"{a} ↔ {b}" for a, b in prune_result.get("corroborations", [])
                    ]

                    if prune_result.get("removed"):
                        console.print(f"    Removed {len(prune_result['removed'])} duplicates")
                    if prune_result.get("corroborations"):
                        console.print(f"    Found {len(prune_result['corroborations'])} corroborations")
                    phase_duration = (time.time() - phase_start) / 60.0
                    self._record_phase_time("prune", phase_start)
                    self.metrics.record_phase_time("prune", phase_duration)

                # Record round duration and show summary
                round_duration = (time.time() - round_start) / 60.0
                budget.record_round(round_duration)
                self.metrics.end_round(round_duration)

                # Round summary
                rsnap = self.metrics.round_snapshots[-1] if self.metrics.round_snapshots else None
                if rsnap:
                    console.print(
                        f"  [dim]Round {round_num}: {round_duration:.1f}min, "
                        f"+{rsnap.tokens_added:,} tokens, "
                        f"{rsnap.scrape_successes}/{rsnap.scrape_attempts} scraped, "
                        f"{rsnap.llm_calls} LLM calls[/dim]\n"
                    )
                else:
                    console.print(f"  Round {round_num} complete ({round_duration:.1f} min)\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Research interrupted — generating report...[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error in round: {e}[/red]")
            logger.exception("Deep research error")

        # ── FINAL REPORT ──
        self.session.set_phase(ResearchPhase.REPORT.value)
        console.print(f"[bold]━━━ Final Report ━━━[/bold]")

        # Ensure any incomplete round is ended
        if self.metrics.current_round:
            self.metrics.end_round(0)

        # Pull stats from metrics
        summary = self.metrics.get_summary()

        self.report.total_time_minutes = budget.elapsed_minutes()
        self.report.rounds_completed = self.session.metadata.get("rounds", 0)
        self.report.total_chars = summary["total_chars"]
        self.report.estimated_tokens = summary["total_tokens"]
        self.report.llm_calls = summary["total_llm_calls"]
        self.report.llm_failures = summary["total_llm_failures"]
        self.report.llm_total_tokens = summary["total_llm_tokens"]
        self.report.scrape_success_rate = summary["scrape_success_rate"]
        self.report.failing_domains = summary["failing_domains"]
        self.report.corpus_growth = summary["corpus_growth"]
        self.report.confidence_trend = summary["confidence_trend"]

        # Generate assessment if we have sources
        if summary["active_files"] > 0 and self._call_llm:
            console.print("  Generating corpus assessment...")
            assessment = self.analyzer.assess_corpus(self.session, topic)
            self.session.add_agent_note("corpus-assessment.md", assessment)

        # Write report
        report_md = self.report.to_markdown(topic)
        self.session.add_agent_note("research-report.md", report_md)

        # Save final metrics
        self.metrics.save()

        # Complete
        self.session.metadata["time_elapsed_minutes"] = round(self.report.total_time_minutes, 1)
        self.session.complete()

        # Display summary
        console.print(f"\n  Rounds: {self.report.rounds_completed}")
        console.print(f"  Time: {self.report.total_time_minutes:.1f} min")
        console.print(f"  Sources: {summary['active_files']} ({summary['pruned_files']} pruned)")
        console.print(f"  Tokens: ~{self.report.estimated_tokens:,}")
        console.print(f"  LLM calls: {summary['total_llm_calls']} ({summary['total_llm_failures']} failed)")
        console.print(f"  Scrape rate: {summary['scrape_success_rate']:.0%}")
        if summary["failing_domains"]:
            console.print(f"  Failing domains: {', '.join(summary['failing_domains'][:5])}")
        growth = summary.get("corpus_growth", [])
        if growth:
            console.print(f"  Growth: {' → '.join(str(g['tokens_added']) for g in growth[-5:])} tokens/round")
        console.print(f"  Confidence: {self.report.confidence}")
        trend = summary.get("confidence_trend", [])
        if len(trend) > 1:
            console.print(f"  Trend: {' → '.join(trend)}")
        console.print(f"\n  Report: [blue]{self.session.agent_notes_dir / 'research-report.md'}[/blue]")
        console.print(f"  Metrics: [blue]{self.metrics._path}[/blue]")

        return self.report

    def run_analyze_only(self) -> AnalysisResult:
        """Run analyze phase only — no web search.

        Useful for evaluating an existing folder of documents.
        """
        topic = self.session.query
        self.session.set_phase(ResearchPhase.ANALYZE.value)

        console.print(f"\n[bold cyan]Analyzing corpus:[/bold cyan] {topic}\n")

        analysis = self.analyzer.analyze(self.session, topic)

        console.print(f"  Covered: {', '.join(analysis.covered_topics) or 'none identified'}")
        console.print(f"  Gaps: {', '.join(analysis.gap_topics) or 'none identified'}")
        console.print(f"  Confidence: {analysis.confidence}")

        if analysis.follow_up_queries:
            console.print(f"\n  Suggested searches:")
            for q in analysis.follow_up_queries:
                console.print(f"    → {q}")

        # Write analysis
        self.session.add_agent_note(
            "analysis.md",
            f"# Corpus Analysis: {topic}\n\n"
            f"**Covered:** {', '.join(analysis.covered_topics)}\n\n"
            f"**Gaps:** {', '.join(analysis.gap_topics)}\n\n"
            f"**Confidence:** {analysis.confidence}\n\n"
            f"**Suggested queries:**\n"
            + "\n".join(f"- {q}" for q in analysis.follow_up_queries)
        )

        # Generate full assessment if we have content
        source_files = self.session.get_all_source_files()
        if source_files and self._call_llm:
            console.print("\n  Generating full assessment...")
            assessment = self.analyzer.assess_corpus(self.session, topic)
            self.session.add_agent_note("corpus-assessment.md", assessment)
            console.print(f"  Saved to: [blue]{self.session.agent_notes_dir}[/blue]")

        self.session.set_phase(ResearchPhase.COMPLETE.value)
        return analysis

    def _record_phase_time(self, phase: str, start_time: float):
        """Record time spent in a phase."""
        duration = (time.time() - start_time) / 60.0
        self.report.time_per_phase[phase] = (
            self.report.time_per_phase.get(phase, 0) + duration
        )
