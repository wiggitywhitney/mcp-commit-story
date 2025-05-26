import pytest
from unittest import mock
from src.mcp_commit_story.server import create_mcp_server, get_version_from_pyproject, register_tools
from mcp.server.fastmcp import FastMCP
from mcp_commit_story.config import Config
import logging

@pytest.mark.asyncio
def test_create_mcp_server_sets_name_and_calls_register_tools(tmp_path):
    # Patch pyproject.toml to a temp file with known version
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "mcp-commit-story"
version = "9.9.9"
""")
    with mock.patch("src.mcp_commit_story.server.get_version_from_pyproject", wraps=get_version_from_pyproject) as get_ver:
        version = get_version_from_pyproject(str(pyproject))
        assert version == "9.9.9"
        # Patch get_version_from_pyproject to use our temp file
        with mock.patch("src.mcp_commit_story.server.get_version_from_pyproject", return_value="9.9.9") as ver_patch:
            with mock.patch("src.mcp_commit_story.server.load_config", return_value=Config({})):
                with mock.patch("src.mcp_commit_story.server.register_tools") as reg_tools:
                    server = create_mcp_server()
                    assert server.name == "mcp-commit-story"
                    reg_tools.assert_called_once_with(server)
            ver_patch.assert_called()

@pytest.mark.asyncio
def test_create_mcp_server_loads_config_and_telemetry(monkeypatch):
    # Patch load_config to return a config with telemetry enabled
    config = Config({"telemetry": {"enabled": True}})
    monkeypatch.setattr("src.mcp_commit_story.server.load_config", lambda: config)
    # If setup_telemetry exists, patch it; otherwise, just run
    try:
        import src.mcp_commit_story.server as server_mod
        if hasattr(server_mod.telemetry, "setup_telemetry"):
            telemetry_called = {}
            def fake_setup_telemetry(cfg):
                telemetry_called["called"] = True
            monkeypatch.setattr(server_mod.telemetry, "setup_telemetry", fake_setup_telemetry)
        else:
            telemetry_called = None
    except ImportError:
        telemetry_called = None
    with mock.patch("src.mcp_commit_story.server.get_version_from_pyproject", return_value="1.2.3"):
        with mock.patch("src.mcp_commit_story.server.register_tools") as reg_tools:
            server = create_mcp_server()
            assert server.name == "mcp-commit-story"
            reg_tools.assert_called_once_with(server)
            if telemetry_called is not None:
                assert telemetry_called["called"] 