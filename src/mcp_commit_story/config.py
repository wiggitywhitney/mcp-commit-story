"""
Configuration module for MCP Journal.

This module provides the Config class and helper functions for loading/saving configuration.
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import yaml

# Default configuration
DEFAULT_CONFIG = {
    'journal': {
        'path': 'journal/',
        'auto_generate': True,
        'include_terminal': True,
        'include_chat': True,
        'include_mood': True,
        'auto_summarize': {
            'daily': True,
            'weekly': True,
            'monthly': True,
            'yearly': True
        }
    },
    'git': {
        'exclude_patterns': ['journal/**', '.mcp-commit-storyrc.yaml']
    },
    'telemetry': {
        'enabled': False,
        'service_name': 'mcp-commit-story'
    }
}

class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass

class Config:
    """
    Configuration class for MCP Journal.
    Handles loading, validation, and access to configuration settings with
    sensible defaults focused on essential functionality.
    Now supports dict-like access for compatibility with tests and legacy code.

    New in 6.5:
    - Hot config reload: call reload_config() to reload from disk and re-validate.
    - Stricter config validation: all required fields must be present and valid, or ConfigError is raised immediately.
    """
    def __init__(self, config_data: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        self._config_path = config_path
        config_data = config_data or {}
        # Strict validation: validate raw config_data before merging with defaults
        validate_config(config_data)
        import copy
        base = copy.deepcopy(DEFAULT_CONFIG)
        merged = merge_configs(base, config_data)
        # Type checks and population for journal
        journal = merged.get('journal', {})
        if not isinstance(journal, dict):
            raise ConfigError("'journal' section must be a dict")
        if 'path' in journal and not isinstance(journal['path'], str):
            raise ConfigError("'journal.path' must be a string")
        self._journal = {**base['journal'], **journal}
        self._journal_path = self._journal['path']
        # Type checks and population for git
        git = merged.get('git', {})
        if not isinstance(git, dict):
            raise ConfigError("'git' section must be a dict")
        if 'exclude_patterns' in git and not isinstance(git['exclude_patterns'], list):
            raise ConfigError("'git.exclude_patterns' must be a list")
        self._git = {**base['git'], **git}
        self._git_exclude_patterns = self._git['exclude_patterns']
        # Type checks and population for telemetry
        telemetry = merged.get('telemetry', {})
        if not isinstance(telemetry, dict):
            raise ConfigError("'telemetry' section must be a dict")
        if 'enabled' in telemetry and not isinstance(telemetry['enabled'], bool):
            raise ConfigError("'telemetry.enabled' must be a boolean")
        self._telemetry = {**base['telemetry'], **telemetry}
        self._telemetry_enabled = self._telemetry['enabled']
        # Store the full config for dict-like access
        self._config_dict = {
            'journal': self._journal,
            'git': self._git,
            'telemetry': self._telemetry
        }

    @property
    def journal_path(self) -> str:
        """Get the journal files path."""
        return self._journal_path
    @journal_path.setter
    def journal_path(self, value: str):
        if not isinstance(value, str):
            raise ConfigError("Journal path must be a string")
        self._journal_path = value
        self._journal['path'] = value
    @property
    def git_exclude_patterns(self) -> List[str]:
        """Get patterns to exclude from git processing."""
        return self._git_exclude_patterns
    @git_exclude_patterns.setter
    def git_exclude_patterns(self, value: List[str]):
        if not isinstance(value, list):
            raise ConfigError("Git exclude patterns must be a list")
        self._git_exclude_patterns = value
        self._git['exclude_patterns'] = value
    @property
    def telemetry_enabled(self) -> bool:
        """Get whether telemetry is enabled."""
        return self._telemetry_enabled
    @telemetry_enabled.setter
    def telemetry_enabled(self, value: bool):
        if not isinstance(value, bool):
            raise ConfigError("Telemetry enabled must be a boolean")
        self._telemetry_enabled = value
        self._telemetry['enabled'] = value
    def as_dict(self) -> Dict[str, Any]:
        """Convert config to a dictionary, always including all defaults."""
        import copy
        d = copy.deepcopy(DEFAULT_CONFIG)
        d['journal'].update(self._journal)
        d['git'].update(self._git)
        d['telemetry'].update(self._telemetry)
        return d
    def to_dict(self) -> Dict[str, Any]:
        """Alias for as_dict for compatibility."""
        return self.as_dict()
    def __getitem__(self, key):
        return self._config_dict[key]
    def __contains__(self, key):
        return key in self._config_dict
    # For deep access in get_config_value
    def get(self, key, default=None):
        return self._config_dict.get(key, default)

    def reload_config(self):
        """
        Reload configuration from disk and re-validate. Raises ConfigError on any missing/invalid field.
        """
        if not self._config_path:
            raise ConfigError("No config_path set for reload.")
        import yaml
        try:
            with open(self._config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Malformed YAML in config file {self._config_path}: {e}")
        except Exception as e:
            raise ConfigError(f"Error loading config from {self._config_path}: {e}")
        # Strict validation before merging with defaults
        validate_config(config_data)
        # Re-init with new data
        self.__init__(config_data, config_path=self._config_path)

def get_config_value(config: Any, key_path: str, default: Any = None) -> Any:
    """
    Get a configuration value by dot-separated key path.
    Supports both dict and Config objects.
    """
    keys = key_path.split('.')
    result = config
    for key in keys:
        if isinstance(result, Config):
            result = result._config_dict
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default
    return result

def find_config_files() -> Tuple[Optional[str], Optional[str]]:
    """
    Find local and global configuration files.
    
    Returns:
        Tuple of (local_config_path, global_config_path), either may be None if not found
    """
    # Get local config path and check if it exists
    local_config_path = os.path.join(os.getcwd(), '.mcp-commit-storyrc.yaml')
    local_exists = os.path.exists(local_config_path)
    local_config = local_config_path if local_exists else None
    
    # Get global config path and check if it exists
    global_config_path = os.path.expanduser('~/.mcp-commit-storyrc.yaml')
    global_exists = os.path.exists(global_config_path)
    global_config = global_config_path if global_exists else None
    
    return local_config, global_config

def merge_configs(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries with deep merging.
    
    Args:
        base: Base configuration
        overlay: Configuration to overlay (takes precedence)
        
    Returns:
        Merged configuration dictionary
    """
    result = base.copy()
    
    for key, value in overlay.items():
        if (
            key in result and 
            isinstance(result[key], dict) and 
            isinstance(value, dict)
        ):
            # Recursively merge nested dicts
            result[key] = merge_configs(result[key], value)
        else:
            # Replace or add values
            result[key] = value
            
    return result

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate configuration and apply defaults for missing values.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Validated configuration with defaults applied
        
    Raises:
        ConfigError: If configuration is invalid
    """
    # Required fields and their types
    validations = {
        'journal.path': (str, 'Journal path is required and must be a string'),
        'git.exclude_patterns': (list, 'Git exclude patterns must be a list'),
        'telemetry.enabled': (bool, 'Telemetry enabled flag must be a boolean')
    }
    
    # Check each required field
    for key_path, (expected_type, error_msg) in validations.items():
        value = get_config_value(config, key_path)
        if value is None:
            raise ConfigError(f"Missing required config: {key_path}")
        if not isinstance(value, expected_type):
            raise ConfigError(f"{error_msg} (got {type(value).__name__})")
    
    return config

def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from a file with proper precedence.
    Always returns a Config object.
    Raises ConfigError on malformed YAML or invalid types.
    """
    import copy
    config_data = copy.deepcopy(DEFAULT_CONFIG)
    def _load_yaml(path):
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Malformed YAML in config file {path}: {e}")
        except Exception as e:
            print(f"Error loading config from {path}: {e}")
            return {}
    if config_path is None:
        local_path, global_path = find_config_files()
        local_data = _load_yaml(local_path) if local_path else {}
        global_data = _load_yaml(global_path) if global_path else {}
        if global_data:
            config_data = merge_configs(config_data, global_data)
        if local_data:
            config_data = merge_configs(config_data, local_data)
    elif config_path and os.path.exists(config_path):
        file_data = _load_yaml(config_path)
        config_data = merge_configs(config_data, file_data)
    # If config_data is empty (e.g., empty file), use defaults
    if not config_data:
        config_data = copy.deepcopy(DEFAULT_CONFIG)
    # Validate config, apply defaults for missing fields (handled in Config)
    return Config(config_data)

def save_config(config: Config, config_path: Optional[str] = None) -> bool:
    """
    Save configuration to a file.
    
    Args:
        config: Config object to save
        config_path: Path to save config file, defaults to .mcp-commit-storyrc.yaml in current directory
        
    Returns:
        True if successful, False otherwise
    """
    if config_path is None:
        config_path = os.path.join(os.getcwd(), '.mcp-commit-storyrc.yaml')
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(config.as_dict(), f, default_flow_style=False)
        return True
    except Exception as e:
        # Log error
        print(f"Error saving config: {e}")
        return False
