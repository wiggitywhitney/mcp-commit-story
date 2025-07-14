# Git Diff Collection

The MCP Commit Story project includes intelligent git diff collection that automatically captures and processes code changes for enhanced journal entries. This system provides detailed insights into code modifications while maintaining performance through adaptive size management.

## Overview

The diff collection system extracts actual code changes from git commits and includes them in journal context. This enables the AI to generate more detailed and technically accurate journal entries by understanding the specific changes made to the codebase.

## Core Features

### Adaptive Size Limits

The system automatically adjusts file size limits based on the number of changed files:

- **≤5 files**: 10KB per file (optimized for detailed analysis)
- **6-20 files**: 2.5KB per file (balanced detail vs performance)  
- **>20 files**: 1KB per file, max 50 files (performance-first with sampling)

This prevents memory exhaustion on large commits while maximizing detail for typical development workflows.

### Intelligent File Filtering

Binary files and generated files are automatically excluded:

- **Binary files**: Images, executables, compiled code
- **Generated files**: `package-lock.json`, build artifacts, dependency files
- **Large files**: Files exceeding size limits are gracefully truncated

### Error Handling

The system provides robust error handling:

- Individual file errors don't break the entire collection
- Critical failures return structured error information
- Size limit violations are clearly indicated with truncation messages

## Usage Example

```python
from mcp_commit_story.git_utils import get_commit_file_diffs, get_repo, get_current_commit

# Get repository and current commit
repo = get_repo("/path/to/repository")
commit = get_current_commit(repo)

# Extract diffs with default limits
diffs = get_commit_file_diffs(repo, commit)

# Process results
for file_path, diff_content in diffs.items():
    if file_path == "__truncated__":
        print("Some diffs were omitted due to size limits")
    elif file_path == "__error__":
        print(f"Error occurred: {diff_content}")
    else:
        print(f"{file_path}: {len(diff_content)} bytes of diff")

# Custom size limits for large repositories
large_repo_diffs = get_commit_file_diffs(
    repo, commit, 
    max_file_size=5*1024,  # 5KB per file
    max_total_size=25*1024  # 25KB total
)
```

## Integration with Journal Generation

The diff collection system is automatically integrated into the journal generation process:

1. **Context Collection**: When `collect_git_context()` runs, it automatically calls `get_commit_file_diffs()`
2. **Journal Enhancement**: The AI uses diff information to provide specific code insights
3. **Graceful Degradation**: If diff collection fails, the journal generation continues with other available context

## Performance Characteristics

- **Typical execution**: <100ms for commits with <10 files
- **Large commits** (>50 files): <500ms due to sampling and limits
- **Memory usage**: Bounded by max_total_size parameter (default 50KB)

## Configuration

### Default Parameters

```python
get_commit_file_diffs(
    repo,
    commit,
    max_file_size=10*1024,   # 10KB base limit (adaptive)
    max_total_size=50*1024   # 50KB total limit
)
```

### Telemetry Integration

The function includes comprehensive telemetry tracking:

- **Performance monitoring**: Execution duration and memory usage
- **File analysis**: Counts of processed, filtered, and truncated files
- **Error classification**: Proper categorization of git, filesystem, and memory errors

## Return Value Structure

The function returns a dictionary with the following structure:

```python
{
    "src/example.py": "diff content for example.py",
    "src/utils.py": "diff content for utils.py",
    # Special keys for metadata:
    "__truncated__": "Additional diffs omitted due to size limits",  # If applicable
    "__error__": "Error description if critical failure occurred"     # If applicable
}
```

## Generated File Patterns

The system automatically filters out common generated file patterns:

- **Package managers**: `package-lock.json`, `yarn.lock`, `Cargo.lock`, `poetry.lock`
- **Build outputs**: Files in `dist/`, `build/`, `target/`, `.next/`
- **Dependencies**: `node_modules/`, `vendor/`, `.venv/`
- **IDE files**: `.vscode/`, `.idea/`, `*.swp`
- **OS files**: `.DS_Store`, `Thumbs.db`

## Error Recovery

The system provides multiple levels of error recovery:

1. **Individual file errors**: Continue processing other files
2. **Size limit exceeded**: Include truncation marker and partial results
3. **Critical git errors**: Return structured error message
4. **Missing dependencies**: Clear error message about GitPython requirement

This ensures journal generation can continue even when diff collection encounters issues. 