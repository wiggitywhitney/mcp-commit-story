import pytest
import os
import tempfile
from pathlib import Path
import yaml
from unittest.mock import patch, mock_open
from mcp_commit_story.config import (
    Config, 
    ConfigError,
    load_config, 
    save_config, 
    get_config_value,
    find_config_files,
    merge_configs,
    validate_config,
    DEFAULT_CONFIG
)
import inspect

def test_config_defaults():
    """Test config object has correct defaults"""
    config_data = {
        'journal': {'path': 'journal/'},
        'git': {'exclude_patterns': ['*.log', 'journal/']},
        'telemetry': {'enabled': True}
    }
    config = Config(config_data)
    assert isinstance(config.journal_path, str)
    assert len(config.journal_path) > 0
    assert isinstance(config.git_exclude_patterns, list)
    assert len(config.git_exclude_patterns) > 0
    assert isinstance(config.telemetry_enabled, bool)

def test_config_custom_values():
    """Test config accepts custom values"""
    custom_config = {
        'journal': {'path': '/custom/journal'},
        'git': {'exclude_patterns': ['*.log', 'journal/']},
        'telemetry': {'enabled': False}
    }
    
    config = Config(custom_config)
    assert config.journal_path == '/custom/journal'
    assert '*.log' in config.git_exclude_patterns
    assert 'journal/' in config.git_exclude_patterns
    assert config.telemetry_enabled is False

def test_config_as_dict():
    """Test config can be converted to dictionary"""
    config_data = {
        'journal': {'path': 'journal/'},
        'git': {'exclude_patterns': ['*.log', 'journal/']},
        'telemetry': {'enabled': True}
    }
    config = Config(config_data)
    config_dict = config.as_dict()
    
    assert isinstance(config_dict, dict)
    assert 'journal' in config_dict
    assert 'path' in config_dict['journal']
    assert 'git' in config_dict
    assert 'exclude_patterns' in config_dict['git']
    assert 'telemetry' in config_dict
    assert 'enabled' in config_dict['telemetry']

