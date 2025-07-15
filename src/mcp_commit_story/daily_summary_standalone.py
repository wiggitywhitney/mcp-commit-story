"""DEPRECATED: Standalone daily summary generation module.

⚠️  DEPRECATION NOTICE ⚠️

This module has been consolidated into daily_summary.py as of task 73.3.
All functionality has been moved to the main daily_summary module.

For new code, import directly from daily_summary:
    from mcp_commit_story.daily_summary import generate_daily_summary_standalone

This module now provides delegation functions for backwards compatibility only.
It will be removed in a future version.

Legacy usage (deprecated but still works):
```python
from mcp_commit_story.daily_summary_standalone import generate_daily_summary_standalone

# This still works but delegates to daily_summary.py
summary = generate_daily_summary_standalone("2025-01-15")
```

New recommended usage:
```python
from mcp_commit_story.daily_summary import generate_daily_summary_standalone

# Use the consolidated module directly
summary = generate_daily_summary_standalone("2025-01-15")
```
"""

import warnings
from typing import Optional, Dict

def generate_daily_summary_standalone(date: Optional[str] = None, repo_path: Optional[str] = None, commit_metadata: Optional[Dict] = None):
    """DEPRECATED: Use mcp_commit_story.daily_summary.generate_daily_summary_standalone instead.
    
    This function delegates to the consolidated daily_summary module.
    """
    warnings.warn(
        "daily_summary_standalone module is deprecated. Use 'from mcp_commit_story.daily_summary import generate_daily_summary_standalone' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Delegate to the consolidated module
    from .daily_summary import generate_daily_summary_standalone as consolidated_function
    return consolidated_function(date, repo_path, commit_metadata)


# Legacy exports for backwards compatibility (all deprecated)
__all__ = ['generate_daily_summary_standalone'] 