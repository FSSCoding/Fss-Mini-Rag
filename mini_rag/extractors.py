"""
Content extractors for web scraping.

Converts raw HTML and PDF content into clean markdown.
Domain-specific extractors handle known sites (arXiv, GitHub),
with a generic fallback for everything else.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Optional dependencies — graceful degradation
try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False

try:
    import fitz  # pymupdf

    PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False


@dataclass
class ScrapedPage:
    """A single scraped and extracted page."""

    url: str
    title: str
    content: str  # Clean markdown
    scraped_at: str  # ISO timestamp
    word_count: int
    links: List[str] = field(default_factory=list)  # Outbound links for crawling
    source_type: str = "web"  # "web", "pdf", "arxiv", "github"
    raw_bytes: Optional[bytes] = None  # Original file (PDF, etc.) for archival


class ContentExtractor(Protocol):
    """Protocol for content extractors."""

    def can_handle(self, url: str, content_type: str) -> bool: ...

    def extract(self, url: str, raw: bytes, content_type: str) -> Optional[ScrapedPage]: ...


def _slugify(text: str, max_length: int = 60) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_length]


def _make_frontmatter(page: ScrapedPage) -> str:
    """Generate BOBAI-compatible frontmatter for a scraped page."""
    return (
        "---\n"
        "profile: scraped\n"
        'generator: "fss-mini-rag-scraper"\n'
        f'title: "{page.title}"\n'
        f'source_url: "{page.url}"\n'
        f'scraped_at: "{page.scraped_at}"\n'
        f"word_count: {page.word_count}\n"
        f'source_type: "{page.source_type}"\n'
        "content_quality: 1.0\n"
        "---\n\n"
    )


def save_scraped_page(page: ScrapedPage, output_dir: Path) -> Path:
    """Save a scraped page as markdown with frontmatter.

    Returns the path to the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(page.title) or "untitled"
    filename = f"{slug}.md"
    filepath = output_dir / filename

    # Avoid collisions
    counter = 1
    while filepath.exists():
        filename = f"{slug}-{counter}.md"
        filepath = output_dir / filename
        counter += 1

    frontmatter = _make_frontmatter(page)
    footer = (
        f"\n\n---\n*Source: [{page.url}]({page.url}) "
        f"— scraped {page.scraped_at[:10]}*\n"
    )

    content = frontmatter + f"# {page.title}\n\n" + page.content + footer
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Saved: {filepath}")

    # Save original binary (PDF, etc.) alongside the markdown
    if page.raw_bytes and page.source_type in ("pdf", "arxiv"):
        originals_dir = output_dir / "originals"
        originals_dir.mkdir(exist_ok=True)
        ext = ".pdf"  # Default for pdf/arxiv
        original_path = originals_dir / f"{slug}{ext}"
        if not original_path.exists():
            original_path.write_bytes(page.raw_bytes)
            logger.info(f"Saved original: {original_path}")

    return filepath


