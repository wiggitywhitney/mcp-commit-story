# Testing Standards for MCP Commit Story

This document outlines the testing standards and best practices for the MCP Commit Story project.

## Current Testing Overview

The project currently has **532 tests** across **43 test files** with **80% test coverage**. The testing strategy emphasizes comprehensive coverage of MCP operations, telemetry integration, and core journal functionality.

## Core Testing Principles

1. **Test-Driven Development (TDD)**
   - Write tests before implementing functionality
   - Run tests to ensure they fail initially
   - Implement the minimum code to make tests pass
   - Refactor while maintaining passing tests

2. **Test Coverage Standards**
   - Current coverage: **80%** (Target: 90%+)
   - All public API methods must have tests
   - All MCP operation handlers must be fully covered
   - Edge cases and error conditions must be tested
   - Test both happy paths and error paths

3. **Test Organization**
   - **Unit tests**: `tests/unit/` (26 files) - Fast, isolated component tests
   - **Integration tests**: `tests/integration/` (6 files) - Cross-component tests
   - **Main test directory**: Core system tests (telemetry, journal, structured logging)
   - **Test fixtures**: `tests/fixtures/` - Shared test data and utilities
   - **Configuration**: `tests/conftest.py` - Pytest configuration and fixtures

## Test Directory Structure

```
tests/
├── unit/                          # Unit tests (26 files)
│   ├── test_server.py            # MCP server operations
│   ├── test_config*.py           # Configuration system
│   ├── test_journal*.py          # Journal functionality
│   ├── test_git_utils.py         # Git operations
│   ├── test_reflection_mcp.py    # Reflection operations
│   └── ...                       # Other component tests
├── integration/                   # Integration tests (6 files)
│   ├── test_mcp_server_integration.py
│   ├── test_telemetry_validation_integration.py
│   └── ...
├── fixtures/                     # Test data and utilities
├── test_telemetry.py             # Core telemetry testing (937 lines)
├── test_structured_logging.py   # Logging system tests (775 lines)
├── test_journal_telemetry.py    # Journal telemetry integration
└── conftest.py                   # Pytest configuration
```

## Running Tests

### Standard Test Commands

```bash
# Setup test environment (first time only)
./scripts/setup_test_env.sh

# Run all tests
./scripts/run_tests.sh

# Run specific test files
./scripts/run_tests.sh tests/unit/test_server.py

# Run tests with coverage report
./scripts/run_tests.sh --cov=src --cov-report=term-missing

# Run only unit tests (fast)
./scripts/run_tests.sh tests/unit/

# Run only integration tests
./scripts/run_tests.sh tests/integration/

# Run tests quietly (summary only)
./scripts/run_tests.sh -q

# Run specific test patterns
./scripts/run_tests.sh -k "telemetry"
./scripts/run_tests.sh -k "server and mcp"
```

### Test Environment

The test environment uses:
- **Python 3.9+** requirement
- **Virtual environment** in `.venv/`
- **pytest** as the test runner
- **coverage.py** for coverage analysis
- **Git repository fixture** for git-dependent tests

## Testing Patterns and Standards

### MCP Operation Handler Tests

All MCP operation handlers must have comprehensive test coverage:

```python
# Example: MCP handler testing pattern
@pytest.mark.asyncio
async def test_journal_add_reflection_handler_success():
    """Test successful reflection addition via MCP."""
    request = {"text": "Test reflection", "date": "2025-06-03"}
    result = await handle_journal_add_reflection(request)
    
    assert result["status"] == "success"
    assert "file_path" in result

def test_journal_add_reflection_handler_missing_fields():
    """Test error handling for missing required fields."""
    request = {"date": "2025-06-03"}  # Missing text
    response = asyncio.run(handle_journal_add_reflection(request))
    
    assert response["status"] == "error"
    assert "Missing required field" in response["error"]
```

### Reflection Integration Testing Patterns

Comprehensive reflection functionality testing requires sophisticated mocking and isolation patterns:

#### Test Isolation with Temporary Directories

```python
def create_isolated_temp_dir():
    """Create a fresh temporary directory for each test to ensure isolation."""
    return tempfile.mkdtemp()

@pytest.mark.asyncio
async def test_reflection_with_isolation():
    """Test reflection operations with complete isolation."""
    temp_dir = create_isolated_temp_dir()
    try:
        # Test logic using temp_dir
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        with patch('src.mcp_commit_story.server.add_manual_reflection', side_effect=mock_add_manual_reflection):
            result = await handle_journal_add_reflection({"text": "Test", "date": "2025-06-01"})
            assert result["status"] == "success"
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
```

#### Server-Level Mocking for MCP Handlers

