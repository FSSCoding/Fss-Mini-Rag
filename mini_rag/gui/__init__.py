"""FSS-Mini-RAG Desktop GUI package."""


def main():
    """Launch the FSS-Mini-RAG desktop application."""
    from .app import MiniRAGApp
    app = MiniRAGApp()
    app.mainloop()
