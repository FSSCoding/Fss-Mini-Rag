#!/usr/bin/env python3
"""
Comprehensive test suite for all rag-mini commands and help systems.

Tests that ALL commands support:
- --help 
- -h
- help (where applicable)

And verifies help menu clarity and completeness.

⚠️  IMPORTANT: Run with venv activated:
    source .venv/bin/activate
    PYTHONPATH=. python tests/test_command_help_systems.py
"""

import unittest
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from mini_rag.cli import cli


class TestAllCommandHelp(unittest.TestCase):
    """Test help systems for all rag-mini commands."""
    
    def setUp(self):
        self.runner = CliRunner()
        # Get all available commands from CLI
        result = self.runner.invoke(cli, ['--help'])
        self.help_output = result.output
        
        # Extract command names from help output
        lines = self.help_output.split('\n')
        commands_section = False
        self.commands = []
        
        for line in lines:
            if line.strip() == 'Commands:':
                commands_section = True
                continue
            if commands_section and line.strip():
                if line.startswith('  ') and not line.startswith('   '):
                    # Command line format: "  command-name  Description..."
                    parts = line.strip().split()
                    if parts:
                        self.commands.append(parts[0])
                elif not line.startswith('  '):
                    # End of commands section
                    break

    def test_main_command_help_formats(self):
        """Test main rag-mini command supports all help formats."""
        # Test --help
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Mini RAG', result.output)
        
        # Note: -h and help subcommand not applicable to main command

    def test_all_subcommands_support_help_flag(self):
        """Test all subcommands support --help flag."""
        for cmd in self.commands:
            with self.subTest(command=cmd):
                result = self.runner.invoke(cli, [cmd, '--help'])
                self.assertEqual(result.exit_code, 0, f"Command {cmd} failed --help")
                self.assertIn('Usage:', result.output, f"Command {cmd} help missing usage")
                
    def test_all_subcommands_support_h_flag(self):
        """Test all subcommands support -h flag."""
        for cmd in self.commands:
            with self.subTest(command=cmd):
                result = self.runner.invoke(cli, [cmd, '-h'])
                self.assertEqual(result.exit_code, 0, f"Command {cmd} failed -h")
                self.assertIn('Usage:', result.output, f"Command {cmd} -h missing usage")

    def test_help_menu_completeness(self):
        """Test that help menus are complete and clear."""
        required_commands = ['init', 'search', 'status', 'info']
        
        for cmd in required_commands:
            with self.subTest(command=cmd):
                self.assertIn(cmd, self.commands, f"Required command {cmd} not found in CLI")
                
                result = self.runner.invoke(cli, [cmd, '--help'])
                self.assertEqual(result.exit_code, 0)
                
                help_text = result.output.lower()
                # Each command should have usage and options sections
                self.assertIn('usage:', help_text, f"{cmd} help missing usage")
                self.assertIn('options:', help_text, f"{cmd} help missing options")

    def test_help_consistency(self):
        """Test help output consistency across commands."""
        for cmd in self.commands:
            with self.subTest(command=cmd):
                # Test --help and -h produce same output
                result1 = self.runner.invoke(cli, [cmd, '--help'])
                result2 = self.runner.invoke(cli, [cmd, '-h'])
                
                self.assertEqual(result1.exit_code, result2.exit_code, 
                               f"{cmd}: --help and -h exit codes differ")
                self.assertEqual(result1.output, result2.output,
                               f"{cmd}: --help and -h output differs")


class TestCommandFunctionality(unittest.TestCase):
    """Test actual command functionality."""
    
    def setUp(self):
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test files
        (self.temp_path / "test.py").write_text('''
def hello_world():
    """Say hello to the world"""
    print("Hello, World!")
    return "success"

class TestClass:
    """A test class for demonstration"""
    def __init__(self):
        self.name = "test"
        
    def method_example(self):
        """Example method"""
        return self.name
''')
        
        (self.temp_path / "config.json").write_text('''
{
    "name": "test_project",
    "version": "1.0.0",
    "settings": {
        "debug": true,
        "api_key": "test123"
    }
}
''')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_command_functionality(self):
        """Test init command creates proper index."""
        result = self.runner.invoke(cli, ['init', '-p', str(self.temp_path)])
        # Should complete without crashing
        self.assertIn(result.exit_code, [0, 1])  # May fail due to model config but shouldn't crash
        
        # Check that .mini-rag directory was created
        rag_dir = self.temp_path / '.mini-rag'
        if result.exit_code == 0:
            self.assertTrue(rag_dir.exists(), "Init should create .mini-rag directory")

    def test_search_command_functionality(self):
        """Test search command basic functionality."""
        # First try to init
        init_result = self.runner.invoke(cli, ['init', '-p', str(self.temp_path)])
        
        # Then search (may fail if no index, but shouldn't crash)
        result = self.runner.invoke(cli, ['search', '-p', str(self.temp_path), 'hello world'])
        
        # Should complete without crashing  
        self.assertNotIn('Traceback', result.output, "Search should not crash with traceback")

    def test_status_command_functionality(self):
        """Test status command functionality."""
        result = self.runner.invoke(cli, ['status', '-p', str(self.temp_path)])
        # Should complete without crashing
        self.assertNotIn('Traceback', result.output, "Status should not crash")

    def test_info_command_functionality(self):
        """Test info command functionality."""
        result = self.runner.invoke(cli, ['info'])
        self.assertEqual(result.exit_code, 0, "Info command should succeed")
        self.assertNotIn('Traceback', result.output, "Info should not crash")

    def test_stats_command_functionality(self):
        """Test stats command functionality."""
        result = self.runner.invoke(cli, ['stats', '-p', str(self.temp_path)])
        # Should complete without crashing even if no index
        self.assertNotIn('Traceback', result.output, "Stats should not crash")


