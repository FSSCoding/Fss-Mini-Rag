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
    """Compact semi-transparent overlay with spinner and rotating messages.

    Sits in the center of the parent widget — the GUI is still visible
    behind and around the overlay panel.
    """

    def __init__(self, parent):
        # Use Canvas as base for rounded-corner look
        super().__init__(parent, bg="#252535", highlightthickness=0,
                         bd=0, padx=0, pady=0)
        self._message_idx = 0
        self._spin_idx = 0
        self._spin_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self._operation = "searching"
        self._after_id = None
        self._messages = []
        self._msg_after_id = None

        bg = "#252535"

        # Outer canvas for rounded border effect
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0,
                                 width=380, height=130)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Draw rounded rectangle
        self._draw_rounded_rect(self._canvas, 2, 2, 378, 128, radius=16,
                                fill="#1e1e2e", outline="#4a4a6a", width=1)

        # Overlay widgets on the canvas
        self.spinner_label = tk.Label(
            self._canvas, text="⠋", font=("", 24), fg="#4a9eff", bg="#1e1e2e",
        )
        self._canvas.create_window(190, 35, window=self.spinner_label)

        self.message_label = tk.Label(
            self._canvas, text="", font=("", 10), fg="#a0a0a0", bg="#1e1e2e",
            wraplength=320,
        )
        self._canvas.create_window(190, 72, window=self.message_label)

        self.detail_label = tk.Label(
            self._canvas, text="", font=("", 9), fg="#666666", bg="#1e1e2e",
        )
        self._canvas.create_window(190, 100, window=self.detail_label)

    @staticmethod
    def _draw_rounded_rect(canvas, x1, y1, x2, y2, radius=15, **kwargs):
        """Draw a rounded rectangle on a canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1, x2, y1 + radius,
            x2, y2 - radius,
            x2, y2, x2 - radius, y2,
            x1 + radius, y2,
            x1, y2, x1, y2 - radius,
            x1, y1 + radius,
            x1, y1, x1 + radius, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def show(self, operation: str = "searching", detail: str = ""):
        """Show the overlay centered in the parent widget."""
        self._operation = operation
        self._messages = list(MESSAGES.get(operation, MESSAGES["searching"]))
        random.shuffle(self._messages)
        self._message_idx = 0
        self._spin_idx = 0

        self.detail_label.config(text=detail)
        self._update_message()
        self.place(relx=0.5, rely=0.4, anchor="center")
        self.lift()
        self._animate()

    def hide(self):
        """Hide the overlay."""
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if self._msg_after_id:
            self.after_cancel(self._msg_after_id)
            self._msg_after_id = None
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
        self._msg_after_id = self.after(3000, self._update_message)
