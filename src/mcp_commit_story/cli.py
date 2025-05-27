import sys
import json
import click
from pathlib import Path
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

@click.group()
def cli():
    """MCP Commit Story CLI"""
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
def install_hook(repo_path):
    """
    Install or replace the git post-commit hook for MCP Journal system.
    Returns JSON output matching the approved CLI contract.
    """
    try:
        backup_path = install_post_commit_hook(repo_path)
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
    result = {
        "status": "success",
        "result": {
            "message": "Post-commit hook installed successfully.",
            "backup_path": backup_path
        }
    }
    print(json.dumps(result, indent=2))
    return 0

@cli.command('new-entry')
@click.option('--repo-path', type=click.Path(), default=None, help='Path to git repository (default: current directory)')
@click.option('--summary', type=str, required=True, help='Summary for the new journal entry')
def new_entry(repo_path, summary):
    """
    Create a new journal entry in the MCP Journal system.
    Returns JSON output matching the approved CLI contract.
    """
    import datetime
    import getpass
    from mcp_commit_story.journal import JournalEntry, append_to_journal_file

    try:
        # Determine repo path
        repo_path = Path(repo_path) if repo_path else Path.cwd()
        journal_dir = repo_path / "journal" / "daily"
        journal_dir.mkdir(parents=True, exist_ok=True)
        # Journal file for today
        today = datetime.date.today().strftime("%Y-%m-%d")
        journal_file = journal_dir / f"{today}-journal.md"
        # Create journal entry
        now = datetime.datetime.now().isoformat(timespec="seconds")
        commit_hash = "manual"  # Could be improved to get HEAD commit
        author = getpass.getuser()
        entry = JournalEntry(
            timestamp=now,
            commit_hash=commit_hash,
            summary=summary,
            technical_synopsis=None,
            accomplishments=None,
            frustrations=None,
            terminal_commands=None,
            discussion_notes=None,
            tone_mood=None,
            commit_metadata={"author": author, "date": now}
        )
        append_to_journal_file(entry.to_markdown(), journal_file)
        result = {
            "status": "success",
            "paths": {"journal_file": str(journal_file)},
            "message": f"Journal entry added to {journal_file}"
        }
        cli_output(result)
    except Exception as e:
        output = {
            "status": "error",
            "message": str(e),
            "code": ERROR_CODES["general"],
            "details": "Exception in new-entry CLI: {}".format(repr(e))
        }
        print(json.dumps(output, indent=2))
        sys.exit(ERROR_CODES["general"])

@cli.command('add-reflection')
@click.option('--repo-path', type=click.Path(), default=None, help='Path to git repository (default: current directory)')
@click.option('--reflection', type=str, required=True, help='Reflection text to add to today\'s journal entry')
def add_reflection(repo_path, reflection):
    """
    Add a reflection to today's journal entry in the MCP Journal system.
    Returns JSON output matching the approved CLI contract.
    """
    import datetime
    try:
        repo_path = Path(repo_path) if repo_path else Path.cwd()
        journal_dir = repo_path / "journal" / "daily"
        today = datetime.date.today().strftime("%Y-%m-%d")
        journal_file = journal_dir / f"{today}-journal.md"
        if not journal_file.exists():
            raise FileNotFoundError(f"Journal file {journal_file} does not exist. Please create an entry first.")
        # Append the reflection as a new section
        with open(journal_file, "a", encoding="utf-8") as f:
            f.write("\n#### Reflection\n\n" + reflection + "\n")
        result = {
            "status": "success",
            "paths": {"journal_file": str(journal_file)},
            "message": f"Reflection added to {journal_file}"
        }
        cli_output(result)
    except Exception as e:
        output = {
            "status": "error",
            "message": str(e),
            "code": ERROR_CODES["general"],
            "details": "Exception in add-reflection CLI: {}".format(repr(e))
        }
        print(json.dumps(output, indent=2))
        sys.exit(ERROR_CODES["general"])

if __name__ == "__main__":
    cli()
