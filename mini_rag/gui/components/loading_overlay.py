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
        "Rummaging through your files...",
        "Searching harder than my last relationship...",
        "Turning every stone in the index...",
        "Looking for that needle in the haystack...",
        "Crunching vectors at light speed...",
        "Asking the embeddings nicely...",
        "Hold tight, the maths is mathing...",
        "Semantic wizardry in progress...",
        "Your query is important to us...",
        "Somewhere in here is the answer...",
    ],
    "indexing": [
        "Reading every file like it's the last book on earth...",
        "Chunking, embedding, storing... the holy trinity...",
        "Teaching the vectors about your code...",
        "Building a search brain from scratch...",
        "Processing files faster than you can read them...",
        "Turning code into searchable knowledge...",
        "Indexing like there's no tomorrow...",
        "Making your codebase actually findable...",
        "Converting chaos into order...",
        "Almost there... just 47 more dimensions to compute...",
    ],
    "streaming": [
        "The LLM is thinking really hard...",
        "Generating words one token at a time...",
        "Consulting the neural oracle...",
        "Synthesising an answer from the void...",
        "The model is doing its thing...",
        "Tokens incoming... brace yourself...",
        "Assembling intelligence from mathematics...",
        "The AI is writing your answer in real-time...",
        "Patience... genius takes a moment...",
        "Translating embeddings into English...",
    ],
    "scraping": [
        "Fetching pages from the wild internet...",
        "Scraping responsibly... robots.txt approved...",
        "Downloading the knowledge of the web...",
        "Grabbing content before it changes...",
        "The internet is large, give us a sec...",
        "Extracting signal from the noise...",
        "Collecting research materials...",
        "Reading the web so you don't have to...",
        "Converting web pages to searchable text...",
        "Building your research corpus...",
    ],
    "deep_research": [
        "Deep research mode: going full detective...",
        "Searching, scraping, analysing, repeat...",
        "Multi-round research in progress...",
        "The research engine is on a mission...",
        "Hunting for knowledge across the web...",
        "Round after round of pure discovery...",
        "Building a research corpus from scratch...",
        "This is the serious research mode...",
        "Going deeper than a Wikipedia rabbit hole...",
        "Automated research assistant at work...",
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