def test_load_config(tmp_path):
    """Test loading config from file"""
    # Create a test config file
    config_path = tmp_path / '.mcp-commit-storyrc.yaml'
    test_config = {
        'journal': {'path': 'test_journal/'},
        'git': {'exclude_patterns': ['test/*.log']},
        'telemetry': {'enabled': True}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(test_config, f)
    
    # Load the config
    config = load_config(config_path)
    
    assert config.journal_path == 'test_journal/'
    assert 'test/*.log' in config.git_exclude_patterns
    assert config.telemetry_enabled is True

def test_load_config_missing_file():
    """Test loading config with missing file falls back to defaults"""
    config = load_config('/path/does/not/exist')
    assert config is not None
    assert isinstance(config, Config)

def test_save_config(tmp_path):
    """Test saving config to file"""
    config_path = tmp_path / '.mcp-commit-storyrc.yaml'
    config_data = {
        'journal': {'path': 'saved_journal/'},
        'git': {'exclude_patterns': ['saved/*.log']},
        'telemetry': {'enabled': False}
    }
    config = Config(config_data)
    save_config(config, config_path)
    # Verify file was created
    assert config_path.exists()
    # Verify content
    with open(config_path, 'r') as f:
        loaded_yaml = yaml.safe_load(f)
    assert loaded_yaml['journal']['path'] == 'saved_journal/'
    assert 'saved/*.log' in loaded_yaml['git']['exclude_patterns']
    assert loaded_yaml['telemetry']['enabled'] is False

def test_nested_config_access():
    """Test accessing nested configuration values using dot notation"""
    config_data = {
        'journal': {
            'path': 'test_journal/',
            'nested': {
                'value': 42,
                'deep': {
                    'list': [1, 2, 3]
                }
            }
        }
    }
    
    assert get_config_value(config_data, 'journal.path') == 'test_journal/'
    assert get_config_value(config_data, 'journal.nested.value') == 42
    assert get_config_value(config_data, 'journal.nested.deep.list')[0] == 1
    assert get_config_value(config_data, 'nonexistent') is None
    assert get_config_value(config_data, 'nonexistent', 'default') == 'default'

def test_find_config_files():
    """Test finding config files in different locations"""
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.expanduser') as mock_expanduser:
        
        # Mock paths
        mock_expanduser.return_value = '/home/user/.mcp-commit-storyrc.yaml'
        local_path = os.path.join(os.getcwd(), '.mcp-commit-storyrc.yaml')
        
        # Case 1: Local and global exist
        mock_exists.return_value = True
        
        local, global_path = find_config_files()
        assert local == local_path
        assert global_path == '/home/user/.mcp-commit-storyrc.yaml'
        
        # Case 2: Only local exists
        def exists_side_effect(path):
            # Only return False for the exact global config path
            if path == '/home/user/.mcp-commit-storyrc.yaml':
                return False  # Global config does not exist
            return True  # Local config exists
        mock_exists.side_effect = exists_side_effect
        
        local, global_path = find_config_files()
        assert local == local_path
        assert global_path is None
        
        # Case 3: Only global exists
        def exists_side_effect2(path):
            # Only return True for the exact global config path
            if path == '/home/user/.mcp-commit-storyrc.yaml':
                return True  # Global config exists
            return False  # Local config does not exist
        mock_exists.side_effect = exists_side_effect2
        
        local, global_path = find_config_files()
        assert local is None
        assert global_path == '/home/user/.mcp-commit-storyrc.yaml'
        
        # Case 4: No configs exist - reset the mock
        mock_exists.side_effect = None
        mock_exists.return_value = False
        
        local, global_path = find_config_files()
        assert local is None
        assert global_path is None

def test_merge_configs():
    """Test merging configurations from different sources with proper precedence"""
    base = {
        'journal': {
            'path': 'base/',
            'nested': {
                'value': 1,
                'list': [1, 2, 3]
            }
        },
        'base_only': True
    }
    
    overlay = {
        'journal': {
            'path': 'overlay/',
            'nested': {
                'value': 2
            }
        },
        'overlay_only': True
    }
    
    # Merge configs
    result = merge_configs(base, overlay)
    
    # Overlay values should override base values
    assert result['journal']['path'] == 'overlay/'
    assert result['journal']['nested']['value'] == 2
    
    # Base values not in overlay should be preserved
    assert 'list' in result['journal']['nested']
    assert result['journal']['nested']['list'] == [1, 2, 3]
    assert 'base_only' in result
    
    # Overlay-only values should be added
    assert 'overlay_only' in result

def test_load_config_with_precedence():
    """Test loading config with proper precedence: local > global > defaults"""
    default_config = {
        'journal': {'path': 'default_journal/'},
        'git': {'exclude_patterns': ['default/*.log']},
        'telemetry': {'enabled': True}
    }
    
    global_config = {
        'journal': {'path': 'global_journal/'},
        'git': {'exclude_patterns': ['global/*.log']},
    }
    
    local_config = {
        'journal': {'path': 'local_journal/'},
    }
    
    # Mock the config file finding and loading
    with patch('mcp_commit_story.config.find_config_files') as mock_find, \
         patch('mcp_commit_story.config.yaml.safe_load') as mock_load, \
         patch('mcp_commit_story.config.DEFAULT_CONFIG', default_config), \
         patch('builtins.open', mock_open()):
        
        # Case 1: Local and global exist
        mock_find.return_value = ('local_path', 'global_path')
        mock_load.side_effect = [local_config, global_config]
        
        config = load_config()
        
        # Local should override global and default
        assert config.journal_path == 'local_journal/'
        # Global should override default when local doesn't specify
        assert config.git_exclude_patterns == ['global/*.log']
        # Default should be used when neither local nor global specify
        assert config.telemetry_enabled is True
        
        # Case 2: Only global exists
        mock_find.return_value = (None, 'global_path')
        mock_load.side_effect = [global_config]
        
        config = load_config()
        
        # Global should override default
        assert config.journal_path == 'global_journal/'
        assert config.git_exclude_patterns == ['global/*.log']
        # Default should be used when global doesn't specify
        assert config.telemetry_enabled is True
        
        # Case 3: Only local exists
        mock_find.return_value = ('local_path', None)
        mock_load.side_effect = [local_config]
        
        config = load_config()
        
        # Local should override default
        assert config.journal_path == 'local_journal/'
        # Default should be used when local doesn't specify
        assert config.git_exclude_patterns == ['default/*.log']
        assert config.telemetry_enabled is True
        
        # Case 4: No configs exist
        mock_find.return_value = (None, None)
        
        config = load_config()
        
        # Default values should be used
        assert config.journal_path == 'default_journal/'
        assert config.git_exclude_patterns == ['default/*.log']
        assert config.telemetry_enabled is True

def test_validate_config():
    """Test configuration validation"""
    # Valid config
    valid_config = {
        'journal': {'path': 'journal/'},
        'git': {'exclude_patterns': ['*.log']},
        'telemetry': {'enabled': True}
    }
    
    assert validate_config(valid_config) == valid_config
    
    # Missing required field
    invalid_config = {
        'journal': {},  # Missing 'path'
        'git': {'exclude_patterns': ['*.log']},
        'telemetry': {'enabled': True}
    }
    
    with pytest.raises(ConfigError):
        validate_config(invalid_config)
    
    # Invalid type
    invalid_type_config = {
        'journal': {'path': 123},  # Should be string
        'git': {'exclude_patterns': ['*.log']},
        'telemetry': {'enabled': True}
    }
    
    with pytest.raises(ConfigError):
        validate_config(invalid_type_config)

def test_handle_malformed_yaml():
    """Test handling of malformed YAML configuration files"""
    with patch('builtins.open', mock_open(read_data='invalid: yaml: content')), \
         patch('yaml.safe_load') as mock_load:
        
        # Simulate YAML parsing error
        mock_load.side_effect = yaml.YAMLError("Test YAML Error")
        
        # Should fall back to defaults instead of crashing
        config = load_config('some_path')
        
        assert config is not None
        assert isinstance(config, Config)
        # Should use default values
        assert config.journal_path == 'journal/'

# ---
# Additional TDD tests for subtask 2.11: Final review and optimization

def test_load_large_config_file(tmp_path):
    """Test loading a very large config file."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    with open(config_path, "w") as f:
        f.write("journal:\n")
        for i in range(1000):
            f.write(f"  key{i}: value{i}\n")
    config = load_config(str(config_path))
    assert config["journal"]["key999"] == "value999"

def test_repeated_load_config_is_consistent(tmp_path):
    """Test repeated calls to load_config return consistent results."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal:\n  path: journal/")
    config1 = load_config(str(config_path))
    config2 = load_config(str(config_path))
    assert config1.as_dict() == config2.as_dict()