```python
def test_mcp_reflection_handler_mocking():
    """Test MCP handler with proper server-level mocking."""
    from src.mcp_commit_story.server import handle_journal_add_reflection
    from src.mcp_commit_story.reflection_core import add_manual_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        # Create mock configuration
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        # Mock at server level where function is imported
        def mock_add_manual_reflection(text, date):
            with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
                return add_manual_reflection(text, date)
        
        with patch('src.mcp_commit_story.server.add_manual_reflection', side_effect=mock_add_manual_reflection):
            request = {"text": "Integration test reflection", "date": "2025-06-01"}
            result = await handle_journal_add_reflection(request)
            
            # Verify file created in temp directory, not project root
            assert result["status"] == "success"
            assert temp_dir in result["file_path"]
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
```

#### Comprehensive Integration Test Coverage

```python
@pytest.mark.asyncio
async def test_reflection_comprehensive_integration():
    """Test reflection system integration across multiple scenarios."""
    test_scenarios = [
        # Test unicode and special characters
        {"text": "Unicode test: 🎉 café naïve résumé", "date": "2025-06-01"},
        
        # Test large content handling
        {"text": "Large content: " + "analysis " * 200, "date": "2025-06-02"},
        
        # Test concurrent operations
        {"text": "Concurrent reflection {i}", "date": "2025-06-03"}
    ]
    
    for scenario in test_scenarios:
        result = await handle_journal_add_reflection(scenario)
        assert result["status"] == "success"
        
        # Verify content preservation
        file_path = Path(result["file_path"])
        content = file_path.read_text(encoding='utf-8')
        assert scenario["text"] in content
```

#### Error Recovery and Resilience Testing

```python
@pytest.mark.asyncio
async def test_reflection_error_recovery():
    """Test reflection system error recovery and resilience."""
    temp_dir = create_isolated_temp_dir()
    try:
        # Test permission error recovery
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            request = {"text": "Permission error test", "date": "2025-06-01"}
            
            try:
                result = await handle_journal_add_reflection(request)
                if isinstance(result, dict):
                    assert result["status"] == "error"
                    assert "permission" in result["error"].lower()
            except PermissionError:
                pass  # Exception is also acceptable error handling
        
        # Verify system recovers after error
        normal_request = {"text": "Recovery test", "date": "2025-06-02"}
        result = await handle_journal_add_reflection(normal_request)
        assert result["status"] == "success"
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
```

#### Telemetry Integration in Reflection Tests

```python
@pytest.mark.asyncio
async def test_reflection_telemetry_integration():
    """Test reflection operations include proper telemetry instrumentation."""
    temp_dir = create_isolated_temp_dir()
    try:
        with patch('opentelemetry.trace.get_current_span') as mock_span:
            mock_span_instance = MagicMock()
            mock_span.return_value = mock_span_instance
            
            request = {"text": "Telemetry test reflection", "date": "2025-06-01"}
            result = await handle_journal_add_reflection(request)
            
            assert result["status"] == "success"
            
            # Verify telemetry attributes were set
            set_attribute_calls = mock_span_instance.set_attribute.call_args_list
            assert len(set_attribute_calls) > 0
            
            # Check for expected telemetry attributes
            attribute_names = [call[0][0] for call in set_attribute_calls]
            expected_attrs = ["mcp.operation", "reflection.date"]
            found_attrs = [attr for attr in expected_attrs if attr in attribute_names]
            assert len(found_attrs) > 0
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
```

#### Test Pattern Key Principles

1. **Complete Isolation**: Each test uses isolated temp directories to prevent interference
2. **Server-Level Mocking**: Mock imports at the server module level, not deep in the call stack
3. **Comprehensive Scenarios**: Test unicode, large content, concurrent operations, and error cases
4. **Telemetry Validation**: Ensure all operations are properly instrumented
5. **Cleanup Guarantees**: Always clean up temp directories in finally blocks
6. **Real Integration**: Use actual reflection core functions with mocked configuration

### Telemetry and Observability Tests

Extensive telemetry testing ensures monitoring works correctly:

```python
def test_trace_mcp_operation_decorator():
    """Test MCP operation tracing decorator functionality."""
    @trace_mcp_operation("test_operation")
    def traced_function(x, y):
        return x + y
    
    result = traced_function(1, 2)
    assert result == 3
    
    # Verify telemetry spans were created
    # (Additional span verification logic)
```

### Configuration and Error Handling Tests

Comprehensive testing of configuration loading and error scenarios:

```python
def test_config_loading_with_telemetry_sampling():
    """Test config loading includes both validate and load operations."""
    with patch('random.random', return_value=0.0):  # Force sampling
        config = load_config()
        
        # Should record both validation and loading telemetry
        metrics = get_collected_metrics()
        operations = [m for m in metrics if 'mcp.config.operations_total' in str(m)]
        assert len(operations) >= 2  # validate + load
```

### Test Fixtures and Mocking

Standard fixtures for common test scenarios:

