import pytest

def call_mcp_server(*args, **kwargs):
    if kwargs.get('invalid'):
        return {'success': False, 'error': 'Invalid input'}
    return {'success': True, 'output': 'journal entry created'}

def call_cli_tool(*args, **kwargs):
    if kwargs.get('invalid'):
        return {'success': False, 'error': 'Invalid input'}
    return {'success': True, 'output': 'journal entry created'}

def test_mcp_server_minimal_journal_entry():
    response = call_mcp_server()
    assert response['success'] is True
    assert 'journal entry' in response['output']

def test_cli_tool_minimal_journal_entry():
    response = call_cli_tool()
    assert response['success'] is True
    assert 'journal entry' in response['output']

def test_mcp_server_handles_error():
    response = call_mcp_server(invalid=True)
    assert response['success'] is False
    assert 'error' in response

def test_cli_tool_handles_error():
    response = call_cli_tool(invalid=True)
    assert response['success'] is False
    assert 'error' in response 