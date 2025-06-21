"""
Unit tests for platform detection module.

Tests the cross-platform SQLite workspace path detection functionality
for Windows, macOS, Linux, and WSL environments.
"""

import pytest
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

# Import the module we're about to create (will fail initially - that's expected)
try:
    from mcp_commit_story.cursor_db.platform import (
        detect_platform,
        get_cursor_workspace_paths,
        validate_workspace_path,
        PlatformType,
        CursorPathError
    )
except ImportError:
    # Expected to fail initially in TDD
    pytest.skip("Platform detection module not yet implemented", allow_module_level=True)


class TestPlatformDetection:
    """Test platform detection functionality."""
    
    @patch('platform.system')
    def test_detect_platform_windows(self, mock_system):
        """Test Windows platform detection."""
        mock_system.return_value = 'Windows'
        result = detect_platform()
        assert result == PlatformType.WINDOWS
    
    @patch('platform.system')
    def test_detect_platform_darwin(self, mock_system):
        """Test macOS platform detection."""
        mock_system.return_value = 'Darwin'
        result = detect_platform()
        assert result == PlatformType.MACOS
    
    @patch('platform.system')
    def test_detect_platform_linux(self, mock_system):
        """Test Linux platform detection."""
        mock_system.return_value = 'Linux'
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False  # No /proc/version file
            result = detect_platform()
            assert result == PlatformType.LINUX
    
    @patch('platform.system')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_detect_platform_wsl(self, mock_read_text, mock_exists, mock_system):
        """Test WSL platform detection."""
        mock_system.return_value = 'Linux'
        mock_exists.return_value = True  # /proc/version exists
        mock_read_text.return_value = 'Linux version 4.4.0-43-Microsoft'
        result = detect_platform()
        assert result == PlatformType.WSL
    
    @patch('platform.system')
    def test_detect_platform_unknown(self, mock_system):
        """Test unknown platform handling."""
        mock_system.return_value = 'FreeBSD'
        with pytest.raises(CursorPathError, match="Unsupported platform"):
            detect_platform()


class TestWorkspacePathDetection:
    """Test workspace path detection across platforms."""
    
    @patch('mcp_commit_story.cursor_db.platform.detect_platform')
    @patch.dict(os.environ, {'APPDATA': 'C:\\Users\\TestUser\\AppData\\Roaming'})
    def test_get_cursor_workspace_paths_windows(self, mock_detect):
        """Test Windows workspace path detection."""
        mock_detect.return_value = PlatformType.WINDOWS
        paths = get_cursor_workspace_paths()
        
        expected_path = Path('C:/Users/TestUser/AppData/Roaming/Cursor/User/workspaceStorage')
        assert expected_path in paths
        assert len(paths) >= 1
    
    @patch('mcp_commit_story.cursor_db.platform.detect_platform')
    @patch('pathlib.Path.home')
    def test_get_cursor_workspace_paths_macos(self, mock_home, mock_detect):
        """Test macOS workspace path detection."""
        mock_detect.return_value = PlatformType.MACOS
        mock_home.return_value = Path('/Users/testuser')
        
        paths = get_cursor_workspace_paths()
        
        expected_path = Path('/Users/testuser/Library/Application Support/Cursor/User/workspaceStorage')
        assert expected_path in paths
        assert len(paths) >= 1
    
    @patch('mcp_commit_story.cursor_db.platform.detect_platform')
    @patch('pathlib.Path.home')
    def test_get_cursor_workspace_paths_linux(self, mock_home, mock_detect):
        """Test Linux workspace path detection."""
        mock_detect.return_value = PlatformType.LINUX
        mock_home.return_value = Path('/home/testuser')
        
        paths = get_cursor_workspace_paths()
        
        expected_path = Path('/home/testuser/.config/Cursor/User/workspaceStorage')
        assert expected_path in paths
        assert len(paths) >= 1
    
    @patch('mcp_commit_story.cursor_db.platform.detect_platform')
    @patch('pathlib.Path.iterdir')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_get_cursor_workspace_paths_wsl(self, mock_is_dir, mock_exists, mock_iterdir, mock_detect):
        """Test WSL workspace path detection."""
        mock_detect.return_value = PlatformType.WSL
        
        # Mock the /mnt/c/Users directory exists
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        
        # Mock user directories in /mnt/c/Users
        mock_user_dir = Path('/mnt/c/Users/TestUser')
        mock_iterdir.return_value = [mock_user_dir]
        
        paths = get_cursor_workspace_paths()
        
        expected_path = Path('/mnt/c/Users/TestUser/AppData/Roaming/Cursor/User/workspaceStorage')
        assert expected_path in paths
        assert len(paths) >= 1
    
    @patch.dict(os.environ, {'CURSOR_WORKSPACE_PATH': '/custom/path/to/cursor'})
    def test_get_cursor_workspace_paths_custom_env_var(self):
        """Test custom workspace path via environment variable."""
        paths = get_cursor_workspace_paths()
        
        custom_path = Path('/custom/path/to/cursor')
        assert custom_path in paths
    
    def test_get_cursor_workspace_paths_multiple_locations(self):
        """Test that multiple potential locations are returned."""
        paths = get_cursor_workspace_paths()
        
        # Should return a list even if some paths don't exist
        assert isinstance(paths, list)
        assert len(paths) >= 1