class GenericExtractor:
    """Generic HTML to markdown extractor using BeautifulSoup.

    Strips navigation, footers, scripts, and other noise.
    Extracts main content and converts to clean markdown.
    """

    # Elements to remove entirely
    REMOVE_TAGS = {
        "script", "style", "nav", "footer", "header", "aside",
        "iframe", "noscript", "svg", "form", "button",
    }

    # Elements likely to contain main content
    CONTENT_SELECTORS = [
        "article",
        "main",
        '[role="main"]',
        ".post-content",
        ".article-content",
        ".entry-content",
        "#content",
        ".content",
    ]

    def can_handle(self, url: str, content_type: str) -> bool:
        return "text/html" in content_type

    def extract(self, url: str, raw: bytes, content_type: str) -> Optional[ScrapedPage]:
        if not BS4_AVAILABLE:
            logger.warning(
                "beautifulsoup4 not installed. Install with: pip install beautifulsoup4"
            )
            return None

        try:
            # Detect encoding from content-type or let bs4 handle it
            soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")

            # Extract title
            title = self._extract_title(soup, url)

            # Remove noise elements
            for tag_name in self.REMOVE_TAGS:
                for tag in soup.find_all(tag_name):
                    tag.decompose()

            # Find main content area
            content_element = self._find_content(soup)

            # Convert to markdown
            markdown = self._html_to_markdown(content_element)

            if not markdown or len(markdown.strip()) < 50:
                logger.debug(f"Insufficient content from {url}")
                return None

            # Extract links for crawling
            links = self._extract_links(soup, url)

            word_count = len(markdown.split())

            return ScrapedPage(
                url=url,
                title=title,
                content=markdown,
                scraped_at=datetime.now().isoformat(),
                word_count=word_count,
                links=links,
                source_type="web",
            )

        except Exception as e:
            logger.error(f"Extraction failed for {url}: {e}")
            return None

    def _extract_title(self, soup, url: str) -> str:
        """Extract page title from various sources."""
        # Try og:title first (usually cleanest)
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try <title> tag
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            # Remove common suffixes like " | Site Name" or " - Site Name"
            title = re.split(r"\s*[\|\-–—]\s*", title)[0].strip()
            if title:
                return title

        # Try first h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Fallback to domain
        return urlparse(url).netloc

    def _find_content(self, soup):
        """Find the main content element."""
        # Try known content selectors
        for selector in self.CONTENT_SELECTORS:
            element = soup.select_one(selector)
            if element and len(element.get_text(strip=True)) > 100:
                return element

        # Fallback: find the div with most text content
        best = None
        best_length = 0
        for div in soup.find_all(["div", "section"]):
            text = div.get_text(strip=True)
            if len(text) > best_length:
                best_length = len(text)
                best = div

        return best or soup.body or soup

    def _html_to_markdown(self, element) -> str:
        """Convert an HTML element to clean markdown."""
        if element is None:
            return ""

        lines = []
        self._process_element(element, lines)

        # Clean up excessive blank lines
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _process_element(self, element, lines: list, depth: int = 0):
        """Recursively process HTML elements into markdown lines."""
        if hasattr(element, "name"):
            tag = element.name

            if tag in self.REMOVE_TAGS:
                return

            # Headings
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag[1])
                text = element.get_text(strip=True)
                if text:
                    lines.append("")
                    lines.append(f"{'#' * level} {text}")
                    lines.append("")
                return

            # Paragraphs
            if tag == "p":
                text = element.get_text(strip=True)
                if text:
                    lines.append("")
                    lines.append(text)
                return

            # Lists
            if tag in ("ul", "ol"):
                lines.append("")
                for i, li in enumerate(element.find_all("li", recursive=False)):
                    prefix = f"{i + 1}." if tag == "ol" else "-"
                    text = li.get_text(strip=True)
                    if text:
                        lines.append(f"{prefix} {text}")
                lines.append("")
                return

            # Code blocks
            if tag == "pre":
                code = element.find("code")
                text = (code or element).get_text()
                lang = ""
                if code and code.get("class"):
                    for cls in code["class"]:
                        if cls.startswith("language-"):
                            lang = cls[9:]
                            break
                lines.append("")
                lines.append(f"```{lang}")
                lines.append(text.rstrip())
                lines.append("```")
                lines.append("")
                return

            # Inline code
            if tag == "code" and element.parent and element.parent.name != "pre":
                text = element.get_text()
                if text:
                    lines.append(f"`{text}`")
                return

            # Blockquotes
            if tag == "blockquote":
                text = element.get_text(strip=True)
                if text:
                    lines.append("")
                    for line in text.split("\n"):
                        lines.append(f"> {line.strip()}")
                    lines.append("")
                return

            # Links
            if tag == "a":
                href = element.get("href", "")
                text = element.get_text(strip=True)
                if text and href and not href.startswith("#"):
                    lines.append(f"[{text}]({href})")
                elif text:
                    lines.append(text)
                return

            # Images
            if tag == "img":
                alt = element.get("alt", "")
                src = element.get("src", "")
                if src:
                    lines.append(f"![{alt}]({src})")
                return

            # Tables
            if tag == "table":
                self._process_table(element, lines)
                return

            # For other block elements, recurse into children
            if tag in ("div", "section", "article", "main", "span", "figure",
                        "figcaption", "details", "summary"):
                for child in element.children:
                    self._process_element(child, lines, depth + 1)
                return

        # NavigableString — raw text
        elif hasattr(element, "string") and element.string:
            text = element.string.strip()
            if text:
                lines.append(text)

    def _process_table(self, table, lines: list):
        """Convert an HTML table to markdown."""
        rows = table.find_all("tr")
        if not rows:
            return

        lines.append("")
        for i, row in enumerate(rows):
            cells = row.find_all(["th", "td"])
            cell_texts = [c.get_text(strip=True).replace("|", "\\|") for c in cells]
            lines.append("| " + " | ".join(cell_texts) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * len(cell_texts)) + " |")
        lines.append("")

    def _extract_links(self, soup, base_url: str) -> List[str]:
        """Extract outbound links from the page."""
        from urllib.parse import urljoin

        links = []
        seen = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith(("#", "javascript:", "mailto:")):
                continue
            full_url = urljoin(base_url, href)
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)

        return links


