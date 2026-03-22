"""
Content extractors for web scraping.

Converts raw HTML and PDF content into clean markdown.
Domain-specific extractors handle known sites (arXiv, GitHub),
with a generic fallback for everything else.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Protocol
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

    Converts PDF pages to clean markdown with basic structure detection.
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

            # Extract metadata
            metadata = doc.metadata or {}
            title = metadata.get("title", "").strip()

            # Extract text from all pages
            pages_text = []
            for page in doc:
                text = page.get_text("text")
                if text.strip():
                    pages_text.append(text)

            doc.close()

            if not pages_text:
                logger.debug(f"No text extracted from PDF: {url}")
                return None

            # Combine pages with separators
            full_text = "\n\n---\n\n".join(pages_text)

            # Clean up the text
            markdown = self._clean_pdf_text(full_text)

            if not title:
                # Try to get title from first line
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
            )

        except Exception as e:
            logger.error(f"PDF extraction failed for {url}: {e}")
            return None

    def _clean_pdf_text(self, text: str) -> str:
        """Clean up raw PDF text into readable markdown."""
        # Fix common PDF extraction artifacts
        # Remove excessive whitespace within lines (but keep paragraph breaks)
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            line = line.rstrip()
            # Collapse multiple spaces within a line
            line = re.sub(r" {2,}", " ", line)
            cleaned.append(line)

        text = "\n".join(cleaned)

        # Remove page numbers (common patterns)
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

        # Collapse excessive blank lines
        text = re.sub(r"\n{4,}", "\n\n---\n\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()


# Registry of all extractors, ordered by specificity (most specific first)
# Domain-specific extractors (arXiv, GitHub) will be prepended here later
_EXTRACTORS: List[ContentExtractor] = [
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