def test_malformed_yaml_raises_error(tmp_path):
    """Test that malformed YAML raises a ConfigError."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal: [unclosed_list\n")
    with pytest.raises(ConfigError):
        load_config(str(config_path))

def test_missing_required_fields(tmp_path):
    """Test that missing required fields are handled (defaults applied or error raised)."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal: {}\n")
    config = load_config(str(config_path))
    assert "path" in config["journal"]

def test_unexpected_data_type(tmp_path):
    """Test that unexpected data types raise a ConfigError."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal: 123\n")
    with pytest.raises(ConfigError):
        load_config(str(config_path))

def test_deeply_nested_config_access(tmp_path):
    """Test access to deeply nested config keys."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal:\n  auto_summarize:\n    yearly: false\n")
    config = load_config(str(config_path))
    assert get_config_value(config, "journal.auto_summarize.yearly") is False

def test_empty_config_file(tmp_path):
    """Test that an empty config file loads as a valid config object."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("")
    config = load_config(str(config_path))
    assert isinstance(config, Config)

def test_docstrings_and_usage_examples():
    """Test that all public functions in config module have docstrings."""
    import mcp_commit_story.config as config_mod
    for name, obj in inspect.getmembers(config_mod):
        if inspect.isfunction(obj) and not name.startswith("_"):
            assert obj.__doc__ is not None and len(obj.__doc__) > 0 

def test_config_hot_reload(tmp_path):
    """Test config hot reload functionality."""
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("""
journal:
  path: original/
git:
  exclude_patterns:
    - '*.log'
telemetry:
  enabled: true
""")
    config = load_config(str(config_path))
    assert config.journal_path == "original/"
    # Modify file
    config_path.write_text("""
journal:
  path: updated/
git:
  exclude_patterns:
    - '*.log'
telemetry:
  enabled: true
""")
    config.reload_config()
    assert config.journal_path == "updated/"

def test_config_dict_like_access():
    """Test that Config supports dict-like access."""
    config_data = {
        'journal': {'path': 'test/'},
        'git': {'exclude_patterns': ['*.log']},
        'telemetry': {'enabled': True}
    }
    config = Config(config_data)
    assert config['journal']['path'] == 'test/'
    assert 'journal' in config
    assert 'nonexistent' not in config 