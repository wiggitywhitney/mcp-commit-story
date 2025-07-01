#!/usr/bin/env python3
"""
Create test SQLite databases that match Cursor's Composer schema.

This script generates minimal but representative test databases for integration testing:
- Workspace database: ItemTable with composer.composerData  
- Global database: cursorDiskKV with message headers and individual messages
- Sample data: 3 sessions, 15 total messages, realistic timestamps

Database Structure (from ComposerChatProvider analysis):
- Workspace DB: ItemTable([key], value) -> 'composer.composerData' contains allComposers JSON
- Global DB: cursorDiskKV([key], value) -> 'composerData:{id}' and 'bubbleId:{id}:{bid}' entries

RUNNING INTEGRATION TESTS:
    # Run all integration tests
    python -m pytest tests/integration/ -v
    
    # Run specific test categories
    python -m pytest tests/integration/test_composer_smoke.py -v          # Smoke tests (15)
    python -m pytest tests/integration/test_composer_integration.py -v    # Integration tests (5)
    python -m pytest tests/integration/test_composer_performance.py -v    # Performance tests (8)
    
    # Run with coverage
    python -m pytest tests/integration/ --cov=src/mcp_commit_story/composer_chat_provider --cov-report=html

REGENERATING TEST DATABASES:
    # If Cursor's schema changes, regenerate the test databases:
    python tests/fixtures/cursor_databases/create_test_databases.py
    
    # Then commit the updated databases to version control:
    git add tests/fixtures/cursor_databases/*.vscdb
    git commit -m "chore: update test databases for schema changes"

SCHEMA UPDATES:
    If Cursor updates their database schema:
    1. Update the schema creation code in create_workspace_database() and create_global_database()
    2. Update the sample data structure to match new requirements
    3. Run this script to regenerate test databases
    4. Update ComposerChatProvider if needed to handle schema changes
    5. Run integration tests to verify compatibility

Usage:
    python tests/fixtures/cursor_databases/create_test_databases.py
    
Generated files (< 100KB total):
    tests/fixtures/cursor_databases/test_workspace.vscdb  (12,288 bytes)
    tests/fixtures/cursor_databases/test_global.vscdb    (20,480 bytes)
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Any


def create_workspace_database(db_path: str) -> None:
    """Create test workspace database with ItemTable and composer session metadata."""
    
    # Sample session metadata (based on cursor_chat_sample.json structure)
    composer_data = {
        "allComposers": [
            {
                "type": "head",
                "composerId": "test-session-1",
                "name": "Implement error handling tests",
                "lastUpdatedAt": int(time.time() * 1000) - 3600000,  # 1 hour ago
                "createdAt": int(time.time() * 1000) - 7200000,      # 2 hours ago
                "unifiedMode": "agent",
                "forceMode": "edit"
            },
            {
                "type": "head", 
                "composerId": "test-session-2",
                "name": "Review integration patterns",
                "lastUpdatedAt": int(time.time() * 1000) - 1800000,  # 30 minutes ago
                "createdAt": int(time.time() * 1000) - 5400000,      # 1.5 hours ago
                "unifiedMode": "agent",
                "forceMode": "edit"
            },
            {
                "type": "head",
                "composerId": "test-session-3", 
                "name": "Performance optimization discussion",
                "lastUpdatedAt": int(time.time() * 1000) - 900000,   # 15 minutes ago
                "createdAt": int(time.time() * 1000) - 3600000,      # 1 hour ago
                "unifiedMode": "agent",
                "forceMode": "edit"
            }
        ]
    }
    
    # Create database and tables
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Create ItemTable with exact schema
        cursor.execute("""
            CREATE TABLE ItemTable (
                [key] TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Insert composer metadata
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ('composer.composerData', json.dumps(composer_data))
        )
        
        # Add some other typical workspace data (optional, for realism)
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ('workspace.lastAccessed', str(int(time.time() * 1000)))
        )
        
        conn.commit()


