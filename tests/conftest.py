"""Shared fixtures for FSS-Mini-RAG tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with sample files."""
    # Python file
    py_file = tmp_path / "auth.py"
    py_file.write_text('''"""Authentication module."""

import hashlib

class AuthManager:
    """Manages user authentication."""

    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.sessions = {}

    def login(self, username, password):
        """Authenticate a user and create session."""
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if self._validate(username, hashed):
            token = self._create_token(username)
            self.sessions[token] = username
            return token
        return None

    def _validate(self, username, password_hash):
        """Validate credentials against store."""
        return True  # Simplified for testing

    def _create_token(self, username):
        """Generate session token."""
        return hashlib.sha256(username.encode()).hexdigest()

    def logout(self, token):
        """End a user session."""
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False


def get_auth_manager():
    """Factory function for AuthManager."""
    return AuthManager("default-secret")
''')

    # Markdown file
    md_file = tmp_path / "README.md"
    md_file.write_text('''# Test Project

## Overview

This is a test project for validating RAG indexing and search.

## Authentication

The auth module handles user login, session management, and logout.
It uses SHA-256 hashing for password storage.

## API Endpoints

- POST /login - Authenticate user
- POST /logout - End session
- GET /status - Check auth status

## Configuration

Set SECRET_KEY environment variable before starting.
''')

    # Config file
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text('''server:
  port: 8080
  host: localhost

database:
  url: sqlite:///app.db
  pool_size: 5
''')

    return tmp_path


@pytest.fixture
def chunker():
    """Create a CodeChunker with default settings."""
    from mini_rag.chunker import CodeChunker
    return CodeChunker()
