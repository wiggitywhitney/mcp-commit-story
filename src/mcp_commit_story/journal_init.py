from pathlib import Path
import os
import yaml
import time
import shutil
from .config import DEFAULT_CONFIG
import copy
from .git_utils import is_git_repo, get_repo

def create_journal_directories(base_path: Path):
    """
    Create the journal directory structure at the given base path.
    - Creates daily/ and summaries/{daily,weekly,monthly,yearly} subdirectories.
    - Raises appropriate exceptions on error.
    """
    if base_path.exists() and not base_path.is_dir():
        raise NotADirectoryError(f"{base_path} exists and is not a directory")
    try:
        base_path.mkdir(parents=True, exist_ok=True)
        (base_path / "daily").mkdir(parents=True, exist_ok=True)
        summaries = base_path / "summaries"
        summaries.mkdir(parents=True, exist_ok=True)
        for sub in ["daily", "weekly", "monthly", "yearly"]:
            (summaries / sub).mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise PermissionError(f"Permission denied while creating journal directories: {e}")
    except Exception as e:
        raise OSError(f"Failed to create journal directories: {e}")

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