"""Debug script to test mock_load ordering in load_config."""
import unittest
from unittest.mock import patch, mock_open, MagicMock
from mcp_journal.config import load_config, Config, DEFAULT_CONFIG

class DebugTest(unittest.TestCase):
    def test_debug_load_config_order(self):
        """Debug test to identify the order of mock_load calls."""
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
        
        mock_find = MagicMock()
        mock_load = MagicMock()
        
        # Setup return values
        mock_find.return_value = ('local_path', 'global_path')
        mock_load.side_effect = [local_config, global_config]
        
        # Test with patch
        with patch('mcp_journal.config.find_config_files', mock_find), \
             patch('mcp_journal.config.yaml.safe_load', mock_load), \
             patch('mcp_journal.config.DEFAULT_CONFIG', default_config), \
             patch('builtins.open', mock_open()):
            
            config = load_config()
            print(f"Journal path: {config.journal_path}")
            print(f"Mock load call count: {mock_load.call_count}")
            print(f"Mock load call args: {[call[0][0] for call in mock_load.call_args_list]}")
            
            # If we can get to this point, try printing the local and global data before merging
            with patch('mcp_journal.config.find_config_files', return_value=('local_path', 'global_path')):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load') as mock_load2:
                        mock_load2.side_effect = [local_config, global_config]
                        config = load_config()
                        print(f"Second test - Journal path: {config.journal_path}")

if __name__ == "__main__":
    unittest.main() 