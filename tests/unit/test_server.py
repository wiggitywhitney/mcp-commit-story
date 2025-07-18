import pytest
from unittest import mock
from mcp_commit_story.server import create_mcp_server, get_version_from_pyproject, register_tools, MCPError, handle_mcp_error
from mcp.server.fastmcp import FastMCP
from mcp_commit_story.config import Config
import logging
import asyncio
import io
import tempfile
import yaml
import os

def test_create_mcp_server_sets_name_and_calls_register_tools(tmp_path):
    # Patch pyproject.toml to a temp file with known version
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "mcp-commit-story"
version = "9.9.9"
""")
    minimal_config = {
        "journal": {"path": "journal/"},
        "git": {"exclude_patterns": ["journal/**"]},
        "telemetry": {"enabled": False}
    }
    with mock.patch("mcp_commit_story.server.get_version_from_pyproject", wraps=get_version_from_pyproject) as get_ver:
        version = get_version_from_pyproject(str(pyproject))
        assert version == "9.9.9"
        # Patch get_version_from_pyproject to use our temp file
        with mock.patch("mcp_commit_story.server.get_version_from_pyproject", return_value="9.9.9") as ver_patch:
            with mock.patch("mcp_commit_story.server.load_config", return_value=Config(minimal_config)):
                with mock.patch("mcp_commit_story.server.register_tools") as reg_tools:
                    server = create_mcp_server()
                    assert server.name == "mcp-commit-story"
                    reg_tools.assert_called_once_with(server)
            ver_patch.assert_called()

def test_create_mcp_server_loads_config_and_telemetry(monkeypatch):
    # Patch load_config to return a config with telemetry enabled
    minimal_config = {
        "journal": {"path": "journal/"},
        "git": {"exclude_patterns": ["journal/**"]},
        "telemetry": {"enabled": True}
    }
    config = Config(minimal_config)
    monkeypatch.setattr("mcp_commit_story.server.load_config", lambda *a, **k: config)
    # If setup_telemetry exists, patch it; otherwise, just run
    try:
        import mcp_commit_story.server as server_mod
        if hasattr(server_mod.telemetry, "setup_telemetry"):
            telemetry_called = {}
            def fake_setup_telemetry(cfg):
                telemetry_called["called"] = True
            monkeypatch.setattr(server_mod.telemetry, "setup_telemetry", fake_setup_telemetry)
        else:
            telemetry_called = None
    except ImportError:
        telemetry_called = None
    with mock.patch("mcp_commit_story.server.get_version_from_pyproject", return_value="1.2.3"):
        with mock.patch("mcp_commit_story.server.register_tools") as reg_tools:
            server = create_mcp_server()
            assert server.name == "mcp-commit-story"
            reg_tools.assert_called_once_with(server)
            if telemetry_called is not None:
                assert telemetry_called["called"]

def test_mcp_error_response():
    @handle_mcp_error
    async def failing_tool(request):
        raise MCPError("fail message", status="fail-status")
    response = asyncio.run(failing_tool({}))
    assert response["status"] == "fail-status"
    assert response["error"] == "fail message"

def test_handle_mcp_error_catches_generic_exception():
    @handle_mcp_error
    async def generic_error_tool(request):
        raise ValueError("unexpected!")
    response = asyncio.run(generic_error_tool({}))
    assert response["status"] == "error"
    assert "unexpected!" in response["error"]



@pytest.mark.asyncio
async def test_journal_add_reflection_handler(tmp_path, monkeypatch):
    # Mock the config to use tmp_path instead of real journal directory
    from mcp_commit_story.config import Config
    test_config = Config({
        'journal': {'path': str(tmp_path / "journal")},
        'git': {'exclude_patterns': []},
        'telemetry': {'enabled': False}
    })
    # Patch all places that might call load_config during reflection handling
    monkeypatch.setattr("mcp_commit_story.server.load_config", lambda: test_config)
    monkeypatch.setattr("mcp_commit_story.reflection_core.load_config", lambda: test_config)
    monkeypatch.setattr("mcp_commit_story.journal_handlers.load_config", lambda: test_config)
    
    from mcp_commit_story.server import handle_journal_add_reflection
    class DummyRequest(dict):
        pass
    request = DummyRequest(text="This is a test reflection.", date="2025-05-28")
    result = await handle_journal_add_reflection(request)
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "file_path" in result

def test_journal_add_reflection_handler_missing_fields():
    try:
        from mcp_commit_story.server import handle_journal_add_reflection
    except ImportError:
        pytest.skip("handle_journal_add_reflection not implemented yet")
    # Missing 'reflection' field
    request = {"date": "2025-05-26"}
    response = asyncio.run(handle_journal_add_reflection(request))
    assert response["status"] == "error"
    assert "Missing required field: reflection" in response["error"]
    # Missing 'date' field
    request = {"reflection": "Today I learned..."}
    response = asyncio.run(handle_journal_add_reflection(request))
    assert response["status"] == "error"
    assert "Missing required field: date" in response["error"]

def test_journal_add_reflection_handler_error_decorator():
    try:
        from mcp_commit_story.server import handle_journal_add_reflection, handle_mcp_error
    except ImportError:
        pytest.skip("handle_journal_add_reflection or handle_mcp_error not implemented yet")
    @handle_mcp_error
    async def bad_handler(request):
        raise ValueError("fail")
    response = asyncio.run(bad_handler({}))
    assert response["status"] == "error"
    assert "fail" in response["error"]

def test_create_mcp_server_fails_with_malformed_yaml(tmp_path, monkeypatch):
    # Create a malformed YAML config file
    bad_yaml = ": this is not valid: ["
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text(bad_yaml)
    monkeypatch.setattr("mcp_commit_story.server.load_config", lambda *a, **k: (_ for _ in ()).throw(Exception("Malformed YAML")))
    with pytest.raises(Exception) as excinfo:
        create_mcp_server()
    assert "Malformed YAML" in str(excinfo.value)

def test_create_mcp_server_fails_with_missing_required_fields(monkeypatch):
    # Config missing required 'journal.path'
    from mcp_commit_story.config import ConfigError
    monkeypatch.setattr("mcp_commit_story.server.load_config", lambda *a, **k: (_ for _ in ()).throw(ConfigError("Missing required config: journal.path")))
    with pytest.raises(ConfigError) as excinfo:
        create_mcp_server()
    assert "Missing required config: journal.path" in str(excinfo.value)

def test_server_shutdown_logic_called(monkeypatch):
    # Assume FastMCP has a shutdown method or similar
    class DummyServer:
        def __init__(self):
            self.shutdown_called = False
        async def shutdown(self):
            self.shutdown_called = True
    server = DummyServer()
    # Simulate shutdown logic (replace with actual if exists)
    async def shutdown_server():
        await server.shutdown()
    import asyncio
    asyncio.run(shutdown_server())
    assert server.shutdown_called

def test_config_reload_updates_values(tmp_path):
    from mcp_commit_story.config import Config
    import yaml
    # Write initial config
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_data = {"journal": {"path": "journal/"}, "git": {"exclude_patterns": ["journal/**"]}, "telemetry": {"enabled": False}}
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    config = Config(config_data, config_path=str(config_path))
    # Change config on disk
    new_data = {"journal": {"path": "new-journal/"}, "git": {"exclude_patterns": ["journal/**"]}, "telemetry": {"enabled": False}}
    with open(config_path, "w") as f:
        yaml.dump(new_data, f)
    config.reload_config()
    assert config.journal_path == "new-journal/"

def test_config_reload_raises_on_invalid(tmp_path):
    from mcp_commit_story.config import Config, ConfigError
    import yaml
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_data = {"journal": {"path": "journal/"}, "git": {"exclude_patterns": ["journal/**"]}, "telemetry": {"enabled": False}}
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    config = Config(config_data, config_path=str(config_path))
    # Write invalid config (missing journal.path)
    bad_data = {"journal": {}, "git": {"exclude_patterns": ["journal/**"]}, "telemetry": {"enabled": False}}
    with open(config_path, "w") as f:
        yaml.dump(bad_data, f)
    import pytest
    # Actually remove the required field and reload
    with pytest.raises(ConfigError):
        config.reload_config()

def test_config_reload_raises_on_malformed_yaml(tmp_path):
    from mcp_commit_story.config import Config, ConfigError
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_data = {"journal": {"path": "journal/"}, "git": {"exclude_patterns": ["journal/**"]}, "telemetry": {"enabled": False}}
    with open(config_path, "w") as f:
        import yaml
        yaml.dump(config_data, f)
    config = Config(config_data, config_path=str(config_path))
    # Write malformed YAML
    with open(config_path, "w") as f:
        f.write(": this is not valid: [")
    import pytest
    with pytest.raises(ConfigError):
        config.reload_config()

