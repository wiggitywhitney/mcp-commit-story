import sys
import json
import click
from pathlib import Path
from mcp_commit_story.journal_init import initialize_journal

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

@click.command()
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

if __name__ == "__main__":
    journal_init()
