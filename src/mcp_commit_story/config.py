"""
Configuration module for MCP Journal.

This module provides the Config class and helper functions for loading/saving configuration.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import yaml
import logging

# Import telemetry for configuration instrumentation
from .telemetry import trace_config_operation, hash_sensitive_value, get_mcp_metrics

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'journal': {
        'path': 'journal/',
        'auto_generate': True,
        'include_terminal': True,
        'include_chat': True,
        'include_mood': True
    },
    'git': {
        'exclude_patterns': ['journal/**', '.mcp-commit-storyrc.yaml']
    },
    'ai': {
        'openai_api_key': ''
    },
    'telemetry': {
        'enabled': False,
        'service_name': 'mcp-commit-story',
        'service_version': '1.0.0',
        'deployment_environment': 'development',
        'exporters': {
            'console': {
                'enabled': True
            },
            'otlp': {
                'enabled': False
            }
        },
        'auto_instrumentation': {
            'enabled': True,
            'preset': 'minimal'
        }
    }
}

class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass

@trace_config_operation("env_interpolation") 
def resolve_env_vars(config_data: Any) -> Any:
    """
    Resolve environment variables in configuration data.
    
    Supports ${VAR_NAME} syntax for environment variable interpolation.
    Recursively processes nested dictionaries and lists.
    
    Args:
        config_data: Configuration data to process (str, dict, list, or other)
        
    Returns:
        Configuration data with environment variables resolved
        
    Raises:
        ConfigError: If environment variable is missing or syntax is invalid
    """
    metrics = get_mcp_metrics()
    
    try:
        if isinstance(config_data, str):
            result = _resolve_env_vars_in_string(config_data)
        elif isinstance(config_data, dict):
            result = {key: resolve_env_vars(value) for key, value in config_data.items()}
        elif isinstance(config_data, list):
            result = [resolve_env_vars(item) for item in config_data]
        else:
            # Non-string, non-dict, non-list values pass through unchanged
            result = config_data
        
        # Track successful interpolation (optional telemetry)
        if metrics:
            metrics.record_counter('config.env_interpolation_total', 1, {'status': 'success'})
        return result
    except ConfigError:
        # Track failed interpolation (optional telemetry)
        if metrics:
            metrics.record_counter('config.env_interpolation_total', 1, {'status': 'failure'})
        raise

def _resolve_env_vars_in_string(text: str) -> str:
    """
    Resolve environment variables in a string using ${VAR_NAME} syntax.
    
    Args:
        text: String that may contain environment variable references
        
    Returns:
        String with environment variables resolved
        
    Raises:
        ConfigError: If environment variable is missing or syntax is invalid
    """
    # Pattern to match ${VAR_NAME} where VAR_NAME contains only alphanumeric and underscore
    pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
    
    def replace_env_var(match):
        var_name = match.group(1)
        
        # Validate environment variable name
        if not var_name or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', var_name):
            raise ConfigError(f"Invalid environment variable syntax: ${{{var_name}}}")
        
        # Get environment variable value
        value = os.getenv(var_name)
        if value is None:
            raise ConfigError(f"Environment variable '{var_name}' not found")
        
        return value
    
    # Check for empty braces (special case)
    if '${' in text and text.count('${}') > 0:
        raise ConfigError("Invalid environment variable syntax: ${}")
    
    # Check for malformed ${...} patterns with invalid variable names
    if '${' in text:
        # Find all ${...} patterns
        all_var_pattern = r'\$\{([^}]+)\}'
        all_matches = re.findall(all_var_pattern, text)
        for var_name in all_matches:
            # Validate each variable name
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', var_name):
                raise ConfigError(f"Invalid environment variable syntax: ${{{var_name}}}")
    
    # Replace all valid environment variable references
    # The replace_env_var function handles validation of individual variable names
    try:
        result = re.sub(pattern, replace_env_var, text)
        return result
    except ConfigError:
        # Re-raise ConfigError without modification
        raise

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
        
        # Resolve environment variables before merging and validation
        config_data = resolve_env_vars(config_data)
        
        # Merge with defaults first, then validate the complete config
        import copy
        base = copy.deepcopy(DEFAULT_CONFIG)
        merged = merge_configs(base, config_data)
        
        # Strict validation: validate merged config with all required fields
        validate_config(merged)
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
        # Type checks and population for ai
        ai = merged.get('ai', {})
        if not isinstance(ai, dict):
            raise ConfigError("'ai' section must be a dict")
        if 'openai_api_key' in ai and not isinstance(ai['openai_api_key'], str):
            raise ConfigError("'ai.openai_api_key' must be a string")
        self._ai = {**base['ai'], **ai}
        self._ai_openai_api_key = self._ai['openai_api_key']
        
        # Validate AI configuration after environment variable resolution
        self._validate_ai_config()
        
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
            'ai': self._ai,
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
    def ai_openai_api_key(self) -> str:
        """Get the OpenAI API key."""
        return self._ai_openai_api_key
    @ai_openai_api_key.setter
    def ai_openai_api_key(self, value: str):
        if not isinstance(value, str):
            raise ConfigError("OpenAI API key must be a string")
        self._ai_openai_api_key = value
        self._ai['openai_api_key'] = value
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
        d['ai'].update(self._ai)
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

    @trace_config_operation("reload")
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

    def _validate_ai_config(self):
        """
        Validate AI configuration section with graceful degradation.
        
        Only validates when AI section is explicitly provided with non-empty values.
        Empty/missing AI config is allowed - AI features will fail gracefully at runtime.
        
        Raises:
            ConfigError: If AI configuration is explicitly provided but invalid
        """
        metrics = get_mcp_metrics()
        
        # Get the API key - may be empty string from defaults
        api_key = self._ai.get('openai_api_key', '')
        
        # Graceful degradation: allow empty/missing API keys
        # AI features will fail at runtime with clear warnings
        if not api_key or api_key.strip() == '':
            if metrics:
                metrics.record_counter('config.ai_validation_total', 1, {'status': 'success'})
            return
        
        try:
            # Only validate if API key is explicitly provided
            # Check for placeholder values
            placeholder_patterns = [
                'your-openai-api-key-here',
                'your_openai_api_key_here', 
                'placeholder',
                'change-me',
                'change_me'
            ]
            
            api_key_lower = api_key.lower().strip()
            for pattern in placeholder_patterns:
                if pattern in api_key_lower:
                    raise ConfigError(f"OpenAI API key appears to be a placeholder: '{api_key}'. Please set a valid API key.")
            
            # Track successful validation
            if metrics:
                metrics.record_counter('config.ai_validation_total', 1, {'status': 'success'})
                
        except ConfigError:
            # Track failed validation
            if metrics:
                metrics.record_counter('config.ai_validation_total', 1, {'status': 'failure'})
            raise

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

@trace_config_operation("validate")
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
    # Core required fields and their types (strict validation)
    required_validations = {
        'journal.path': (str, 'Journal path is required and must be a string'),
        'git.exclude_patterns': (list, 'Git exclude patterns must be a list'),
        'telemetry.enabled': (bool, 'Telemetry enabled flag must be a boolean')
    }
    
    # Check each core required field
    for key_path, (expected_type, error_msg) in required_validations.items():
        value = get_config_value(config, key_path)
        if value is None:
            raise ConfigError(f"Missing required config: {key_path}")
        if not isinstance(value, expected_type):
            raise ConfigError(f"{error_msg} (got {type(value).__name__})")
    
    # AI section: graceful degradation - only validate if present and non-empty
    api_key = get_config_value(config, 'ai.openai_api_key')
    if api_key is not None and not isinstance(api_key, str):
        raise ConfigError("'ai.openai_api_key' must be a string")
    
    return config

@trace_config_operation("load")
def load_config(config_path: Optional[str] = None) -> 'Config':
    """
    Load configuration from file or return default configuration.
    
    Args:
        config_path: Path to config file, or None for default search
        
    Returns:
        Config instance with loaded configuration
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
    config_file_used = None
    if config_path is None:
        local_path, global_path = find_config_files()
        local_data = _load_yaml(local_path) if local_path else {}
        global_data = _load_yaml(global_path) if global_path else {}
        if global_data:
            config_data = merge_configs(config_data, global_data)
            config_file_used = global_path
        if local_data:
            config_data = merge_configs(config_data, local_data)
            config_file_used = local_path
    elif config_path and os.path.exists(config_path):
        file_data = _load_yaml(config_path)
        config_data = merge_configs(config_data, file_data)
        config_file_used = config_path
    # If config_data is empty (e.g., empty file), use defaults
    if not config_data:
        config_data = copy.deepcopy(DEFAULT_CONFIG)
    # Validate config, apply defaults for missing fields (handled in Config)
    return Config(config_data, config_path=config_file_used)

@trace_config_operation("save")
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
