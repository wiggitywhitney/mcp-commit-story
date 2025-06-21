# Engineering Specification: MCP Commit Story

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [MCP Server Implementation](#mcp-server-implementation)
4. [Git Integration](#git-integration)
5. [SQLite Database Integration](#sqlite-database-integration)
6. [Exception Handling Architecture](#exception-handling-architecture)
7. [Journal Generation](#journal-generation)
8. [Testing Strategy](#testing-strategy)
9. [Development Workflow](#development-workflow)
10. [Deployment](#deployment)

## Overview

MCP Commit Story is a Model Context Protocol (MCP) server that generates journal entries from git commits and AI chat history. The system reads Cursor's SQLite chat databases, extracts conversation context, and combines it with git metadata to create comprehensive development journal entries.

### Key Components
- **MCP Server**: Protocol-compliant server exposing journal generation tools
- **Git Integration**: Commit metadata extraction and diff analysis
- **Database Integration**: Cross-platform Cursor chat database access
- **Exception Handling**: Comprehensive error management with user-friendly messages
- **Journal Generator**: AI-powered content synthesis and formatting

### Technical Stack
- **Language**: Python 3.11+
- **MCP Framework**: Custom implementation following MCP protocol
- **Database**: SQLite (read-only access to Cursor databases)
- **Git Integration**: GitPython library
- **Testing**: pytest with comprehensive coverage
- **Documentation**: Markdown with inline code examples

## Architecture

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │◄──►│   MCP Server     │◄──►│  Git Repository │
│  (AI Assistant) │    │ (mcp-commit-story)│    │   (Commits)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Cursor Databases │
                       │   (Chat History) │
                       └──────────────────┘
```

### Module Structure

```
src/mcp_commit_story/
├── server.py                 # MCP server implementation
├── journal.py               # Journal generation logic
├── git_integration.py       # Git operations and metadata
├── cursor_db/              # Database integration package
│   ├── __init__.py
│   ├── platform.py         # Cross-platform path detection
│   ├── connection.py        # Database connection and queries
│   └── exceptions.py        # Exception handling system
└── tools/                  # MCP tool implementations
    └── journal_tools.py    # Journal generation MCP tools
```

## MCP Server Implementation

### Server Configuration

The MCP server follows the official MCP protocol specification with these key components:

```python
# server.py
class MCPCommitStoryServer:
    def __init__(self):
        self.tools = [
            Tool(
                name="generate_journal_entry",
                description="Generate journal entry from git commit and chat history",
                inputSchema=JOURNAL_ENTRY_SCHEMA
            )
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name == "generate_journal_entry":
            return await self.generate_journal_entry(**arguments)
```

### Tool Schema

```json
{
  "type": "object",
  "properties": {
    "commit_hash": {
      "type": "string",
      "description": "Git commit hash to generate journal entry for"
    },
    "workspace_path": {
      "type": "string",
      "description": "Optional path to workspace for chat history"
    },
    "output_format": {
      "type": "string",
      "enum": ["markdown", "text", "json"],
      "default": "markdown"
    }
  },
  "required": ["commit_hash"]
}
```

## Git Integration

### Commit Metadata Extraction

```python
# git_integration.py
class GitRepository:
    def __init__(self, repo_path: str):
        self.repo = git.Repo(repo_path)
    
    def get_commit_info(self, commit_hash: str) -> CommitInfo:
        commit = self.repo.commit(commit_hash)
        return CommitInfo(
            hash=commit.hexsha,
            message=commit.message,
            author=commit.author.name,
            timestamp=commit.committed_datetime,
            files_changed=list(commit.stats.files.keys()),
            insertions=commit.stats.total["insertions"],
            deletions=commit.stats.total["deletions"]
        )
```

### Diff Analysis

```python
def analyze_commit_changes(self, commit_hash: str) -> ChangeAnalysis:
    commit = self.repo.commit(commit_hash)
    changes = {
        'added_files': [],
        'modified_files': [],
        'deleted_files': [],
        'renamed_files': []
    }
    
    for item in commit.diff(commit.parents[0] if commit.parents else None):
        if item.new_file:
            changes['added_files'].append(item.b_path)
        elif item.deleted_file:
            changes['deleted_files'].append(item.a_path)
        elif item.renamed_file:
            changes['renamed_files'].append((item.a_path, item.b_path))
        else:
            changes['modified_files'].append(item.b_path)
    
    return ChangeAnalysis(**changes)
```

## SQLite Database Integration

### Cross-Platform Database Discovery

The system automatically discovers Cursor chat databases across different platforms:

```python
# cursor_db/platform.py
def get_cursor_workspace_paths() -> List[str]:
    platform_info = detect_platform()
    
    if platform_info.is_wsl:
        # WSL: Check Windows paths first, then Linux fallback
        paths = get_windows_cursor_paths_from_wsl()
        paths.extend(get_linux_cursor_paths())
    elif platform_info.system == "Windows":
        paths = get_windows_cursor_paths()
    elif platform_info.system == "Darwin":
        paths = get_macos_cursor_paths()
    else:  # Linux
        paths = get_linux_cursor_paths()
    
    return validate_workspace_paths(paths)
```

### Database Connection Management

```python
# cursor_db/connection.py
def get_cursor_chat_database(user_override_path: Optional[str] = None) -> str:
    """
    Get path to a valid Cursor chat database with comprehensive error handling.
    
    Returns:
        str: Path to validated database file
        
    Raises:
        CursorDatabaseNotFoundError: When no valid database found
        CursorDatabaseAccessError: When database exists but cannot be accessed
    """
    if user_override_path:
        return _validate_database_file(Path(user_override_path))
    
    # Auto-discovery with 48-hour recency filter
    workspace_paths = get_cursor_workspace_paths()
    valid_databases = []
    
    for workspace_path in workspace_paths:
        for db_file in Path(workspace_path).rglob("state.vscdb"):
            file_age_hours = (time.time() - db_file.stat().st_mtime) / 3600
            if file_age_hours <= 48:  # Only recent databases
                try:
                    validated_path = _validate_database_file(db_file)
                    valid_databases.append((validated_path, file_age_hours))
                except (CursorDatabaseAccessError, CursorDatabaseQueryError):
                    continue
    
    if not valid_databases:
        raise CursorDatabaseNotFoundError(
            "No valid Cursor chat databases found in recent workspace activity",
            search_criteria="state.vscdb files modified within 48 hours"
        )
    
    # Return most recently modified database
    valid_databases.sort(key=lambda x: x[1])
    return valid_databases[0][0]
```

### Query Interface

```python
def query_cursor_chat_database(database_path: str, sql: str, 
                             parameters: Optional[Tuple] = None) -> List[Tuple[Any, ...]]:
    """
    Execute SQL query with comprehensive error handling and logging.
    
    Returns:
        List of tuples containing query results (raw SQLite format)
        
    Raises:
        CursorDatabaseAccessError: Database access issues
        CursorDatabaseSchemaError: Schema compatibility problems  
        CursorDatabaseQueryError: SQL syntax or parameter errors
    """
    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, parameters or ())
            return cursor.fetchall()
    except sqlite3.OperationalError as e:
        # Detailed error classification and user-friendly messages
        error_msg = str(e).lower()
        if "no such table" in error_msg or "no such column" in error_msg:
            raise CursorDatabaseSchemaError(f"Schema mismatch: {e}", sql=sql)
        elif "syntax error" in error_msg:
            raise CursorDatabaseQueryError(f"SQL syntax error: {e}", sql=sql)
        else:
            raise CursorDatabaseAccessError(f"Database operation failed: {e}")
```

## Exception Handling Architecture

### Exception Hierarchy

The system implements a comprehensive exception hierarchy for database operations:

```python
# cursor_db/exceptions.py

class CursorDatabaseError(Exception):
    """Base exception for all cursor database operations."""
    
    def __init__(self, message: str, **context_kwargs):
        super().__init__(message)
        self.message = message
        self.context = self._build_context(**context_kwargs)
        self.troubleshooting_hint = get_troubleshooting_hint(
            self.__class__.__name__.lower(), self.context
        )
    
    def _build_context(self, **kwargs) -> Dict[str, Any]:
        """Build comprehensive context with system information."""
        context = {
            'timestamp': time.time(),
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
        }
        context.update(kwargs)
        return self._sanitize_context(context)

class CursorDatabaseNotFoundError(CursorDatabaseError):
    """Database files cannot be found or discovered."""
    pass

class CursorDatabaseAccessError(CursorDatabaseError):
    """Database access denied due to permissions or locks."""
    pass

class CursorDatabaseSchemaError(CursorDatabaseError):
    """Database schema doesn't match expectations."""
    pass

class CursorDatabaseQueryError(CursorDatabaseError):
    """Query-related errors including syntax and parameters."""
    pass
```

### Context-Rich Error Messages

```python
def format_error_message(message: str, context: Optional[Dict[str, Any]] = None, 
                        troubleshooting_hint: Optional[str] = None) -> str:
    """Format comprehensive error messages with context and guidance."""
    formatted_parts = [message]
    
    if context:
        if 'path' in context and context['path']:
            formatted_parts.append(f"Path: {context['path']}")
        if 'sql' in context and context['sql']:
            sql = context['sql']
            if len(sql) > 100:
                sql = sql[:97] + "..."
            formatted_parts.append(f"SQL: {sql}")
    
    if troubleshooting_hint:
        formatted_parts.append(f"Troubleshooting: {troubleshooting_hint}")
    
    return " | ".join(formatted_parts)
```

### Troubleshooting Guidance

```python
def get_troubleshooting_hint(error_type: str, context: Dict[str, Any]) -> str:
    """Generate context-appropriate troubleshooting hints."""
    error_type = error_type.lower()
    
    if 'notfound' in error_type:
        hints = [
            "Ensure Cursor has been run recently in this workspace",
            "Check that the workspace contains Cursor chat history",
            "Verify the database path is correct"
        ]
        if context.get('path'):
            hints.append(f"Searched path: {context['path']}")
        return ". ".join(hints) + "."
    
    elif 'access' in error_type:
        permission_type = context.get('permission_type', 'access')
        hints = [
            f"Check file permissions for {permission_type} access",
            "Ensure the database file is not locked by another process",
            "Verify you have sufficient system permissions"
        ]
        if context.get('path'):
            hints.append(f"File path: {context['path']}")
        return ". ".join(hints) + "."
    
    elif 'schema' in error_type:
        hints = [
            "Database schema may be from a different Cursor version",
            "Check if Cursor has been updated recently",
            "Try using a more recent workspace database"
        ]
        if context.get('table_name'):
            hints.append(f"Missing table: {context['table_name']}")
        return ". ".join(hints) + "."
    
    elif 'query' in error_type:
        hints = [
            "Check the SQL query for syntax errors or typos",
            "Verify parameter count matches placeholders",
            "Ensure the query is valid SQLite syntax"
        ]
        # Parameter count validation
        if context.get('sql') and '?' in context.get('sql', ''):
            placeholder_count = context['sql'].count('?')
            param_count = len(context.get('parameters', []))
            if placeholder_count != param_count:
                hints.append(f"Query has {placeholder_count} placeholders but {param_count} parameters provided")
        return ". ".join(hints) + "."
    
    return "Ensure Cursor has been run recently in this workspace and check file permissions."
```

### Logging Integration

```python
# Connection functions include structured logging
logger = logging.getLogger(__name__)

def get_cursor_chat_database(user_override_path: Optional[str] = None) -> str:
    logger.info("Starting Cursor chat database discovery")
    
    try:
        # ... discovery logic ...
        logger.info(f"Selected most recent database: {selected_db}")
        return selected_db
    except CursorDatabaseNotFoundError as error:
        logger.error(f"Database not found: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        })
        raise
```

### Error Recovery Mechanisms

```python
def query_multiple_databases(sql: str, parameters: Optional[Tuple] = None, 
                           max_databases: int = 3) -> List[Tuple[str, List[Tuple[Any, ...]]]]:
    """Query multiple databases with automatic fallback handling."""
    try:
        workspace_paths = get_cursor_workspace_paths()
    except Exception as e:
        raise CursorDatabaseNotFoundError(
            "Failed to detect workspace paths for multi-database query"
        ) from e
    
    results = []
    for db_path, _ in selected_databases:
        try:
            query_results = query_cursor_chat_database(db_path, sql, parameters)
            results.append((db_path, query_results))
        except Exception as e:
            logger.warning(f"Query failed for database {db_path}: {e}")
            continue  # Graceful degradation
    
    return results
```
        CursorDatabaseAccessError: When database exists but cannot be accessed
    """
    if user_override_path:
        return _validate_database_file(Path(user_override_path))
    
    # Auto-discovery with 48-hour recency filter
    workspace_paths = get_cursor_workspace_paths()
    valid_databases = []
    
    for workspace_path in workspace_paths:
        for db_file in Path(workspace_path).rglob("state.vscdb"):
            file_age_hours = (time.time() - db_file.stat().st_mtime) / 3600
            if file_age_hours <= 48:  # Only recent databases
                try:
                    validated_path = _validate_database_file(db_file)
                    valid_databases.append((validated_path, file_age_hours))
                except (CursorDatabaseAccessError, CursorDatabaseQueryError):
                    continue
    
    if not valid_databases:
        raise CursorDatabaseNotFoundError(
            "No valid Cursor chat databases found in recent workspace activity",
            search_criteria="state.vscdb files modified within 48 hours"
        )
    
    # Return most recently modified database
    valid_databases.sort(key=lambda x: x[1])
    return valid_databases[0][0]
```

### Query Interface

```python
def query_cursor_chat_database(database_path: str, sql: str, 
                             parameters: Optional[Tuple] = None) -> List[Tuple[Any, ...]]:
    """
    Execute SQL query with comprehensive error handling and logging.
    
    Returns:
        List of tuples containing query results (raw SQLite format)
        
    Raises:
        CursorDatabaseAccessError: Database access issues
        CursorDatabaseSchemaError: Schema compatibility problems  
        CursorDatabaseQueryError: SQL syntax or parameter errors
    """
    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, parameters or ())
            return cursor.fetchall()
    except sqlite3.OperationalError as e:
        # Detailed error classification and user-friendly messages
        error_msg = str(e).lower()
        if "no such table" in error_msg or "no such column" in error_msg:
            raise CursorDatabaseSchemaError(f"Schema mismatch: {e}", sql=sql)
        elif "syntax error" in error_msg:
            raise CursorDatabaseQueryError(f"SQL syntax error: {e}", sql=sql)
        else:
            raise CursorDatabaseAccessError(f"Database operation failed: {e}")
```

## Exception Handling Architecture

### Exception Hierarchy

The system implements a comprehensive exception hierarchy for database operations:

```python
# cursor_db/exceptions.py

class CursorDatabaseError(Exception):
    """Base exception for all cursor database operations."""
    
    def __init__(self, message: str, **context_kwargs):
        super().__init__(message)
        self.message = message
        self.context = self._build_context(**context_kwargs)
        self.troubleshooting_hint = get_troubleshooting_hint(
            self.__class__.__name__.lower(), self.context
        )
    
    def _build_context(self, **kwargs) -> Dict[str, Any]:
        """Build comprehensive context with system information."""
        context = {
            'timestamp': time.time(),
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
        }
        context.update(kwargs)
        return self._sanitize_context(context)

class CursorDatabaseNotFoundError(CursorDatabaseError):
    """Database files cannot be found or discovered."""
    pass

class CursorDatabaseAccessError(CursorDatabaseError):
    """Database access denied due to permissions or locks."""
    pass

class CursorDatabaseSchemaError(CursorDatabaseError):
    """Database schema doesn't match expectations."""
    pass

class CursorDatabaseQueryError(CursorDatabaseError):
    """Query-related errors including syntax and parameters."""
    pass
```

### Context-Rich Error Messages

```python
def format_error_message(message: str, context: Optional[Dict[str, Any]] = None, 
                        troubleshooting_hint: Optional[str] = None) -> str:
    """Format comprehensive error messages with context and guidance."""
    formatted_parts = [message]
    
    if context:
        if 'path' in context and context['path']:
            formatted_parts.append(f"Path: {context['path']}")
        if 'sql' in context and context['sql']:
            sql = context['sql']
            if len(sql) > 100:
                sql = sql[:97] + "..."
            formatted_parts.append(f"SQL: {sql}")
    
    if troubleshooting_hint:
        formatted_parts.append(f"Troubleshooting: {troubleshooting_hint}")
    
    return " | ".join(formatted_parts)
```

### Troubleshooting Guidance

```python
def get_troubleshooting_hint(error_type: str, context: Dict[str, Any]) -> str:
    """Generate context-appropriate troubleshooting hints."""
    error_type = error_type.lower()
    
    if 'notfound' in error_type:
        hints = [
            "Ensure Cursor has been run recently in this workspace",
            "Check that the workspace contains Cursor chat history",
            "Verify the database path is correct"
        ]
        if context.get('path'):
            hints.append(f"Searched path: {context['path']}")
        return ". ".join(hints) + "."
    
    elif 'access' in error_type:
        permission_type = context.get('permission_type', 'access')
        hints = [
            f"Check file permissions for {permission_type} access",
            "Ensure the database file is not locked by another process",
            "Verify you have sufficient system permissions"
        ]
        if context.get('path'):
            hints.append(f"File path: {context['path']}")
        return ". ".join(hints) + "."
    
    elif 'schema' in error_type:
        hints = [
            "Database schema may be from a different Cursor version",
            "Check if Cursor has been updated recently",
            "Try using a more recent workspace database"
        ]
        if context.get('table_name'):
            hints.append(f"Missing table: {context['table_name']}")
        return ". ".join(hints) + "."
    
    elif 'query' in error_type:
        hints = [
            "Check the SQL query for syntax errors or typos",
            "Verify parameter count matches placeholders",
            "Ensure the query is valid SQLite syntax"
        ]
        # Parameter count validation
        if context.get('sql') and '?' in context.get('sql', ''):
            placeholder_count = context['sql'].count('?')
            param_count = len(context.get('parameters', []))
            if placeholder_count != param_count:
                hints.append(f"Query has {placeholder_count} placeholders but {param_count} parameters provided")
        return ". ".join(hints) + "."
    
    return "Ensure Cursor has been run recently in this workspace and check file permissions."
```

### Logging Integration

```python
# Connection functions include structured logging
logger = logging.getLogger(__name__)

def get_cursor_chat_database(user_override_path: Optional[str] = None) -> str:
    logger.info("Starting Cursor chat database discovery")
    
    try:
        # ... discovery logic ...
        logger.info(f"Selected most recent database: {selected_db}")
        return selected_db
    except CursorDatabaseNotFoundError as error:
        logger.error(f"Database not found: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        })
        raise
```

### Error Recovery Mechanisms

```python
def query_multiple_databases(sql: str, parameters: Optional[Tuple] = None, 
                           max_databases: int = 3) -> List[Tuple[str, List[Tuple[Any, ...]]]]:
    """Query multiple databases with automatic fallback handling."""
    try:
        workspace_paths = get_cursor_workspace_paths()
    except Exception as e:
        raise CursorDatabaseNotFoundError(
            "Failed to detect workspace paths for multi-database query"
        ) from e
    
    results = []
    for db_path, _ in selected_databases:
        try:
            query_results = query_cursor_chat_database(db_path, sql, parameters)
            results.append((db_path, query_results))
        except Exception as e:
            logger.warning(f"Query failed for database {db_path}: {e}")
            continue  # Graceful degradation
    
    return results
```

### On-Demand Directory Creation Pattern

The system implements an on-demand directory creation pattern for journal output and temporary files:

```python
# Ensure output directories exist before writing
def ensure_journal_output_directory(output_path: str) -> Path:
    """Create journal output directory structure on-demand."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

# Example usage in journal generation
def write_journal_entry(content: str, output_path: str) -> None:
    """Write journal entry with on-demand directory creation."""
    ensure_journal_output_directory(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
```

## Journal Generation

### Content Synthesis Pipeline

```python
# journal.py
class JournalGenerator:
    def __init__(self, git_repo: GitRepository, db_connection: str):
        self.git_repo = git_repo
        self.db_connection = db_connection
    
    async def generate_entry(self, commit_hash: str) -> JournalEntry:
        # 1. Extract git metadata
        commit_info = self.git_repo.get_commit_info(commit_hash)
        
        # 2. Query chat history around commit time
        chat_context = await self.extract_chat_context(
            commit_info.timestamp, 
            commit_info.files_changed
        )
        
        # 3. Synthesize content sections
        return JournalEntry(
            summary=await self.generate_summary(commit_info, chat_context),
            technical_synopsis=self.generate_technical_synopsis(commit_info),
            accomplishments=await self.generate_accomplishments(chat_context),
            frustrations=await self.extract_frustrations(chat_context),
            discussion_notes=self.extract_discussion_notes(chat_context),
            tone_mood=await self.analyze_tone_mood(chat_context),
            commit_metadata=self.format_commit_metadata(commit_info)
        )
```

### Chat Context Extraction

```python
async def extract_chat_context(self, commit_time: datetime, 
                             changed_files: List[str]) -> ChatContext:
    # Query chat messages around commit time (±2 hours)
    time_window_start = commit_time - timedelta(hours=2)
    time_window_end = commit_time + timedelta(hours=2)
    
    messages = query_cursor_chat_database(
        self.db_connection,
        """
        SELECT timestamp, role, content 
        FROM chat_messages 
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """,
        (time_window_start.timestamp(), time_window_end.timestamp())
    )
    
    # Filter messages related to changed files
    relevant_messages = []
    for timestamp, role, content in messages:
        if any(file_path in content for file_path in changed_files):
            relevant_messages.append(ChatMessage(timestamp, role, content))
    
    return ChatContext(
        messages=relevant_messages,
        time_window=(time_window_start, time_window_end),
        related_files=changed_files
    )
```

## Testing Strategy

### Test Structure

```
tests/
├── unit/                           # Unit tests for individual modules
│   ├── test_platform_detection.py # Cross-platform path detection
│   ├── test_database_connection.py # Database connection and queries
│   ├── test_cursor_db_exceptions.py # Exception handling system
│   ├── test_git_integration.py    # Git operations
│   └── test_journal.py            # Journal generation logic
├── integration/                   # Integration tests
│   ├── test_mcp_server.py         # MCP protocol compliance
│   ├── test_end_to_end.py         # Full journal generation
│   └── test_database_integration.py # Real database testing
└── fixtures/                     # Test data and mock databases
    ├── sample_commits/            # Git repository fixtures
    └── cursor_databases/          # Sample Cursor database files
```

### Exception Testing Strategy

```python
# tests/unit/test_cursor_db_exceptions.py
class TestExceptionHandling:
    def test_database_not_found_error_context(self):
        """Test comprehensive context collection for not found errors."""
        error = CursorDatabaseNotFoundError(
            "Database not found",
            path="/test/path",
            search_type="auto_discovery"
        )
        
        assert error.context["path"] == "/test/path"
        assert error.context["search_type"] == "auto_discovery"
        assert "cursor" in error.troubleshooting_hint.lower()
        assert "timestamp" in error.context
        assert "platform" in error.context
    
    def test_connection_function_integration(self):
        """Test that connection functions raise proper exceptions."""
        with patch('mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths', 
                  return_value=[]):
            with pytest.raises(CursorDatabaseNotFoundError) as exc_info:
                get_cursor_chat_database()
            
            assert "no valid" in exc_info.value.message.lower()
            assert exc_info.value.context["search_type"] == "auto_discovery"
```

### Coverage Requirements

- **Unit Tests**: >90% code coverage for all modules
- **Exception Paths**: 100% coverage of error handling scenarios  
- **Integration Tests**: Real database testing across platforms
- **Performance Tests**: Database discovery and query performance
- **Security Tests**: Sensitive data sanitization validation

## Development Workflow

### TDD Implementation Process

1. **Write Failing Tests**: Create comprehensive test cases that fail initially
2. **Implement Functionality**: Write minimal code to make tests pass
3. **Refactor and Optimize**: Improve code quality while maintaining test coverage
4. **Document and Complete**: Update documentation and mark tasks complete

### Error Handling Development

1. **Define Exception Classes**: Create specific exception types for different failure modes
2. **Implement Context Collection**: Add comprehensive context information to exceptions
3. **Create Troubleshooting Hints**: Generate user-friendly guidance for each error type
4. **Test Error Scenarios**: Validate exception handling with comprehensive test coverage
5. **Integrate Logging**: Add structured logging with error context and troubleshooting hints

### Code Quality Standards

- **Type Hints**: Full type annotation for all public APIs
- **Documentation**: Comprehensive docstrings with examples
- **Error Handling**: Explicit exception handling with user-friendly messages
- **Logging**: Structured logging with appropriate levels and context
- **Testing**: High test coverage with both positive and negative test cases

## Deployment

### Package Structure

```
mcp-commit-story/
├── src/mcp_commit_story/
├── tests/
├── docs/
├── pyproject.toml              # Package configuration
├── README.md                   # User documentation  
└── requirements.txt            # Dependencies
```

### Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "gitpython>=3.1.0",
    "mcp>=0.1.0", 
    "sqlite3",  # Built-in Python module
    "typing-extensions>=4.0.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "mypy>=1.0.0"
]
```

### Installation and Setup

```bash
# Development installation
pip install -e .[dev]

# Production installation  
pip install mcp-commit-story

# MCP server setup and configuration
# Add to ~/.config/mcp/settings.json:
{
  "mcpServers": {
    "commit-story": {
      "command": "python",
      "args": ["-m", "mcp_commit_story.server"]
    }
  }
}
```

This engineering specification provides a comprehensive foundation for implementing MCP Commit Story with robust error handling, cross-platform compatibility, and maintainable architecture.

