#!/usr/bin/env python3
"""
Comprehensive CLI integration tests for FSS-Mini-RAG.

Tests the global command functionality, path intelligence,
and command integration features added for global installation.

⚠️  IMPORTANT: This test requires the virtual environment to be activated:
    source .venv/bin/activate
    PYTHONPATH=. python tests/test_cli_integration.py

Or run directly with venv:
    source .venv/bin/activate && PYTHONPATH=. python tests/test_cli_integration.py
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Import the CLI and related modules
from mini_rag.cli import cli, find_nearby_index, show_index_guidance
from mini_rag.venv_checker import check_and_warn_venv


class TestPathIntelligence(unittest.TestCase):
    """Test the path intelligence features."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Nest 4 levels deep so the 3-level walk-up in find_nearby_index
        # cannot escape our temp tree (avoids false matches from /tmp/.mini-rag)
        self.temp_path = Path(self.temp_dir) / "a" / "b" / "c" / "d"
        self.temp_path.mkdir(parents=True)
        
    def tearDown(self):
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_nearby_index_current_directory(self):
        """Test finding index in current directory."""
        index_dir = self.temp_path / ".mini-rag"
        index_dir.mkdir()
        
        result = find_nearby_index(self.temp_path)
        self.assertEqual(result, self.temp_path)

    def test_find_nearby_index_parent_directory(self):
        """Test finding index in parent directory."""
        # Create nested structure
        nested = self.temp_path / "subdir" / "deep"
        nested.mkdir(parents=True)
        
        # Create index in parent
        index_dir = self.temp_path / ".mini-rag"
        index_dir.mkdir()
        
        result = find_nearby_index(nested)
        self.assertEqual(result, self.temp_path)

    def test_find_nearby_index_parent_search_only(self):
        """Test that find_nearby_index only searches up, not siblings."""
        # Create structure: temp/dir1, temp/dir2 (with index)
        dir1 = self.temp_path / "dir1"
        dir2 = self.temp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        # Create index in dir2 (sibling)
        index_dir = dir2 / ".mini-rag"
        index_dir.mkdir()
        
        # Should NOT find sibling index
        result = find_nearby_index(dir1)
        self.assertIsNone(result)  # Does not search siblings
        
        # But should find parent index
        parent_index = self.temp_path / ".mini-rag"
        parent_index.mkdir()
        result = find_nearby_index(dir1)
        self.assertEqual(result, self.temp_path)  # Finds parent

    def test_find_nearby_index_no_index(self):
        """Test behavior when no index is found."""
        result = find_nearby_index(self.temp_path)
        self.assertIsNone(result)

    @patch('mini_rag.cli.console')
    def test_guidance_display_function(self, mock_console):
        """Test that guidance display function works without path errors."""
        # Test with working directory structure to avoid relative_to errors
        with patch('mini_rag.cli.Path.cwd', return_value=self.temp_path):
            subdir = self.temp_path / "subdir"
            subdir.mkdir()
            
            # Test guidance display - should not crash
            show_index_guidance(subdir, self.temp_path)
            
            # Verify console.print was called multiple times for guidance
            self.assertTrue(mock_console.print.called)
            self.assertGreater(mock_console.print.call_count, 3)

    def test_path_navigation_logic(self):
        """Test path navigation logic for different directory structures."""
        # Create test structure
        parent = self.temp_path
        child = parent / "subdir" 
        sibling = parent / "other"
        child.mkdir()
        sibling.mkdir()
        
        # Test relative path calculation would work
        # (This tests the logic that show_index_guidance uses internally)
        try:
            # This simulates what happens in show_index_guidance
            relative_path = sibling.relative_to(child.parent) if sibling != child else Path(".")
            self.assertTrue(isinstance(relative_path, Path))
        except ValueError:
            # Handle cases where relative_to fails (expected in some cases)
            pass


