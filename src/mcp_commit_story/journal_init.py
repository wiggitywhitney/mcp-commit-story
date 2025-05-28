import os
import yaml
import time
import shutil
import logging
from pathlib import Path
from .config import DEFAULT_CONFIG
import copy
from .git_utils import is_git_repo, get_repo

def generate_default_config(config_path, journal_path):
    """
    Generate a default configuration file at the given path, customizing the journal path.
    If a config file exists, back it up before writing a new one.
    """
    config_path = Path(config_path)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['journal']['path'] = str(journal_path)
    backup_suffix = f".bak{int(time.time() * 1000)}"
    try:
        if config_path.exists():
            backup_path = config_path.parent / (config_path.name + backup_suffix)
            shutil.copy2(config_path, backup_path)
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    except PermissionError:
        raise
    except Exception as e:
        raise OSError(f"Failed to generate default config: {e}")

def validate_git_repository(path):
    """
    Validate that the given path is a valid (non-bare) git repository with proper permissions.
    Logic:
    - If path doesn't exist → FileNotFoundError
    - If path exists but isn't readable → PermissionError
    - If path is readable but not a git repo → FileNotFoundError
    - If path is a bare repo → ValueError
    - Otherwise → success
    """
    path = str(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Cannot access git repository: {path}")
    # Only proceed if readable
    if not is_git_repo(path):
        raise FileNotFoundError(f"Not a git repository: {path}")
    repo = get_repo(path)
    if repo.bare:
        raise ValueError(f"Cannot initialize journal in bare repository: {path}")

def initialize_journal(repo_path=None, config_path=None, journal_path=None):
    """
    Initialize a journal in a git repository.
    Args:
        repo_path: Path to git repository (defaults to current directory)
        config_path: Path for config file (defaults to .mcp-commit-storyrc.yaml in repo root)
        journal_path: Path for journal directory (defaults to journal/ in repo root)
    Returns:
        dict: {"status": "success"/"error", "paths": {...}, "message": "..."}
    Rollback: No automatic rollback. Log what was created so user can manually clean up. Fail fast and report what succeeded.
    Note:
        Only the base journal directory is created during initialization. All subdirectories are created on-demand by file operations.
    Example:
        result = initialize_journal(repo_path="/path/to/repo")
        # Only /path/to/repo/journal/ is created; subdirectories are created as needed.
    """
    created = {}
    try:
        repo_path = Path(repo_path) if repo_path else Path.cwd()
        config_path = Path(config_path) if config_path else repo_path / ".mcp-commit-storyrc.yaml"
        journal_path = Path(journal_path) if journal_path else repo_path / "journal"

        # Validate git repo
        try:
            validate_git_repository(repo_path)
        except Exception as e:
            return {"status": "error", "paths": created, "message": f"Git repository validation failed: {e}"}

        config_exists = config_path.exists()
        journal_exists = journal_path.exists() and journal_path.is_dir()

        if config_exists and journal_exists:
            return {
                "status": "error",
                "paths": {"config": str(config_path), "journal": str(journal_path)},
                "message": "Journal already initialized (config and journal directory exist)"
            }

        # Create config if missing
        if not config_exists:
            try:
                generate_default_config(config_path, journal_path)
                created["config"] = str(config_path)
            except Exception as e:
                return {"status": "error", "paths": created, "message": f"Failed to create config: {e}"}
        else:
            created["config"] = str(config_path)

        # Create journal directory if missing
        if not journal_exists:
            try:
                journal_path.mkdir(parents=True, exist_ok=True)
                created["journal"] = str(journal_path)
            except Exception as e:
                return {"status": "error", "paths": created, "message": f"Failed to create journal directory: {e}"}
        else:
            created["journal"] = str(journal_path)

        return {
            "status": "success",
            "paths": {"config": str(config_path), "journal": str(journal_path)},
            "message": "Journal initialized successfully."
        }
    except Exception as e:
        logging.exception("Unexpected error during journal initialization")
        return {"status": "error", "paths": created, "message": f"Unexpected error: {e}"} 