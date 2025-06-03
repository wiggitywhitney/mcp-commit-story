"""
Test CLI setup commands and architecture compliance.

This test module verifies the MCP-first architecture where:
1. CLI provides focused setup commands (journal-init, install-hook)
2. Setup commands work correctly with proper help and error handling
3. Operational commands are handled by MCP server (not CLI)
4. Console script entry points are properly configured
"""

import pytest
import subprocess
import sys
from click.testing import CliRunner
from mcp_commit_story.cli import cli


class TestCLISetupCommands:
    """Test that CLI provides the correct setup commands and functionality."""

    def test_cli_only_has_setup_commands(self):
        """Test that CLI only exposes setup commands, no operational commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        # Should succeed
        assert result.exit_code == 0
        help_output = result.output
        
        # Should contain setup commands
        assert 'journal-init' in help_output
        assert 'install-hook' in help_output
        
        # Should NOT contain operational commands
        assert 'add-reflection' not in help_output
        assert 'new-entry' not in help_output
        assert 'summarize' not in help_output
        assert 'blogify' not in help_output
        assert 'backfill' not in help_output

    def test_cli_help_text_mentions_mcp_requirement(self):
        """Test that CLI help text clearly indicates MCP is needed for operations."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        help_output = result.output.lower()
        
        # Should mention MCP and setup-only nature
        assert 'setup commands only' in help_output
        assert 'mcp' in help_output
        assert 'operational functionality' in help_output
        assert 'ai agents' in help_output or 'integrated tools' in help_output

    def test_no_add_reflection_command_exists(self):
        """Test that add-reflection command does not exist in CLI."""
        runner = CliRunner()
        
        # This should fail because add-reflection should not exist
        result = runner.invoke(cli, ['add-reflection', '--help'])
        assert result.exit_code != 0
        
        # Should get a "no such command" type error
        error_output = result.output.lower()
        assert 'no such command' in error_output or 'usage:' in error_output

    def test_no_operational_commands_exist(self):
        """Test that none of the MCP operational commands exist in CLI."""
        runner = CliRunner()
        
        operational_commands = [
            'add-reflection',
            'new-entry', 
            'summarize',
            'blogify',
            'backfill'
        ]
        
        for cmd in operational_commands:
            result = runner.invoke(cli, [cmd, '--help'])
            # All should fail because they shouldn't exist
            assert result.exit_code != 0, f"Command '{cmd}' should not exist in CLI"

    def test_available_commands_are_exactly_setup_commands(self):
        """Test that the available commands are exactly the expected setup commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        help_output = result.output
        
        # Count actual commands mentioned in help
        commands_found = []
        if 'journal-init' in help_output:
            commands_found.append('journal-init')
        if 'install-hook' in help_output:
            commands_found.append('install-hook')
            
        # Should have exactly these two setup commands
        assert len(commands_found) == 2
        assert 'journal-init' in commands_found
        assert 'install-hook' in commands_found

    def test_console_script_entry_point_works(self):
        """Test that the console script entry point works correctly."""
        # Test that we can call the CLI via the console script entry point
        try:
            result = subprocess.run([
                sys.executable, '-c', 
                'from mcp_commit_story.cli import cli; cli(["--help"])'
            ], capture_output=True, text=True, timeout=10)
            
            # Should succeed and show help
            assert result.returncode == 0
            assert 'journal-init' in result.stdout
            assert 'install-hook' in result.stdout
            
        except subprocess.TimeoutExpired:
            pytest.fail("CLI entry point test timed out")
        except Exception as e:
            pytest.fail(f"CLI entry point test failed: {e}")

    def test_pyproject_toml_entry_point_configuration(self):
        """Test that pyproject.toml is configured correctly for setup-only CLI."""
        import toml
        from pathlib import Path
        
        # Load pyproject.toml
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, 'r') as f:
            pyproject_data = toml.load(f)
        
        # Check that only setup CLI entry point exists
        scripts = pyproject_data.get('project', {}).get('scripts', {})
        
        # Should have exactly one script entry point for setup
        assert len(scripts) == 1
        
        # Should be named appropriately for setup
        setup_entry_found = False
        for script_name, entry_point in scripts.items():
            if 'setup' in script_name.lower():
                setup_entry_found = True
                # Should point to CLI module
                assert 'mcp_commit_story.cli' in entry_point
                
        assert setup_entry_found, "Should have a setup-named console script"

    def test_cli_group_name_indicates_setup_only(self):
        """Test that the CLI group name clearly indicates setup-only purpose."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        help_output = result.output
        
        # The group name should indicate setup-only nature
        # This is defined in the @click.group(name='...') decorator
        assert 'mcp-commit-story-setup' in help_output or 'Setup Commands Only' in help_output

    def test_journal_init_command_exists_and_works(self):
        """Test that journal-init command exists and shows proper help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['journal-init', '--help'])
        
        assert result.exit_code == 0
        help_output = result.output.lower()
        
        # Should mention initialization and setup concepts
        assert 'initialize' in help_output or 'init' in help_output
        assert 'repository' in help_output or 'repo' in help_output

    def test_install_hook_command_exists_and_works(self):
        """Test that install-hook command exists and shows proper help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['install-hook', '--help'])
        
        assert result.exit_code == 0
        help_output = result.output.lower()
        
        # Should mention hook installation concepts
        assert 'hook' in help_output
        assert 'install' in help_output
        assert 'git' in help_output or 'repository' in help_output or 'repo' in help_output 