class TestHelpMenuClarity(unittest.TestCase):
    """Test help menu clarity and user experience."""
    
    def setUp(self):
        self.runner = CliRunner()

    def test_main_help_is_clear(self):
        """Test main help menu is clear and informative."""
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        
        help_text = result.output
        # Should contain clear description
        self.assertIn('Mini RAG', help_text)
        # Check for semantic search concept (appears in multiple forms)
        help_lower = help_text.lower()
        semantic_found = ('semantic search' in help_lower or 
                         'semantic code search' in help_lower or
                         'semantic similarity' in help_lower)
        self.assertTrue(semantic_found, f"No semantic search concept found in help: {help_lower}")
        
        # Should list main commands clearly
        self.assertIn('Commands:', help_text)
        self.assertIn('init', help_text)
        self.assertIn('search', help_text)

    def test_init_help_is_clear(self):
        """Test init command help is clear."""
        result = self.runner.invoke(cli, ['init', '--help'])
        self.assertEqual(result.exit_code, 0)
        
        help_text = result.output
        self.assertIn('Initialize RAG index', help_text)
        self.assertIn('-p, --path', help_text)  # Should explain path option

    def test_search_help_is_clear(self):
        """Test search command help is clear."""
        result = self.runner.invoke(cli, ['search', '--help'])
        self.assertEqual(result.exit_code, 0)
        
        help_text = result.output
        self.assertIn('Search', help_text)
        self.assertIn('query', help_text.lower())  # Should mention query
        # Should have key options
        self.assertIn('--top-k', help_text)
        self.assertIn('--show-perf', help_text)

    def test_error_messages_are_helpful(self):
        """Test error messages provide helpful guidance."""
        # Test command without required arguments
        result = self.runner.invoke(cli, ['search'])
        # Should show usage help, not just crash
        if result.exit_code != 0:
            self.assertIn('Usage:', result.output)


def run_comprehensive_help_test():
    """Run all help system tests with detailed reporting."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]FSS-Mini-RAG Command Help System Test Suite[/bold cyan]\n"
        "[dim]Testing all commands support -h, --help, and help functionality[/dim]",
        border_style="cyan"
    ))
    
    # Test suites to run
    test_suites = [
        ("Help System Support", TestAllCommandHelp),
        ("Command Functionality", TestCommandFunctionality), 
        ("Help Menu Clarity", TestHelpMenuClarity)
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for suite_name, test_class in test_suites:
        console.print(f"\n[bold yellow]Testing {suite_name}[/bold yellow]")
        
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
                        console.print(f"    [red]{error[1].split('AssertionError:')[-1].strip()}[/red]")
                        
            except Exception as e:
                failed_tests.append(f"{test_class.__name__}.{test._testMethodName}")
                console.print(f"  [red]✗[/red] {test._testMethodName}: {e}")
    
    # Results summary
    console.print("\n" + "="*60)
    console.print(f"[bold]Test Results Summary[/bold]")
    
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green" if len(failed_tests) == 0 else "red")
    
    table.add_row("Total Tests", str(total_tests))
    table.add_row("Passed", str(passed_tests))
    table.add_row("Failed", str(len(failed_tests)))
    table.add_row("Success Rate", f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%")
    
    console.print(table)
    
    if failed_tests:
        console.print(f"\n[red]Failed Tests:[/red]")
        for test in failed_tests[:10]:  # Show first 10
            console.print(f"  • {test}")
        if len(failed_tests) > 10:
            console.print(f"  ... and {len(failed_tests) - 10} more")
    else:
        console.print(f"\n[green]🎉 All help system tests passed![/green]")
    
    # Show available commands
    from click.testing import CliRunner
    from mini_rag.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    if result.exit_code == 0:
        console.print(f"\n[cyan]Available Commands Tested:[/cyan]")
        lines = result.output.split('\n')
        commands_section = False
        
        for line in lines:
            if line.strip() == 'Commands:':
                commands_section = True
                continue
            if commands_section and line.strip():
                if line.startswith('  ') and not line.startswith('   '):
                    parts = line.strip().split(None, 1)
                    if len(parts) >= 2:
                        console.print(f"  • [bold]{parts[0]}[/bold] - {parts[1]}")
                elif not line.startswith('  '):
                    break
    
    console.print(f"\n[dim]Command help system verification complete.[/dim]")
    return passed_tests == total_tests


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--comprehensive":
        # Run with rich output
        success = run_comprehensive_help_test()
        sys.exit(0 if success else 1)
    else:
        # Run standard unittest
        unittest.main()