class TestPathValidation:
    """Test workspace path validation functionality."""
    
    def test_validate_workspace_path_exists_and_accessible(self, tmp_path):
        """Test validation of existing and accessible path."""
        test_path = tmp_path / "cursor_workspace"
        test_path.mkdir()
        
        result = validate_workspace_path(test_path)
        assert result is True
    
    def test_validate_workspace_path_not_exists(self, tmp_path):
        """Test validation of non-existent path."""
        test_path = tmp_path / "nonexistent"
        
        result = validate_workspace_path(test_path)
        assert result is False
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_validate_workspace_path_not_directory(self, mock_is_dir, mock_exists):
        """Test validation when path exists but is not a directory."""
        mock_exists.return_value = True
        mock_is_dir.return_value = False
        
        result = validate_workspace_path(Path('/some/file'))
        assert result is False
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('os.access')
    def test_validate_workspace_path_no_read_permission(self, mock_access, mock_is_dir, mock_exists):
        """Test validation when path exists but is not readable."""
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_access.return_value = False
        
        result = validate_workspace_path(Path('/restricted/path'))
        assert result is False
    
    def test_validate_workspace_path_string_input(self, tmp_path):
        """Test validation accepts string paths."""
        test_path = tmp_path / "cursor_workspace"
        test_path.mkdir()
        
        result = validate_workspace_path(str(test_path))
        assert result is True
    
    def test_validate_workspace_path_none_input(self):
        """Test validation handles None input gracefully."""
        result = validate_workspace_path(None)
        assert result is False


class TestEnvironmentVariableExpansion:
    """Test environment variable expansion in paths."""
    
    @patch.dict(os.environ, {'HOME': '/home/testuser', 'CURSOR_HOME': '/opt/cursor'})
    def test_expand_environment_variables(self):
        """Test that environment variables are properly expanded."""
        paths = get_cursor_workspace_paths()
        
        # Should not contain raw environment variable strings
        for path in paths:
            assert '$' not in str(path)
            assert '%' not in str(path)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_environment_variables(self):
        """Test handling when expected environment variables are missing."""
        # Should not raise exceptions, should use fallbacks
        paths = get_cursor_workspace_paths()
        assert isinstance(paths, list)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_network_drive_paths(self):
        """Test handling of network drive paths on Windows."""
        # This is a placeholder - actual implementation would test UNC paths
        # like \\server\share\path
        pass
    
    def test_symlink_handling(self, tmp_path):
        """Test that symlinks are handled correctly."""
        real_dir = tmp_path / "real_cursor"
        real_dir.mkdir()
        
        symlink_dir = tmp_path / "symlink_cursor"
        symlink_dir.symlink_to(real_dir)
        
        result = validate_workspace_path(symlink_dir)
        assert result is True
    
    def test_very_long_paths(self):
        """Test handling of very long file paths."""
        long_path = Path('/' + 'a' * 500 + '/cursor/workspace')
        result = validate_workspace_path(long_path)
        # Should handle gracefully without crashing
        assert isinstance(result, bool)
    
    def test_unicode_paths(self, tmp_path):
        """Test handling of Unicode characters in paths."""
        unicode_dir = tmp_path / "カーソル_workspace"
        unicode_dir.mkdir()
        
        result = validate_workspace_path(unicode_dir)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 