import pytest
from mcp_journal.config import Config

def test_config_defaults():
    config = Config()
    defaults = Config.get_default_config()
    assert config.journal_path == defaults['journal_path']
    assert config.auto_generate == defaults['auto_generate']
    assert config.included_sections == defaults['included_sections']
    assert config.section_order == defaults['section_order']
    assert config.date_format == defaults['date_format']
    assert config.file_extension == defaults['file_extension']

def test_get_default_config():
    defaults = Config.get_default_config()
    assert isinstance(defaults, dict)
    assert 'journal_path' in defaults
    assert 'auto_generate' in defaults
    assert 'included_sections' in defaults
    assert 'section_order' in defaults
    assert 'date_format' in defaults
    assert 'file_extension' in defaults

def test_as_dict():
    config = Config()
    d = config.as_dict()
    assert isinstance(d, dict)
    assert d['journal_path'] == config.journal_path

def test_is_valid_defaults():
    config = Config()
    assert config.is_valid()

def test_reset_to_defaults():
    config = Config({'journal_path': '/tmp/override'})
    config.reset_to_defaults()
    assert config.journal_path == Config.get_default_config()['journal_path']

def test_partial_and_invalid_config():
    config = Config({'auto_generate': False, 'unknown_key': 123})
    assert config.auto_generate is False
    # unknown_key should be ignored
    assert not hasattr(config, 'unknown_key')
    # Invalid type for included_sections should fallback to default
    config2 = Config({'included_sections': 'notalist'})
    assert config2.included_sections == Config.get_default_config()['included_sections'] 