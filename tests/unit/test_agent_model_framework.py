import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), './')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../tests/unit')))
from test_agent_model_validation import (
    agent_model_parse,
    agent_model_generate_summary,
    DAILY_NOTE_MD,
    REFLECTION_MD,
    SUMMARY_MD,
    EMPTY_MD,
    MALFORMED_MD,
)

def run_agent_model_tests():
    results = []
    # Test: Parse Daily Note
    try:
        entry = agent_model_parse(DAILY_NOTE_MD)
        results.append({'name': 'Parse Daily Note', 'status': 'success', 'output': entry})
    except Exception as e:
        results.append({'name': 'Parse Daily Note', 'status': 'exception', 'exception': str(e)})
    # Test: Parse Reflection
    try:
        entry = agent_model_parse(REFLECTION_MD)
        results.append({'name': 'Parse Reflection', 'status': 'success', 'output': entry})
    except Exception as e:
        results.append({'name': 'Parse Reflection', 'status': 'exception', 'exception': str(e)})
    # Test: Generate Summary
    try:
        summary = agent_model_generate_summary(SUMMARY_MD)
        results.append({'name': 'Generate Summary', 'status': 'success', 'output': summary})
    except Exception as e:
        results.append({'name': 'Generate Summary', 'status': 'exception', 'exception': str(e)})
    # Test: Handle Empty Entry
    try:
        agent_model_parse(EMPTY_MD)
        results.append({'name': 'Handle Empty Entry', 'status': 'failure', 'output': 'No exception raised'})
    except Exception as e:
        results.append({'name': 'Handle Empty Entry', 'status': 'exception', 'exception': str(e)})
    # Test: Handle Malformed Entry
    try:
        agent_model_parse(MALFORMED_MD)
        results.append({'name': 'Handle Malformed Entry', 'status': 'failure', 'output': 'No exception raised'})
    except Exception as e:
        results.append({'name': 'Handle Malformed Entry', 'status': 'exception', 'exception': str(e)})
    return results

# Minimal TDD tests for the agent/model test execution framework

def test_framework_runs_and_captures_results():
    results = run_agent_model_tests()
    assert isinstance(results, list)
    assert any(r['status'] == 'success' for r in results) or any(r['status'] == 'failure' for r in results)


def test_framework_logs_results(capsys):
    results = run_agent_model_tests()
    for r in results:
        print(f"{r['name']}: {r['status']}")
    captured = capsys.readouterr()
    assert any('success' in captured.out or 'failure' in captured.out for _ in results)


def test_framework_handles_exceptions():
    results = run_agent_model_tests()
    assert any(r['status'] == 'exception' for r in results) 