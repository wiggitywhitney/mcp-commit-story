import os
import pytest
from pathlib import Path
import re

SRC_DIR = Path(__file__).parent.parent.parent / "src" / "mcp_commit_story"
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
SPEC_PATH = Path(__file__).parent.parent.parent / "engineering-mcp-journal-spec-final.md"
GUIDANCE_PATH = DOCS_DIR / "on-demand-directory-pattern.md"


def test_journal_functions_have_on_demand_docstrings():
    # Check that all file-writing functions mention the on-demand pattern in their docstrings
    file_ops = [
        (SRC_DIR / "journal.py", ["append_to_journal_file", "ensure_journal_directory"]),
        (SRC_DIR / "journal_init.py", []),  # Add any file-writing functions here if present
    ]
    for file_path, fnames in file_ops:
        if not file_path.exists():
            continue
        with open(file_path) as f:
            code = f.read()
        for fname in fnames:
            # Find the function definition and its docstring
            m = re.search(rf"def {fname}.*?\n\s+\"\"\"(.*?)\"\"\"", code, re.DOTALL)
            assert m, f"Function {fname} not found in {file_path}"
            doc = m.group(1)
            assert "on-demand" in doc.lower(), f"Docstring for {fname} in {file_path} does not mention on-demand pattern"


def test_engineering_spec_has_on_demand_pattern_section():
    # Check for a section header mentioning 'On-Demand Directory Creation Pattern'
    if not SPEC_PATH.exists():
        pytest.skip("engineering spec not found")
    with open(SPEC_PATH) as f:
        content = f.read()
    assert re.search(r"on-demand directory creation pattern", content, re.IGNORECASE), "Engineering spec missing on-demand directory creation pattern section"


def test_guidance_document_exists():
    # Check that docs/on-demand-directory-pattern.md exists
    assert GUIDANCE_PATH.exists(), "Guidance document for on-demand directory pattern does not exist"


def test_create_journal_directories_removed():
    """Test that create_journal_directories is fully removed from journal.py and journal_init.py."""
    import pathlib
    for fname in [
        pathlib.Path('src/mcp_commit_story/journal.py'),
        pathlib.Path('src/mcp_commit_story/journal_init.py'),
    ]:
        if fname.exists():
            with open(fname) as f:
                code = f.read()
                assert 'def create_journal_directories' not in code, f"create_journal_directories still present in {fname}"
                assert 'create_journal_directories(' not in code, f"create_journal_directories reference still present in {fname}"


def test_no_code_calls_create_journal_directories():
    """No code in src/mcp_commit_story/ should reference create_journal_directories."""
    for pyfile in SRC_DIR.glob("*.py"):
        with open(pyfile) as f:
            code = f.read()
            assert 'create_journal_directories' not in code, f"Found reference to create_journal_directories in {pyfile}"


def test_task5_init_does_not_use_create_journal_directories():
    """Task 5 implementation and tests should not reference create_journal_directories."""
    # Task 5 is journal entry generation; check journal.py and related test files
    files_to_check = [
        SRC_DIR / "journal.py",
        Path(__file__).parent.parent / "unit" / "test_journal.py",
        Path(__file__).parent.parent / "integration" / "test_journal_init_integration.py",
    ]
    for file_path in files_to_check:
        if file_path.exists():
            with open(file_path) as f:
                code = f.read()
                assert 'create_journal_directories' not in code, f"Task 5 file {file_path} references create_journal_directories"


def test_file_operations_work_without_upfront_directory_creation(tmp_path):
    """File operations should succeed with only on-demand directory creation (no upfront creation)."""
    from mcp_commit_story.journal import append_to_journal_file
    test_file = tmp_path / "journal" / "daily" / "2025-05-28-journal.md"
    entry = "Test entry\n"
    # Should not raise
    append_to_journal_file(entry, test_file)
    assert test_file.exists(), "File was not created by on-demand pattern"
    with open(test_file) as f:
        assert f.read() == entry, "Entry not written correctly by on-demand pattern" 