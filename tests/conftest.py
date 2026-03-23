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

    # HTML file
    html_file = tmp_path / "page.html"
    html_file.write_text("""<html><body>
<h1>Architecture</h1>
<p>Main system overview with important details about the application architecture.
This section describes the core components and their interactions within the system.
The architecture follows a modular design pattern with clear separation of concerns.</p>
<table>
<tr><th>Component</th><th>Status</th><th>Description</th><th>Version</th></tr>
<tr><td>Router</td><td>Active</td><td>Handles all incoming requests and routes them to appropriate handlers</td><td>2.1</td></tr>
<tr><td>Cache</td><td>Warm</td><td>In-memory cache layer for frequently accessed data and query results</td><td>1.5</td></tr>
<tr><td>Database</td><td>Connected</td><td>PostgreSQL backend for persistent storage of application data</td><td>15.2</td></tr>
<tr><td>Auth</td><td>Active</td><td>Authentication and authorization middleware for all API endpoints</td><td>3.0</td></tr>
</table>
<h2>Code Example</h2>
<pre><code>def initialize_application():
    config = load_config_from_environment()
    database = connect_to_database(config.db_url)
    cache = initialize_cache(config.cache_size)
    router = create_router(database, cache)
    auth = setup_authentication(config.secret_key)
    return Application(router, auth, database, cache)</code></pre>
<script>alert('should be stripped')</script>
<style>.hidden { display: none; }</style>
<nav><a href="/">Home</a></nav>
</body></html>""")

    # Shell script
    sh_file = tmp_path / "build.sh"
    sh_file.write_text("""#!/bin/bash
set -e
VERSION="1.0"

build_project() {
    echo "Building version $VERSION"
    make clean
    make all
}

function run_tests {
    pytest tests/
    echo "Tests passed"
}

build_project
run_tests
""")

    return tmp_path


@pytest.fixture
def chunker():
    """Create a CodeChunker with default settings."""
    from mini_rag.chunker import CodeChunker
    return CodeChunker()
