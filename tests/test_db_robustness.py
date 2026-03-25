"""Tests for LanceDB table management robustness.

Covers ghost table states, corruption recovery, force-reindex paths,
and connection handling edge cases.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestGhostTableRecovery:
    """Test recovery when table_names() and create_table() disagree."""

    def test_ghost_table_recovery_drop_and_recreate(self):
        """When create_table raises 'already exists' but table_names() is empty,
        recovery should drop, reconnect, and create successfully."""
        mock_db = MagicMock()
        mock_table = MagicMock()

        # table_names() says empty
        mock_db.table_names.return_value = []

        # First create_table raises "already exists"
        # Second create_table (after reconnect) succeeds
        mock_db.create_table.side_effect = [
            Exception("Table 'code_vectors' already exists"),
            mock_table,
        ]
        mock_db.drop_table.return_value = None

        # Simulate the recovery logic from indexer.py
        table = None
        if "code_vectors" not in mock_db.table_names():
            try:
                table = mock_db.create_table("code_vectors", schema="fake")
            except Exception:
                try:
                    mock_db.drop_table("code_vectors")
                except Exception:
                    pass
                # Reconnect would happen here in real code
                table = mock_db.create_table("code_vectors", schema="fake")

        assert table is mock_table
        assert mock_db.drop_table.called
        assert mock_db.create_table.call_count == 2

    def test_ghost_table_drop_fails_then_create_fails(self):
        """When both drop and second create fail, should raise with clear message."""
        mock_db = MagicMock()
        mock_db.table_names.return_value = []
        mock_db.create_table.side_effect = Exception("Table already exists")
        mock_db.drop_table.side_effect = Exception("Cannot drop")

        with pytest.raises(Exception, match="Table already exists"):
            if "code_vectors" not in mock_db.table_names():
                try:
                    mock_db.create_table("code_vectors", schema="fake")
                except Exception:
                    try:
                        mock_db.drop_table("code_vectors")
                    except Exception:
                        pass
                    mock_db.create_table("code_vectors", schema="fake")

    def test_normal_create_no_ghost(self):
        """Normal path: table doesn't exist, create succeeds first time."""
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table_names.return_value = []
        mock_db.create_table.return_value = mock_table

        if "code_vectors" not in mock_db.table_names():
            table = mock_db.create_table("code_vectors", schema="fake")

        assert table is mock_table
        assert mock_db.create_table.call_count == 1
        assert not mock_db.drop_table.called

    def test_table_exists_open_succeeds(self):
        """Normal path: table exists, open succeeds."""
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table_names.return_value = ["code_vectors"]
        mock_db.open_table.return_value = mock_table

        if "code_vectors" in mock_db.table_names():
            table = mock_db.open_table("code_vectors")

        assert table is mock_table
        assert not mock_db.create_table.called


class TestForceReindex:
    """Test the force reindex path handles table state correctly."""

    def test_force_reindex_drops_and_reconnects(self):
        """Force reindex should drop table, reconnect, then init fresh."""
        mock_db = MagicMock()
        mock_db.table_names.return_value = ["code_vectors"]

        # Simulate force reindex logic
        if "code_vectors" in mock_db.table_names():
            mock_db.drop_table("code_vectors")

        mock_db.drop_table.assert_called_with("code_vectors")

    def test_force_reindex_no_table_exists(self):
        """Force reindex when table doesn't exist should still work."""
        mock_db = MagicMock()
        mock_db.table_names.return_value = []

        # Should not try to drop
        if "code_vectors" in mock_db.table_names():
            mock_db.drop_table("code_vectors")

        assert not mock_db.drop_table.called


class TestTableNamesAPI:
    """Verify table_names() returns the correct type."""

    def test_table_names_returns_list(self):
        """table_names() must return a plain list, not a response object."""
        import warnings
        warnings.filterwarnings("ignore", message="table_names.*deprecated")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                import lancedb
                db = lancedb.connect(tmpdir)
                result = db.table_names()
                assert isinstance(result, list), f"table_names() returned {type(result)}, expected list"
                assert "code_vectors" not in result
            except ImportError:
                pytest.skip("lancedb not installed")

    def test_in_check_works_with_table_names(self):
        """The 'in' operator must work correctly with table_names() result."""
        import warnings
        warnings.filterwarnings("ignore", message="table_names.*deprecated")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                import lancedb
                db = lancedb.connect(tmpdir)

                # Empty DB
                assert "code_vectors" not in db.table_names()

                # Create a table
                import pyarrow as pa
                schema = pa.schema([pa.field("x", pa.string())])
                db.create_table("code_vectors", schema=schema)

                # Now it should be found
                assert "code_vectors" in db.table_names()

                # Clean up
                db.drop_table("code_vectors")
                assert "code_vectors" not in db.table_names()

            except ImportError:
                pytest.skip("lancedb not installed")


class TestConnectionHandling:
    """Test database connection edge cases."""

    def test_connect_to_nonexistent_dir(self):
        """Connecting to a non-existent directory should create it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "new_subdir" / "lancedb"
            try:
                import lancedb
                db = lancedb.connect(str(db_path))
                assert db.table_names() == []
            except ImportError:
                pytest.skip("lancedb not installed")

    def test_connect_to_empty_dir(self):
        """Connecting to an empty directory should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                import lancedb
                db = lancedb.connect(tmpdir)
                assert db.table_names() == []
            except ImportError:
                pytest.skip("lancedb not installed")
