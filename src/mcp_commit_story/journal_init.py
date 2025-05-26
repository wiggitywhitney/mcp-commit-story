from pathlib import Path
import os

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