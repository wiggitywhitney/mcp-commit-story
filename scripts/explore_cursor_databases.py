#!/usr/bin/env python3
"""
One-time exploration script for Cursor databases.

This script explores Cursor SQLite databases to understand their structure
and identify where chat data is stored. Results inform Task 46 implementation.

Usage:
    python scripts/explore_cursor_databases.py [database_path]
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def explore_database_structure(db_path: Path) -> Dict[str, Any]:
    """Explore basic database structure."""
    print(f"\n🔍 Exploring database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Found {len(tables)} tables: {tables}")
        
        results = {
            'database_path': str(db_path),
            'tables': tables,
            'has_item_table': 'ItemTable' in tables
        }
        
        # If ItemTable exists, explore its structure
        if 'ItemTable' in tables:
            cursor.execute("PRAGMA table_info(ItemTable)")
            columns = cursor.fetchall()
            column_info = [(col[1], col[2]) for col in columns]  # (name, type)
            
            cursor.execute("SELECT COUNT(*) FROM ItemTable")
            row_count = cursor.fetchone()[0]
            
            print(f"📋 ItemTable structure: {column_info}")
            print(f"📈 ItemTable rows: {row_count}")
            
            results['item_table'] = {
                'columns': column_info,
                'row_count': row_count
            }
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"❌ Error exploring {db_path}: {e}")
        return {'error': str(e), 'database_path': str(db_path)}


def sample_item_table_keys(db_path: Path, limit: int = 20) -> List[str]:
    """Sample keys from ItemTable to see what's stored."""
    print(f"\n🔑 Sampling keys from ItemTable (limit: {limit})")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key FROM ItemTable LIMIT ?", (limit,))
        keys = [row[0] for row in cursor.fetchall()]
        
        print(f"📝 Sample keys:")
        for i, key in enumerate(keys, 1):
            print(f"  {i:2}. {key}")
        
        conn.close()
        return keys
        
    except Exception as e:
        print(f"❌ Error sampling keys: {e}")
        return []


def examine_chat_keys(db_path: Path) -> Dict[str, Any]:
    """Look for known chat-related keys and examine their content."""
    print(f"\n💬 Examining potential chat data keys")
    
    chat_keys = [
        "aiService.prompts",
        "workbench.panel.aichat.view.aichat.chatdata",
        "composerData",
        "aichat",
        "chat",
        "conversations"
    ]
    
    results = {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for key in chat_keys:
            cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                value = result[0]
                print(f"  ✅ Found key: {key}")
                print(f"     Data length: {len(value)} chars")
                
                # Try to parse as JSON and show structure
                try:
                    data = json.loads(value)
                    print(f"     JSON structure: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")
                    
                    # Show first few chars of data (truncated)
                    preview = value[:200] + "..." if len(value) > 200 else value
                    print(f"     Preview: {preview}")
                    
                    results[key] = {
                        'found': True,
                        'data_length': len(value),
                        'data_type': type(data).__name__,
                        'structure': list(data.keys()) if isinstance(data, dict) else None,
                        'preview': preview
                    }
                    
                except json.JSONDecodeError:
                    print(f"     Not valid JSON")
                    preview = value[:100] + "..." if len(value) > 100 else value
                    print(f"     Raw preview: {preview}")
                    
                    results[key] = {
                        'found': True,
                        'data_length': len(value),
                        'data_type': 'string',
                        'preview': preview
                    }
                    
                print()
            else:
                results[key] = {'found': False}
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"❌ Error examining chat keys: {e}")
        return {'error': str(e)}


def check_database_health(db_path: Path) -> Dict[str, Any]:
    """Basic database health check."""
    print(f"\n🏥 Checking database health")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        
        # Quick check
        cursor.execute("PRAGMA quick_check")
        quick_check = cursor.fetchone()[0]
        
        is_healthy = integrity == "ok" and quick_check == "ok"
        
        print(f"  Integrity check: {integrity}")
        print(f"  Quick check: {quick_check}")
        print(f"  Overall health: {'✅ HEALTHY' if is_healthy else '❌ ISSUES DETECTED'}")
        
        conn.close()
        
        return {
            'healthy': is_healthy,
            'integrity_check': integrity,
            'quick_check': quick_check
        }
        
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return {'error': str(e)}


def find_cursor_databases() -> List[Path]:
    """Find Cursor databases on this system."""
    print("🔍 Looking for Cursor databases...")
    
    # Common Cursor database locations
    potential_paths = []
    
    # macOS
    if sys.platform == "darwin":
        home = Path.home()
        potential_paths.extend([
            home / "Library/Application Support/Cursor/User/workspaceStorage",
            home / "Library/Application Support/Cursor/CachedData",
        ])
    
    # Windows
    elif sys.platform == "win32":
        import os
        appdata = Path(os.getenv('APPDATA', ''))
        potential_paths.extend([
            appdata / "Cursor/User/workspaceStorage",
            appdata / "Cursor/CachedData",
        ])
    
    # Linux
    else:
        home = Path.home()
        potential_paths.extend([
            home / ".config/Cursor/User/workspaceStorage",
            home / ".cache/Cursor",
        ])
    
    # Find actual database files
    databases = []
    for base_path in potential_paths:
        if base_path.exists():
            # Look for SQLite databases
            for db_file in base_path.rglob("*.db"):
                if db_file.is_file():
                    databases.append(db_file)
            for db_file in base_path.rglob("*.sqlite"):
                if db_file.is_file():
                    databases.append(db_file)
            for db_file in base_path.rglob("*.vscdb"):
                if db_file.is_file():
                    databases.append(db_file)
            for db_file in base_path.rglob("storage.json"):
                # Also look for storage.json files that might point to databases
                continue
    
    print(f"📍 Found {len(databases)} potential databases")
    return databases


def main():
    """Main exploration function."""
    print("🚀 Cursor Database Explorer")
    print("=" * 50)
    
    # Check for specific database path argument
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return
        databases = [db_path]
    else:
        # Auto-discover databases
        databases = find_cursor_databases()
        
        if not databases:
            print("❌ No Cursor databases found. Try specifying a path:")
            print("   python scripts/explore_cursor_databases.py /path/to/database.db")
            return
    
    # Explore each database
    all_results = []
    
    for db_path in databases:
        print(f"\n{'='*60}")
        
        # Basic structure
        structure = explore_database_structure(db_path)
        
        if 'error' in structure:
            continue
            
        if not structure.get('has_item_table'):
            print("⚠️  No ItemTable found - skipping detailed exploration")
            continue
        
        # Sample keys
        keys = sample_item_table_keys(db_path, limit=15)
        
        # Examine chat data
        chat_data = examine_chat_keys(db_path)
        
        # Health check
        health = check_database_health(db_path)
        
        # Compile results
        results = {
            'structure': structure,
            'sample_keys': keys,
            'chat_data': chat_data,
            'health': health
        }
        
        all_results.append(results)
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 EXPLORATION SUMMARY")
    print(f"   Databases explored: {len(all_results)}")
    
    chat_keys_found = set()
    for result in all_results:
        for key, data in result['chat_data'].items():
            if data.get('found'):
                chat_keys_found.add(key)
    
    if chat_keys_found:
        print(f"   Chat keys found: {', '.join(chat_keys_found)}")
    else:
        print("   No chat keys found")
    
    print("\n💡 Next steps for Task 46:")
    print("   1. Focus on databases with ItemTable")
    if chat_keys_found:
        print(f"   2. Implement parsing for: {', '.join(chat_keys_found)}")
    print("   3. Build chat data extraction functions")
    print("   4. Handle different Cursor versions gracefully")


if __name__ == "__main__":
    main() 