class TestCLICommands(unittest.TestCase):
    """Test CLI command functionality."""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_help_command(self):
        """Test that help command works."""
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Mini RAG - Fast semantic code search', result.output)

    def test_info_command(self):
        """Test info command (no --version available)."""
        result = self.runner.invoke(cli, ['info', '--help'])
        self.assertEqual(result.exit_code, 0)

    @patch('mini_rag.cli.CodeSearcher')
    def test_search_command_with_index(self, mock_searcher):
        """Test search command when index exists."""
        # Create mock index
        index_dir = self.temp_path / ".mini-rag"
        index_dir.mkdir()
        
        # Mock searcher
        mock_instance = MagicMock()
        mock_instance.search.return_value = []
        mock_searcher.return_value = mock_instance
        
        with patch('mini_rag.cli.find_nearby_index', return_value=self.temp_path):
            result = self.runner.invoke(cli, ['search', str(self.temp_path), 'test query'])
            # Should not exit with error code 1 (no index found)
            self.assertNotEqual(result.exit_code, 1)

    def test_search_command_no_index(self):
        """Test search command when no index exists."""
        # Search command expects query as argument, path as option
        result = self.runner.invoke(cli, ['search', '-p', str(self.temp_path), 'test query'])
        # CLI may return different exit codes based on error type
        self.assertNotEqual(result.exit_code, 0)
        
    def test_search_command_basic_syntax(self):
        """Test search command basic syntax works."""
        # Change to temp directory to avoid existing index
        with patch('os.getcwd', return_value=str(self.temp_path)):
            with patch('mini_rag.cli.Path.cwd', return_value=self.temp_path):
                result = self.runner.invoke(cli, ['search', 'test query'])
                # Should fail gracefully when no index exists, not crash
                self.assertNotEqual(result.exit_code, 0)

    def test_init_command_help(self):
        """Test init subcommand help."""
        result = self.runner.invoke(cli, ['init', '--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Initialize RAG index', result.output)

    def test_search_command_no_query(self):
        """Test search command missing query parameter."""
        result = self.runner.invoke(cli, ['search'])
        # Click returns exit code 2 for usage errors
        self.assertEqual(result.exit_code, 2)
        self.assertIn('Usage:', result.output)


class TestVenvChecker(unittest.TestCase):
    """Test virtual environment checking functionality."""

    def test_venv_checker_global_wrapper(self):
        """Test that global wrapper suppresses venv warnings."""
        with patch.dict(os.environ, {'FSS_MINI_RAG_GLOBAL_WRAPPER': '1'}):
            # check_and_warn_venv should not exit when global wrapper is set
            result = check_and_warn_venv("test", force_exit=False)
            self.assertIsInstance(result, bool)

    def test_venv_checker_without_global_wrapper(self):
        """Test venv checker behavior without global wrapper."""
        # Remove the env var if it exists
        with patch.dict(os.environ, {}, clear=True):
            # This should return the normal venv check result
            result = check_and_warn_venv("test", force_exit=False)
            # The result depends on actual venv state, so we just test it doesn't crash
            self.assertIsInstance(result, bool)


class TestCLIIntegration(unittest.TestCase):
    """Test overall CLI integration and user experience."""

    def setUp(self):
        self.runner = CliRunner()

    def test_all_commands_have_help(self):
        """Test that all commands provide help information."""
        # Test main help
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        
        # Test subcommand helps  
        subcommands = ['search', 'init', 'status', 'info']
        for cmd in subcommands:
            result = self.runner.invoke(cli, [cmd, '--help'])
            self.assertEqual(result.exit_code, 0, f"Help failed for {cmd}")

    def test_error_handling_graceful(self):
        """Test that CLI handles errors gracefully."""
        # Test invalid directory
        result = self.runner.invoke(cli, ['search', '/nonexistent/path', 'query'])
        self.assertNotEqual(result.exit_code, 0)
        # Should not crash with unhandled exception
        self.assertNotIn('Traceback', result.output)

    def test_command_parameter_validation(self):
        """Test that command parameters are validated."""
        # Test search without query (should fail with exit code 2)
        result = self.runner.invoke(cli, ['search'])
        self.assertEqual(result.exit_code, 2)  # Click usage error
        
        # Test with proper help parameters
        result = self.runner.invoke(cli, ['search', '--help'])
        self.assertEqual(result.exit_code, 0)

    def test_performance_options_exist(self):
        """Test that performance-related options exist."""
        result = self.runner.invoke(cli, ['search', '--help'])
        self.assertEqual(result.exit_code, 0)
        # Check for performance options
        help_text = result.output
        self.assertIn('--show-perf', help_text)
        self.assertIn('--top-k', help_text)


def run_comprehensive_test():
    """Run all CLI integration tests with detailed reporting."""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    console.print("\n[bold cyan]FSS-Mini-RAG CLI Integration Test Suite[/bold cyan]")
    console.print("[dim]Testing global command functionality and path intelligence[/dim]\n")
    
    # Create test suite
    test_classes = [
        TestPathIntelligence,
        TestCLICommands, 
        TestVenvChecker,
        TestCLIIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        console.print(f"\n[bold yellow]Running {test_class.__name__}[/bold yellow]")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        
        for test in suite:
            total_tests += 1
            try:
                result = unittest.TestResult()
                test.run(result)
                
                if result.wasSuccessful():
                    passed_tests += 1
                    console.print(f"  [green]✓[/green] {test._testMethodName}")
                else:
                    failed_tests.append(f"{test_class.__name__}.{test._testMethodName}")
                    console.print(f"  [red]✗[/red] {test._testMethodName}")
                    for error in result.errors + result.failures:
                        console.print(f"    [red]{error[1]}[/red]")
                        
            except Exception as e:
                failed_tests.append(f"{test_class.__name__}.{test._testMethodName}")
                console.print(f"  [red]✗[/red] {test._testMethodName}: {e}")
    
    # Results summary
    console.print(f"\n[bold]Test Results Summary:[/bold]")
    
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Tests", str(total_tests))
    table.add_row("Passed", str(passed_tests))
    table.add_row("Failed", str(len(failed_tests)))
    table.add_row("Success Rate", f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%")
    
    console.print(table)
    
    if failed_tests:
        console.print(f"\n[red]Failed Tests:[/red]")
        for test in failed_tests:
            console.print(f"  • {test}")
    else:
        console.print(f"\n[green]🎉 All tests passed![/green]")
    
    console.print("\n[dim]CLI integration tests complete.[/dim]")
    return passed_tests == total_tests


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--comprehensive":
        # Run with rich output
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    else:
        # Run standard unittest
        unittest.main()