"""Full-window loading overlay with spinner and entertaining messages.

Shows a centered spinner animation with rotating status messages
during long operations (search, indexing, LLM, web scraping).
"""

import random
import tkinter as tk
from tkinter import ttk


# Messages grouped by operation type
MESSAGES = {
    "searching": [
        "Querying vector index...",
        "Running semantic search...",
        "Matching embeddings against your query...",
        "Scanning indexed chunks...",
        "Computing similarity scores...",
        "Ranking results by relevance...",
        "Loading search results...",
        "Retrieving matching documents...",
    ],
    "indexing": [
        "Parsing source files...",
        "Generating embeddings for each chunk...",
        "Building vector search index...",
        "Processing file contents...",
        "Storing embeddings in database...",
        "Mapping document structure...",
        "Analysing code and content...",
        "Preparing searchable index...",
    ],
    "streaming": [
        "Generating response from LLM...",
        "Streaming tokens from model...",
        "Synthesising answer from search results...",
        "Model is processing your query...",
        "Building response token by token...",
        "LLM synthesis in progress...",
        "Composing answer from context...",
        "Generating structured response...",
    ],
    "scraping": [
        "Fetching web pages...",
        "Downloading page content...",
        "Extracting text from HTML...",
        "Processing web content...",
        "Converting pages to searchable format...",
        "Collecting source material...",
        "Running content extraction pipeline...",
        "Saving scraped content to session...",
    ],
    "deep_research": [
        "Running deep research cycle...",
        "Analyse → Search → Scrape → Repeat...",
        "Multi-round automated research...",
        "Evaluating corpus and identifying gaps...",
        "Generating targeted search queries...",
        "Expanding research corpus...",
        "Pruning low-quality sources...",
        "Building comprehensive research report...",
    ],
}


class LoadingOverlay(tk.Frame):
    """Semi-transparent overlay with spinner and rotating messages."""

    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a1a")
        self._message_idx = 0
        self._spin_idx = 0
        self._spin_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self._operation = "searching"
        self._after_id = None
        self._messages = []

        # Center content
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        container = tk.Frame(self, bg="#1a1a1a")
        container.grid(row=0, column=0)

        self.spinner_label = tk.Label(
            container, text="⠋", font=("", 32), fg="#4a9eff", bg="#1a1a1a",
        )
        self.spinner_label.pack(pady=(0, 10))

        self.message_label = tk.Label(
            container, text="", font=("", 11), fg="#888888", bg="#1a1a1a",
            wraplength=400,
        )
        self.message_label.pack()

        self.detail_label = tk.Label(
            container, text="", font=("", 9), fg="#555555", bg="#1a1a1a",
        )
        self.detail_label.pack(pady=(8, 0))

    def show(self, operation: str = "searching", detail: str = ""):
        """Show the overlay for a given operation type."""
        self._operation = operation
        self._messages = list(MESSAGES.get(operation, MESSAGES["searching"]))
        random.shuffle(self._messages)
        self._message_idx = 0
        self._spin_idx = 0

        self.detail_label.config(text=detail)
        self._update_message()
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self._animate()

    def hide(self):
        """Hide the overlay."""
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.place_forget()

    def set_detail(self, text: str):
        """Update the detail text (e.g., progress info)."""
        self.detail_label.config(text=text)

    def _animate(self):
        """Animate spinner and rotate messages."""
        self._spin_idx = (self._spin_idx + 1) % len(self._spin_chars)
        self.spinner_label.config(text=self._spin_chars[self._spin_idx])
        self._after_id = self.after(100, self._animate)

    def _update_message(self):
        """Show next message from the shuffled pool."""
        if self._messages:
            msg = self._messages[self._message_idx % len(self._messages)]
            self.message_label.config(text=msg)
            self._message_idx += 1
        # Rotate message every 3 seconds
        self.after(3000, self._update_message)
