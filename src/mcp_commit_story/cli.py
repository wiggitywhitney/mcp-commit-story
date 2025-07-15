import sys
import json
import click
from pathlib import Path
import datetime
import getpass
from mcp_commit_story.journal_generate import JournalEntry, append_to_journal_file, ensure_journal_directory
from mcp_commit_story.journal_init import initialize_journal
from mcp_commit_story.git_utils import install_post_commit_hook

ERROR_CODES = {
    "success": 0,
    "general": 1,
    "already_initialized": 2,
    "invalid_args": 3,
    "filesystem": 4,
}

def cli_output(result):
    if result["status"] == "success":
        output = {
            "status": "success",
            "result": {
                "paths": result.get("paths", {}),
                "message": result.get("message", "")
            }
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)
    else:
        # Map error message to code
        msg = result.get("message", "Unknown error")
        if "already initialized" in msg.lower():
            code = ERROR_CODES["already_initialized"]
        elif "not a git repo" in msg.lower() or "permission" in msg.lower():
            code = ERROR_CODES["general"]
        elif "argument" in msg.lower() or "usage" in msg.lower():
            code = ERROR_CODES["invalid_args"]
        elif "file" in msg.lower() or "directory" in msg.lower():
            code = ERROR_CODES["filesystem"]
        else:
            code = ERROR_CODES["general"]
        output = {
            "status": "error",
            "message": msg,
            "code": code,
            "details": result.get("details", "")
        }
        print(json.dumps(output, indent=2))
        sys.exit(code)

@click.group(name='mcp-commit-story-setup')
@click.version_option()
def cli():
    """MCP Commit Story - Setup Commands Only
    
    Initialize and configure your automated engineering journal.
    
    This CLI provides setup commands only. Operational functionality 
    is available via the MCP server for AI agents and integrated tools.
    
    Setup Commands:
    - journal-init: Initialize journal configuration and directory structure
    - install-hook: Install git post-commit hook for automated journal entries (supports --background mode)
    """
    pass

@cli.command('journal-init')
@click.option('--repo-path', type=click.Path(), default=None, help='Path to git repository (default: current directory)')
@click.option('--config-path', type=click.Path(), default=None, help='Path for config file (default: .mcp-commit-storyrc.yaml in repo root)')
@click.option('--journal-path', type=click.Path(), default=None, help='Path for journal directory (default: journal/ in repo root)')
def journal_init(repo_path, config_path, journal_path):
    """
    Initialize the MCP Journal system in a git repository.
    Returns JSON output matching the approved CLI contract.
    """
    try:
        result = initialize_journal(repo_path, config_path, journal_path)
        cli_output(result)
    except Exception as e:
        output = {
            "status": "error",
            "message": str(e),
            "code": ERROR_CODES["general"],
            "details": "Exception in CLI: {}".format(repr(e))
        }
        print(json.dumps(output, indent=2))
        sys.exit(ERROR_CODES["general"])

@cli.command('install-hook')
@click.option('--repo-path', type=click.Path(), default=None, help='Path to git repository (default: current directory)')
@click.option('--background', is_flag=True, default=False, help='Run journal generation in background to avoid blocking git commits')
@click.option('--timeout', type=int, default=30, help='Timeout in seconds for background worker (default: 30)')
def install_hook(repo_path, background, timeout):
    """
    Install or replace the git post-commit hook for MCP Journal system.
    
    With --background flag, journal generation runs in background to avoid blocking git commits.
    Returns JSON output matching the approved CLI contract.
    """
    try:
        success = install_post_commit_hook(repo_path, background=background, timeout=timeout)
    except FileNotFoundError as e:
        output = {
            "status": "error",
            "message": str(e),
            "code": ERROR_CODES["filesystem"],
        }
        print(json.dumps(output, indent=2))
        return ERROR_CODES["filesystem"]
    except PermissionError as e:
        output = {
            "status": "error",
            "message": str(e),
            "code": ERROR_CODES["general"],
        }
        print(json.dumps(output, indent=2))
        return ERROR_CODES["general"]
    except FileExistsError as e:
        output = {
            "status": "error",
            "message": str(e),
            "code": ERROR_CODES["already_initialized"],
        }
        print(json.dumps(output, indent=2))
        return ERROR_CODES["already_initialized"]
    except Exception as e:
        output = {
            "status": "error",
            "message": str(e),
            "code": ERROR_CODES["general"],
        }
        print(json.dumps(output, indent=2))
        return ERROR_CODES["general"]
    
    mode_description = "background" if background else "synchronous"
    result = {
        "status": "success",
        "result": {
            "message": f"Post-commit hook installed successfully ({mode_description} mode).",
            "background_mode": background,
            "timeout": timeout if background else None
        }
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    cli()

def main():
    """Main entry point for console scripts."""
    cli()
