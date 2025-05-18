#!/usr/bin/env python3
"""
This utility script verifies that a configuration file exists and is readable.
It is a development tool used for testing, not part of the main application.

The main application will generate the configuration file during initialization,
referencing the .mcp-journalrc.yaml.example if it exists.
"""
from pathlib import Path
import sys

def verify_config_file(config_path=".mcp-journalrc.yaml"):
    """Verify that the configuration file exists and is readable"""
    try:
        config_path = Path(config_path)
        
        if not config_path.exists():
            print(f"Error: Configuration file '{config_path}' not found.")
            return False
        
        # Try to read the file
        with open(config_path, 'r') as f:
            content = f.read()
            
        if not content.strip():
            print("Error: Configuration file is empty.")
            return False
            
        # Check for basic YAML structure
        if ":" not in content:
            print("Warning: Configuration file may not be valid YAML (no key-value pairs detected).")
            return False
            
        # Check for required sections
        required_sections = ['journal:', 'git:', 'telemetry:']
        missing_sections = []
        
        for section in required_sections:
            if section not in content:
                missing_sections.append(section.rstrip(':'))
        
        if missing_sections:
            print(f"Warning: Missing required configuration sections: {', '.join(missing_sections)}")
            return False
        
        # Count lines as a basic metric
        line_count = len(content.splitlines())
        print(f"Configuration file has {line_count} lines.")
        
        print(f"Successfully verified configuration file at '{config_path}'")
        return True
    
    except Exception as e:
        print(f"Error verifying configuration file: {e}")
        return False

def main():
    """Main function to verify configuration file"""
    config_path = ".mcp-journalrc.yaml"
    
    # Check if custom path provided
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    success = verify_config_file(config_path)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 