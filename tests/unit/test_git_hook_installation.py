import pytest
from mcp_commit_story.git_utils import generate_hook_content

def test_basic_hook_content():
    """Should generate a valid post-commit hook with default command."""
    content = generate_hook_content()
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh"
    assert "mcp-commit-story new-entry" in content, "Default command should be present"
    assert ">/dev/null 2>&1" in content, "Should suppress output"
    assert content.strip().endswith("|| true"), "Should not block commit on error"

def test_custom_command():
    """Should allow custom command(s) in the hook."""
    custom = "echo 'hello world'"
    content = generate_hook_content(custom)
    assert custom in content, "Custom command should be present"
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh"
    assert content.strip().endswith("|| true"), "Should not block commit on error"

def test_proper_shebang():
    """Should use the correct shebang line (to be approved)."""
    content = generate_hook_content()
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh and on its own line"

def test_executable_format():
    """Should ensure the script is in executable format (line endings, permissions)."""
    content = generate_hook_content()
    # Check for Unix line endings only (no \r\n)
    assert "\r" not in content, "Script should use Unix (LF) line endings only" 