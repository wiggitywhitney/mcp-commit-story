"""Debug script to investigate the mocking behavior in test_load_config_with_precedence."""
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import yaml
from mcp_journal.config import load_config, Config, DEFAULT_CONFIG

def print_calls(mock_obj, name="Mock"):
    print(f"{name} call count: {mock_obj.call_count}")
    for i, c in enumerate(mock_obj.call_args_list):
        print(f"  Call {i+1}: {c}")

class DebugTest(unittest.TestCase):
    def test_debug_precedence_issue(self):
        """Debug test to investigate the mocking behavior in test_load_config_with_precedence."""
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
        
        # Create mocks
        mock_find = MagicMock()
        mock_load = MagicMock()
        mock_open_instance = mock_open()
        
        # Setup return values
        mock_find.return_value = ('local_path', 'global_path')
        
        # Test 1: Load local first, then global
        print("\nTEST 1: Load local first, then global")
        mock_load.reset_mock()
        mock_load.side_effect = [local_config, global_config]
        
        with patch('mcp_journal.config.find_config_files', mock_find), \
             patch('mcp_journal.config.yaml.safe_load', mock_load), \
             patch('mcp_journal.config.DEFAULT_CONFIG', default_config), \
             patch('builtins.open', mock_open_instance):
            
            config = load_config()
            print(f"Journal path: {config.journal_path}")
            print_calls(mock_load, "yaml.safe_load")
            print_calls(mock_open_instance, "open")
        
        # Test 2: Load global first, then local
        print("\nTEST 2: Load global first, then local")
        mock_load.reset_mock()
        mock_load.side_effect = [global_config, local_config]
        
        with patch('mcp_journal.config.find_config_files', mock_find), \
             patch('mcp_journal.config.yaml.safe_load', mock_load), \
             patch('mcp_journal.config.DEFAULT_CONFIG', default_config), \
             patch('builtins.open', mock_open_instance):
            
            config = load_config()
            print(f"Journal path: {config.journal_path}")
            print_calls(mock_load, "yaml.safe_load")
            print_calls(mock_open_instance, "open")

if __name__ == "__main__":
    unittest.main() 