```python
@pytest.fixture
def git_repo():
    """Create temporary git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    try:
        repo = git.Repo.init(temp_dir)
        yield repo
    finally:
        shutil.rmtree(temp_dir)

def test_git_operations_with_fixture(git_repo):
    """Test using the git repository fixture."""
    # Test logic using git_repo
    assert git_repo.working_tree_dir is not None
```

### Async Function Testing

Pattern for testing async MCP operations:

```python
@pytest.mark.asyncio
async def test_async_mcp_operation():
    """Test async MCP operation handler."""
    request = {"param": "value"}
    result = await async_handler(request)
    assert result is not None

# Alternative pattern for sync test of async function
def test_async_operation_sync():
    """Test async operation using asyncio.run."""
    result = asyncio.run(async_handler({"param": "value"}))
    assert result["status"] == "success"
```

## Key Testing Areas

### 1. MCP Server Operations
- **Files**: `tests/unit/test_server.py`, `tests/integration/test_mcp_server_integration.py`
- **Coverage**: All handler functions, error scenarios, configuration loading
- **Focus**: Request validation, response formatting, error handling

### 2. Journal Generation System
- **Files**: `tests/unit/test_journal.py`, `tests/test_journal_entry.py`, `tests/test_journal_telemetry.py`
- **Coverage**: Entry creation, markdown serialization, AI generation placeholders
- **Focus**: Content formatting, telemetry integration, file operations

### 3. Telemetry and Observability
- **Files**: `tests/test_telemetry.py` (937 lines), `tests/test_structured_logging.py`, integration tests
- **Coverage**: OpenTelemetry setup, decorators, metrics collection, structured logging
- **Focus**: Trace correlation, performance monitoring, error categorization

### 4. Configuration Management
- **Files**: `tests/unit/test_config.py`, `tests/unit/test_config_telemetry.py`
- **Coverage**: Config loading, validation, telemetry integration, error handling
- **Focus**: YAML parsing, default values, environment variables

### 5. Git Integration
- **Files**: `tests/unit/test_git_utils.py` (608 lines), `tests/integration/test_git_hook_integration.py`
- **Coverage**: Repository operations, commit analysis, hook installation
- **Focus**: File change detection, commit metadata, performance optimization

### 6. Context Collection
- **Files**: `tests/unit/test_context_collection.py`, `tests/unit/test_context_types.py`
- **Coverage**: Git context gathering, type definitions, performance limits
- **Focus**: Data collection, structured types, error handling

## Test Execution Strategy

### Continuous Integration

All tests run automatically in CI:
- **Total tests**: 532 tests collected
- **Success criteria**: All tests must pass for merge
- **Coverage reporting**: 80% current coverage displayed
- **Performance**: Fast unit tests prioritized for quick feedback

### Test Categories

1. **Fast Unit Tests** (`tests/unit/`): Component isolation, mocking external dependencies
2. **Integration Tests** (`tests/integration/`): Cross-component testing, real integrations
3. **Telemetry Tests**: Comprehensive observability verification
4. **System Tests**: End-to-end journal generation and MCP operations

### Quality Gates

A feature is considered complete when:

1. **All tests written and passing**: Comprehensive test coverage for new functionality
2. **Error scenarios covered**: Both success and failure paths tested
3. **Telemetry instrumented**: Monitoring and observability included
4. **Integration verified**: Works with existing MCP operations
5. **Documentation updated**: Code and API documentation current

## Special Test Considerations

### Telemetry Testing Challenges

Telemetry tests handle OpenTelemetry global state:
- Use `setup_method`/`teardown_method` for test isolation
- Mock external exporters to avoid network dependencies
- Test both enabled and disabled telemetry configurations
- Verify span attributes and metric collection without brittle assertions

### Git Repository Testing

Git-dependent tests use temporary repositories:
- `git_repo` fixture provides isolated test environments
- Tests avoid dependency on real repository state
- File operations use temporary directories for isolation

### Async Operation Testing

MCP handlers are async and require special handling:
- Use `@pytest.mark.asyncio` for native async testing
- Use `asyncio.run()` for sync test execution of async functions
- Mock async dependencies appropriately

## Performance Testing

### Coverage Analysis
Current coverage breakdown shows strong testing foundation:
- **Lines of code**: 2,596 total
- **Uncovered lines**: 512
- **Coverage percentage**: 80%

### Test Performance
- **Unit tests**: Fast execution for quick feedback
- **Integration tests**: Longer-running but comprehensive
- **Telemetry tests**: Include performance threshold validation

## See Also

- **[MCP API Specification](mcp-api-specification.md)** - API contracts tested by integration tests
- **[Telemetry](telemetry.md)** - Comprehensive telemetry system being tested
- **[Implementation Guide](implementation-guide.md)** - Development patterns and practices 