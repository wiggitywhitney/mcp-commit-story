# Testing Standards for MCP Journal

This document outlines the testing standards and best practices for the MCP Journal project.

## Core Testing Principles

1. **Test-Driven Development (TDD)**
   - Write tests before implementing functionality
   - Run tests to ensure they fail initially
   - Implement the minimum code to make tests pass
   - Refactor while maintaining passing tests

2. **Test Coverage**
   - Aim for 90%+ test coverage for all code
   - All public API methods must have tests
   - Edge cases and error conditions must be tested
   - Test both happy paths and error paths

3. **Test Organization**
   - Unit tests in `tests/unit/`
   - Integration tests in `tests/integration/`
   - Test fixtures in `tests/fixtures/`
   - Name test files with `test_` prefix
   - Name test functions with `test_` prefix

## Running Tests

To run tests, use the provided scripts:

```bash
# Setup test environment (first time only)
./scripts/setup_test_env.sh

# Run all tests
./scripts/run_tests.sh

# Run specific tests
./scripts/run_tests.sh tests/unit/test_config.py

# Run tests with coverage
./scripts/run_tests.sh --cov=src
```

## Writing Tests

### Unit Tests

Unit tests should test individual components in isolation:

```python
# Example unit test
def test_config_defaults():
    """Test config object has correct defaults"""
    config = Config()
    assert config.journal_path == 'journal/'
    assert isinstance(config.git_exclude_patterns, list)
    assert config.telemetry_enabled is False
```

### Integration Tests

Integration tests should test components working together:

```python
# Example integration test
def test_config_loading_from_file():
    """Test loading configuration from a file"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a test config file
        config_path = Path(tmp_dir) / '.mcp-journalrc.yaml'
        with open(config_path, 'w') as f:
            f.write('journal:\n  path: test/\n')
        
        # Load the config and verify it works with the journal system
        config = load_config(config_path)
        journal = Journal(config)
        assert journal.path == 'test/'
```

### Mocking and Fixtures

Use pytest fixtures for shared setup and teardown:

```python
@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'journal': {'path': 'test_journal/'},
        'git': {'exclude_patterns': ['*.log']},
        'telemetry': {'enabled': False}
    }

def test_config_validation(sample_config):
    """Test config validation with fixture"""
    config = Config(sample_config)
    assert config.journal_path == 'test_journal/'
```

Use mocking for testing components that depend on external systems:

```python
def test_git_operations():
    """Test Git operations with mocking"""
    with patch('mcp_journal.git_utils.git.Repo') as mock_repo:
        # Setup mock
        mock_instance = mock_repo.return_value
        mock_instance.head.commit.hexsha = 'abcdef'
        
        # Test function
        result = get_current_commit_hash()
        assert result == 'abcdef'
```

## Continuous Integration

All tests must pass in the CI environment before merging changes:

- The CI pipeline runs all tests automatically
- PRs cannot be merged if tests fail
- Code coverage is reported in the CI pipeline

## Task Completion Criteria

A task is only considered complete when:

1. All tests for the task are written
2. All tests for the task pass
3. The code has been reviewed
4. All edge cases are covered
5. Documentation is updated

## Running Specific Task Tests

For Task 1 verification:
```bash
./scripts/run_tests.sh tests/unit/test_structure.py tests/unit/test_imports.py
```

For Task 2 verification:
```bash
./scripts/run_tests.sh tests/unit/test_config.py
``` 