def create_global_database(db_path: str) -> None:
    """Create test global database with cursorDiskKV and message data."""
    
    current_time_ms = int(time.time() * 1000)
    
    # Sample message data for each session
    sessions_data = {
        "test-session-1": {
            "headers": {
                "fullConversationHeadersOnly": [
                    {"bubbleId": "bubble-1-1", "type": 1},
                    {"bubbleId": "bubble-1-2", "type": 2},
                    {"bubbleId": "bubble-1-3", "type": 1},
                    {"bubbleId": "bubble-1-4", "type": 2},
                    {"bubbleId": "bubble-1-5", "type": 1}
                ],
                "sessionName": "Implement error handling tests",
                "totalMessages": 5
            },
            "messages": [
                {
                    "bubble_id": "bubble-1-1",
                    "content": "I need to implement comprehensive error handling for the Composer integration. Let's start with creating test cases for all exception types.",
                    "messageType": 0,  # user message
                    "timestamp": current_time_ms - 7000000,  # ~2 hours ago
                },
                {
                    "bubble_id": "bubble-1-2", 
                    "content": "I'll help you implement comprehensive error handling following TDD methodology. Let's start by writing failing tests for each exception type, then implement the error handling patterns.",
                    "messageType": 1,  # assistant message
                    "timestamp": current_time_ms - 6950000,
                },
                {
                    "bubble_id": "bubble-1-3",
                    "content": "The tests should cover CursorDatabaseNotFoundError, CursorDatabaseAccessError, CursorDatabaseSchemaError, CursorDatabaseQueryError, and WorkspaceDetectionError scenarios.",
                    "messageType": 0,
                    "timestamp": current_time_ms - 6900000,
                },
                {
                    "bubble_id": "bubble-1-4",
                    "content": "Excellent! I'll create comprehensive test scenarios covering all those exception types. We should also test graceful degradation and ensure the system continues operation despite component failures.",
                    "messageType": 1,
                    "timestamp": current_time_ms - 6850000,
                },
                {
                    "bubble_id": "bubble-1-5",
                    "content": "Perfect. Let's also make sure we implement circuit breaker patterns and proper telemetry integration.",
                    "messageType": 0,
                    "timestamp": current_time_ms - 6800000,
                }
            ]
        },
        "test-session-2": {
            "headers": {
                "fullConversationHeadersOnly": [
                    {"bubbleId": "bubble-2-1", "type": 1},
                    {"bubbleId": "bubble-2-2", "type": 2},
                    {"bubbleId": "bubble-2-3", "type": 1},
                    {"bubbleId": "bubble-2-4", "type": 2}
                ],
                "sessionName": "Review integration patterns", 
                "totalMessages": 4
            },
            "messages": [
                {
                    "bubble_id": "bubble-2-1",
                    "content": "Can you help me review the integration patterns we're using for the chat context manager?",
                    "messageType": 0,
                    "timestamp": current_time_ms - 5300000,  # ~1.5 hours ago
                },
                {
                    "bubble_id": "bubble-2-2",
                    "content": "Absolutely! The chat context manager uses a thin orchestration layer approach that calls the existing query_cursor_chat_database() function and transforms the response into enhanced ChatContextData format.",
                    "messageType": 1,
                    "timestamp": current_time_ms - 5250000,
                },
                {
                    "bubble_id": "bubble-2-3", 
                    "content": "That makes sense. How does it handle the time window filtering?",
                    "messageType": 0,
                    "timestamp": current_time_ms - 5200000,
                },
                {
                    "bubble_id": "bubble-2-4",
                    "content": "The time window filtering is handled by the commit-based time window system. It calculates precise time ranges based on commit timing and development context, ensuring we get relevant conversation history.",
                    "messageType": 1,
                    "timestamp": current_time_ms - 5150000,
                }
            ]
        },
        "test-session-3": {
            "headers": {
                "fullConversationHeadersOnly": [
                    {"bubbleId": "bubble-3-1", "type": 1},
                    {"bubbleId": "bubble-3-2", "type": 2},
                    {"bubbleId": "bubble-3-3", "type": 1},
                    {"bubbleId": "bubble-3-4", "type": 2},
                    {"bubbleId": "bubble-3-5", "type": 1},
                    {"bubbleId": "bubble-3-6", "type": 2}
                ],
                "sessionName": "Performance optimization discussion",
                "totalMessages": 6  
            },
            "messages": [
                {
                    "bubble_id": "bubble-3-1",
                    "content": "I'm concerned about performance. The chat context extraction should complete under 500ms.",
                    "messageType": 0,
                    "timestamp": current_time_ms - 3500000,  # ~1 hour ago
                },
                {
                    "bubble_id": "bubble-3-2",
                    "content": "You're absolutely right to focus on performance. The 500ms threshold is critical for responsive journal generation. Let me review our current implementation.",
                    "messageType": 1,
                    "timestamp": current_time_ms - 3450000,
                },
                {
                    "bubble_id": "bubble-3-3",
                    "content": "What are the main performance bottlenecks we should be aware of?",
                    "messageType": 0,
                    "timestamp": current_time_ms - 3400000,
                },
                {
                    "bubble_id": "bubble-3-4",
                    "content": "The main bottlenecks are: 1) Database connection time, 2) Query execution for large message volumes, 3) JSON parsing of session metadata, and 4) Message transformation processing.",
                    "messageType": 1,
                    "timestamp": current_time_ms - 3350000,
                },
                {
                    "bubble_id": "bubble-3-5",
                    "content": "How can we optimize these areas?",
                    "messageType": 0,
                    "timestamp": current_time_ms - 3300000,
                },
                {
                    "bubble_id": "bubble-3-6",
                    "content": "We can optimize by: using parameterized queries, implementing efficient time window filtering, minimizing JSON parsing overhead, and adding proper database indexing strategies.",
                    "messageType": 1,
                    "timestamp": current_time_ms - 3250000,
                }
            ]
        }
    }
    
    # Create database and tables
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Create cursorDiskKV table with exact schema
        cursor.execute("""
            CREATE TABLE cursorDiskKV (
                [key] TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Insert data for each session
        for session_id, session_data in sessions_data.items():
            # Insert message headers
            headers_key = f"composerData:{session_id}"
            cursor.execute(
                "INSERT INTO cursorDiskKV ([key], value) VALUES (?, ?)",
                (headers_key, json.dumps(session_data["headers"]))
            )
            
            # Insert individual messages
            for message in session_data["messages"]:
                bubble_id = message["bubble_id"]
                message_key = f"bubbleId:{session_id}:{bubble_id}"
                
                # Create message data structure (excluding bubble_id from content)
                message_data = {
                    "text": message["content"],  # ComposerChatProvider expects 'text' field
                    "messageType": message["messageType"],
                    "timestamp": message["timestamp"]
                }
                
                cursor.execute(
                    "INSERT INTO cursorDiskKV ([key], value) VALUES (?, ?)",
                    (message_key, json.dumps(message_data))
                )
        
        conn.commit()


def main():
    """Generate test databases in the fixtures directory."""
    
    # Determine script location and set output paths
    script_dir = Path(__file__).parent
    workspace_db_path = script_dir / "test_workspace.vscdb"
    global_db_path = script_dir / "test_global.vscdb"
    
    print("Creating test Cursor Composer databases...")
    print(f"Workspace DB: {workspace_db_path}")
    print(f"Global DB: {global_db_path}")
    
    # Remove existing databases if they exist
    workspace_db_path.unlink(missing_ok=True)
    global_db_path.unlink(missing_ok=True)
    
    # Create new test databases
    create_workspace_database(str(workspace_db_path))
    create_global_database(str(global_db_path))
    
    # Report file sizes
    workspace_size = workspace_db_path.stat().st_size
    global_size = global_db_path.stat().st_size
    total_size = workspace_size + global_size
    
    print(f"\nDatabases created successfully!")
    print(f"Workspace DB size: {workspace_size:,} bytes")
    print(f"Global DB size: {global_size:,} bytes") 
    print(f"Total size: {total_size:,} bytes")
    
    # Verify the target of < 100KB
    if total_size < 100 * 1024:
        print(f"✅ Size target met: {total_size:,} bytes < 100KB")
    else:
        print(f"⚠️  Size target exceeded: {total_size:,} bytes > 100KB")
    
    print("\nTest data summary:")
    print("- 3 sessions with realistic names")
    print("- 15 total messages across all sessions")
    print("- Timestamps spanning ~2 hours of development work")
    print("- Mix of user and assistant messages")
    print("- Representative conversation patterns")


if __name__ == "__main__":
    main() 