class PDFExtractor:
    """Extract text from PDF files using pymupdf (fitz).

    Uses font-size analysis to detect headings and document structure.
    Converts to clean markdown with proper heading hierarchy.
    """

    def can_handle(self, url: str, content_type: str) -> bool:
        return (
            "application/pdf" in content_type
            or url.lower().endswith(".pdf")
        )

    def extract(self, url: str, raw: bytes, content_type: str) -> Optional[ScrapedPage]:
        if not PYMUPDF_AVAILABLE:
            logger.warning(
                "pymupdf not installed. Install with: pip install pymupdf"
            )
            return None

        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            metadata = doc.metadata or {}
            title = metadata.get("title", "").strip()
            page_count = len(doc)

            markdown, stats = self._extract_structured(doc)
            doc.close()

            if not markdown:
                logger.debug(f"No text extracted from PDF: {url}")
                return None

            markdown = self._clean_pdf_text(markdown)

            if not title:
                first_line = markdown.split("\n")[0].strip()
                if first_line and len(first_line) < 200:
                    title = first_line.lstrip("# ").strip()
                else:
                    title = Path(urlparse(url).path).stem or "Untitled PDF"

            word_count = len(markdown.split())

            return ScrapedPage(
                url=url,
                title=title,
                content=markdown,
                scraped_at=datetime.now().isoformat(),
                word_count=word_count,
                links=[],
                source_type="pdf",
                raw_bytes=raw,
            )

        except Exception as e:
            logger.error(f"PDF extraction failed for {url}: {e}")
            return None

    def _extract_structured(self, doc) -> Tuple[str, Dict]:
        """Extract text with structure detection from font metadata.

        Two-pass approach:
        1. Build font-size histogram to identify body vs heading sizes
        2. Extract text, converting larger fonts to markdown headings
        """
        # Phase 1: font-size histogram
        size_counter: Counter = Counter()
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            size_counter[round(span["size"], 1)] += len(text)

        if not size_counter:
            return "", {}

        body_size = size_counter.most_common(1)[0][0]

        # Heading sizes: anything > body_size * 1.15, ranked largest first
        heading_sizes = sorted(
            [sz for sz in size_counter if sz > body_size * 1.15],
            reverse=True,
        )
        heading_map: Dict[float, int] = {}
        for i, sz in enumerate(heading_sizes[:3]):
            heading_map[sz] = i + 1  # 1=H2, 2=H3, 3=H4 (offset +1 in output)

        # Phase 2: extract with structure
        pages_md = []
        for page in doc:
            lines_out: List[str] = []
            prev_was_heading = False

            for block in page.get_text("dict")["blocks"]:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    line_text = ""
                    line_size = None
                    is_bold = False

                    for span in line["spans"]:
                        line_text += span["text"]
                        if span["text"].strip():
                            line_size = round(span["size"], 1)
                            is_bold = bool(span["flags"] & 16)

                    line_text = line_text.rstrip()
                    stripped = line_text.strip()
                    if not stripped:
                        continue

                    # Heading by font size
                    if line_size in heading_map:
                        level = heading_map[line_size] + 1  # +1 so title=##, sections=###
                        lines_out.append("")
                        lines_out.append(f"{'#' * level} {stripped}")
                        lines_out.append("")
                        prev_was_heading = True
                        continue

                    # Bold subheading (same body size but bold, short, starts a block)
                    if is_bold and line_size == body_size and len(stripped) < 100:
                        # Only treat as subheading if it looks like a title (not mid-paragraph bold)
                        if prev_was_heading or not lines_out or not lines_out[-1].strip():
                            lines_out.append("")
                            lines_out.append(f"### {stripped}")
                            lines_out.append("")
                            prev_was_heading = True
                            continue

                    lines_out.append(line_text)
                    prev_was_heading = False

            page_text = "\n".join(lines_out)
            if page_text.strip():
                pages_md.append(page_text)

        stats = {"body_size": body_size, "heading_sizes": heading_sizes}
        return "\n\n***\n\n".join(pages_md), stats

    def _clean_pdf_text(self, text: str) -> str:
        """Clean up extracted PDF text.

        Handles: paragraph reconstruction, dehyphenation, ALL-CAPS section
        detection, page numbers, excessive whitespace.
        """
        # Dehyphenation: fix word-break hyphens at line ends
        text = re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)

        # Reconstruct paragraphs from line-per-block PDF output
        text = self._join_paragraphs(text)

        lines = text.split("\n")
        cleaned = []
        for line in lines:
            line = line.rstrip()
            line = re.sub(r" {2,}", " ", line)  # Collapse multiple spaces
            stripped = line.strip()

            # ALL-CAPS section detection (academic papers)
            # Must be standalone line, 5-80 chars, actual words, not already a heading
            if (
                stripped
                and not stripped.startswith("#")
                and 5 <= len(stripped) <= 80
                and re.match(r"^[A-Z][A-Z\s,&:;\'\-]{3,}$", stripped)
                and sum(1 for c in stripped if c.isalpha()) > len(stripped) * 0.5
            ):
                cleaned.append("")
                cleaned.append(f"## {stripped}")
                cleaned.append("")
                continue

            cleaned.append(line)

        text = "\n".join(cleaned)

        # Remove standalone page numbers
        text = re.sub(r"\n\s*\d{1,4}\s*\n", "\n", text)

        # Collapse excessive blank lines
        text = re.sub(r"\n{4,}", "\n\n***\n\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    @staticmethod
    def _join_paragraphs(text: str) -> str:
        """Reconstruct paragraphs from line-per-block PDF output.

        PDF extraction produces one line per text block. Consecutive body text
        lines that belong to the same paragraph are joined with spaces.
        Paragraph breaks are inserted at sentence boundaries when the
        accumulated paragraph is long enough to be a complete thought.
        """
        lines = text.split("\n")
        result: List[str] = []
        current_para: List[str] = []
        current_len = 0

        def _flush_para():
            nonlocal current_len
            if current_para:
                result.append(" ".join(current_para))
                result.append("")  # blank line = paragraph break
                current_para.clear()
                current_len = 0

        for line in lines:
            stripped = line.strip()

            # Empty line — flush current paragraph
            if not stripped:
                _flush_para()
                continue

            # Headings, separators — always their own block with surrounding breaks
            if stripped.startswith("#") or stripped == "***":
                _flush_para()
                result.append(line)
                result.append("")
                continue

            # If current paragraph is empty, start a new one
            if not current_para:
                current_para.append(stripped)
                current_len = len(stripped)
                continue

            # Decide: join to current paragraph or start new one?
            # Look at the accumulated paragraph so far
            joined_so_far = " ".join(current_para)
            last_char = joined_so_far.rstrip()[-1] if joined_so_far.rstrip() else ""

            # Sentence-end detection: flush paragraph when ALL conditions met:
            # 1. Current para ends with sentence-ending punctuation
            # 2. Next line starts with uppercase (new sentence)
            # 3. Current para is at least 80 chars (not just a short fragment)
            is_sentence_end = last_char in '.!?"\')\u201d'
            starts_new = stripped[0].isupper() or stripped[0] in "\"\u2018\u201c(-\u2022\u2013\u2014"
            long_enough = current_len > 80

            if is_sentence_end and starts_new and long_enough:
                _flush_para()
                current_para.append(stripped)
                current_len = len(stripped)
                continue

            # Otherwise: continuation — join to current paragraph
            current_para.append(stripped)
            current_len += len(stripped) + 1

        _flush_para()
        return "\n".join(result)


class ArxivExtractor:
    """Extract content from arXiv pages.

    Handles:
    - Abstract pages (arxiv.org/abs/...) — extracts title, authors, abstract, metadata
    - PDF links (arxiv.org/pdf/...) — delegates to PDFExtractor
    """

    _pdf_extractor = PDFExtractor()

    def can_handle(self, url: str, content_type: str) -> bool:
        return "arxiv.org" in urlparse(url).netloc

    def extract(self, url: str, raw: bytes, content_type: str) -> Optional[ScrapedPage]:
        # PDF on arXiv — delegate
        if self._pdf_extractor.can_handle(url, content_type):
            page = self._pdf_extractor.extract(url, raw, content_type)
            if page:
                page.source_type = "arxiv"
            return page

        if not BS4_AVAILABLE:
            return None

        try:
            soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")

            # Title
            title_el = soup.select_one("h1.title")
            title = title_el.get_text(strip=True).replace("Title:", "").strip() if title_el else ""

            # Authors
            authors_el = soup.select_one(".authors")
            authors = authors_el.get_text(strip=True).replace("Authors:", "").strip() if authors_el else ""

            # Abstract
            abstract_el = soup.select_one("blockquote.abstract")
            abstract = abstract_el.get_text(strip=True).replace("Abstract:", "").strip() if abstract_el else ""

            # Subjects/categories
            subjects_el = soup.select_one(".subjects")
            subjects = subjects_el.get_text(strip=True) if subjects_el else ""

            # Submission date
            date_el = soup.select_one(".dateline")
            dateline = date_el.get_text(strip=True) if date_el else ""

            # Build markdown
            parts = [f"**Authors:** {authors}"] if authors else []
            if dateline:
                parts.append(f"**Submitted:** {dateline}")
            if subjects:
                parts.append(f"**Subjects:** {subjects}")
            parts.append("")
            parts.append("## Abstract")
            parts.append("")
            parts.append(abstract)

            # Get PDF link
            pdf_link = soup.select_one('a[href*="/pdf/"]')
            if pdf_link:
                pdf_url = pdf_link.get("href", "")
                if pdf_url.startswith("/"):
                    pdf_url = f"https://arxiv.org{pdf_url}"
                parts.append("")
                parts.append(f"**PDF:** [{pdf_url}]({pdf_url})")

            content = "\n".join(parts)
            word_count = len(content.split())

            if not title and not abstract:
                return None

            return ScrapedPage(
                url=url,
                title=title or "Untitled arXiv Paper",
                content=content,
                scraped_at=datetime.now().isoformat(),
                word_count=word_count,
                links=[],
                source_type="arxiv",
            )

        except Exception as e:
            logger.error(f"arXiv extraction failed for {url}: {e}")
            return None


class GitHubExtractor:
    """Extract content from GitHub pages.

    Handles:
    - Repository pages (github.com/user/repo) — extracts README
    - File views — extracts code content
    - Focuses on the actual content, stripping GitHub chrome
    """

    def can_handle(self, url: str, content_type: str) -> bool:
        return "github.com" in urlparse(url).netloc and "text/html" in content_type

    def extract(self, url: str, raw: bytes, content_type: str) -> Optional[ScrapedPage]:
        if not BS4_AVAILABLE:
            return None

        try:
            soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")

            parsed_url = urlparse(url)
            path_parts = [p for p in parsed_url.path.split("/") if p]

            # Repository main page — extract README
            readme_el = soup.select_one("article.markdown-body")
            if readme_el:
                title = self._extract_repo_title(soup, path_parts)
                content = self._readme_to_markdown(readme_el)

                # Extract repo metadata
                description_el = soup.select_one("p.f4.my-3")
                description = description_el.get_text(strip=True) if description_el else ""

                # Topics/tags
                topics = [t.get_text(strip=True) for t in soup.select("a.topic-tag")]

                parts = []
                if description:
                    parts.append(f"*{description}*\n")
                if topics:
                    parts.append(f"**Topics:** {', '.join(topics)}\n")
                parts.append(content)

                full_content = "\n".join(parts)
                word_count = len(full_content.split())

                return ScrapedPage(
                    url=url,
                    title=title,
                    content=full_content,
                    scraped_at=datetime.now().isoformat(),
                    word_count=word_count,
                    links=self._extract_links(soup, url),
                    source_type="github",
                )

            # Code file view
            code_el = soup.select_one("table.highlight")
            if code_el:
                title = path_parts[-1] if path_parts else "GitHub File"
                code_text = code_el.get_text()
                repo_name = "/".join(path_parts[:2]) if len(path_parts) >= 2 else ""

                content = f"**Repository:** {repo_name}\n\n```\n{code_text}\n```"
                word_count = len(content.split())

                return ScrapedPage(
                    url=url,
                    title=f"{repo_name}/{title}",
                    content=content,
                    scraped_at=datetime.now().isoformat(),
                    word_count=word_count,
                    links=[],
                    source_type="github",
                )

            # Fallback to generic extraction for other GitHub pages
            return None

        except Exception as e:
            logger.error(f"GitHub extraction failed for {url}: {e}")
            return None

    def _extract_repo_title(self, soup, path_parts: list) -> str:
        """Extract repository name from GitHub page."""
        if len(path_parts) >= 2:
            return f"{path_parts[0]}/{path_parts[1]}"
        title_el = soup.select_one("strong[itemprop='name'] a")
        if title_el:
            return title_el.get_text(strip=True)
        return "GitHub Repository"

    def _readme_to_markdown(self, article) -> str:
        """Convert GitHub's rendered README back to clean markdown."""
        # GitHub's markdown-body is already rendered HTML — use generic conversion
        extractor = GenericExtractor()
        return extractor._html_to_markdown(article)

    def _extract_links(self, soup, base_url: str) -> List[str]:
        """Extract relevant links from GitHub page."""
        from urllib.parse import urljoin
        links = []
        for a in soup.select("article.markdown-body a[href]"):
            href = a["href"]
            if href.startswith(("#", "javascript:")):
                continue
            links.append(urljoin(base_url, href))
        return links


# Registry of all extractors, ordered by specificity (most specific first)
_EXTRACTORS: List[ContentExtractor] = [
    ArxivExtractor(),
    GitHubExtractor(),
    PDFExtractor(),
    GenericExtractor(),
]


def get_extractor(url: str, content_type: str) -> Optional[ContentExtractor]:
    """Find the best extractor for a given URL and content type."""
    for extractor in _EXTRACTORS:
        if extractor.can_handle(url, content_type):
            return extractor
    return None


def extract_content(url: str, raw: bytes, content_type: str) -> Optional[ScrapedPage]:
    """Extract content from raw bytes using the appropriate extractor."""
    extractor = get_extractor(url, content_type)
    if extractor is None:
        logger.warning(f"No extractor available for {content_type} from {url}")
        return None
    return extractor.extract(url, raw, content_type)
