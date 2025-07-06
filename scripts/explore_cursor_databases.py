#!/usr/bin/env python3
"""
One-time exploration script for Cursor databases.

This script explores Cursor SQLite databases to understand their structure
and identify where chat data is stored. Results inform chat integration implementation.

Enhanced with deep chat data format research:
- Message counting and date range analysis
- Role indicators (user vs assistant) detection
- Conversation threading/structure analysis
- Multi-key investigation for chat data storage patterns
- Truncation pattern detection

Usage:
    python scripts/explore_cursor_databases.py [database_path]
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


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


def deep_analyze_chat_data(db_path: Path) -> Dict[str, Any]:
    """
    Deep analysis of chat data to answer critical research questions.
    
    Critical Questions:
    1. Where is all chat history stored in the database?
    2. How are user prompts and AI responses organized?
    3. What's the actual message count and date range in each workspace?
    4. Is there any truncation happening based on size/age?
    5. Do messages have role indicators or threading information?
    """
    print(f"\n🔬 DEEP CHAT DATA ANALYSIS (Task 45.7)")
    print("=" * 60)
    
    chat_keys_to_investigate = [
        "aiService.prompts",
        "aiService.generations", 
        "composer.composerData",
        "composerData",
        "workbench.panel.aichat.view.aichat.chatdata",
        "aichat",
        "chat",
        "conversations"
    ]
    
    analysis_results = {
        'critical_questions': {},
        'key_findings': {},
        'message_analysis': {},
        'database_path': str(db_path)
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📍 Analyzing database: {db_path.name}")
        
        # Check each potential chat key
        for key in chat_keys_to_investigate:
            cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                print(f"\n✅ FOUND KEY: {key}")
                value = result[0]
                
                try:
                    data = json.loads(value)
                    key_analysis = analyze_chat_key_content(key, data, value)
                    analysis_results['key_findings'][key] = key_analysis
                    
                    # Print summary for this key
                    print(f"   📊 Data type: {key_analysis['data_type']}")
                    print(f"   📏 Data length: {key_analysis['data_length']} chars")
                    if 'message_count' in key_analysis:
                        print(f"   💬 Message count: {key_analysis['message_count']}")
                    if 'date_range' in key_analysis:
                        print(f"   📅 Date range: {key_analysis['date_range']['earliest']} to {key_analysis['date_range']['latest']}")
                    if 'roles_found' in key_analysis:
                        print(f"   👥 Roles found: {key_analysis['roles_found']}")
                    
                except json.JSONDecodeError:
                    print(f"   ⚠️  Not valid JSON - length: {len(value)} chars")
                    analysis_results['key_findings'][key] = {
                        'found': True,
                        'data_type': 'string',
                        'data_length': len(value),
                        'json_valid': False
                    }
            else:
                analysis_results['key_findings'][key] = {'found': False}
        
        # Answer critical questions based on findings
        analysis_results['critical_questions'] = answer_critical_questions(analysis_results['key_findings'])
        
        # Generate summary insights
        analysis_results['summary_insights'] = generate_summary_insights(analysis_results['key_findings'])
        
        conn.close()
        return analysis_results
        
    except Exception as e:
        print(f"❌ Error in deep analysis: {e}")
        return {'error': str(e), 'database_path': str(db_path)}


def analyze_chat_key_content(key: str, data: Any, raw_value: str) -> Dict[str, Any]:
    """Analyze the content of a specific chat-related key."""
    analysis = {
        'found': True,
        'data_type': type(data).__name__,
        'data_length': len(raw_value),
        'json_valid': True
    }
    
    # If it's a list, analyze as potential messages
    if isinstance(data, list):
        analysis['message_count'] = len(data)
        analysis['is_message_array'] = True
        
        if data:  # If not empty
            # Sample first and last few messages
            sample_size = min(3, len(data))
            analysis['sample_messages'] = {
                'first': data[:sample_size],
                'last': data[-sample_size:] if len(data) > sample_size else []
            }
            
            # Analyze message structure
            structure_analysis = analyze_message_structure(data)
            analysis.update(structure_analysis)
            
            # Check for date ranges
            date_analysis = analyze_message_dates(data)
            if date_analysis:
                analysis['date_range'] = date_analysis
    
    elif isinstance(data, dict):
        analysis['dict_keys'] = list(data.keys())
        analysis['is_message_array'] = False
        
        # Check if any dict values contain message arrays
        for dict_key, dict_value in data.items():
            if isinstance(dict_value, list) and dict_value:
                print(f"      📋 Found nested array in '{dict_key}': {len(dict_value)} items")
                nested_analysis = analyze_message_structure(dict_value)
                if nested_analysis.get('likely_messages'):
                    analysis[f'nested_{dict_key}'] = nested_analysis
    
    else:
        analysis['is_message_array'] = False
    
    return analysis


def analyze_message_structure(messages: List[Any]) -> Dict[str, Any]:
    """Analyze the structure of potential chat messages."""
    if not messages:
        return {'likely_messages': False}
    
    analysis = {
        'likely_messages': False,
        'roles_found': set(),
        'common_fields': {},
        'message_types': set()
    }
    
    # Sample a few messages to analyze structure
    sample_size = min(10, len(messages))
    sample_messages = messages[:sample_size]
    
    field_counts = {}
    
    for msg in sample_messages:
        if isinstance(msg, dict):
            for field in msg.keys():
                field_counts[field] = field_counts.get(field, 0) + 1
            
            # Look for role indicators
            for role_field in ['role', 'sender', 'author', 'commandType']:
                if role_field in msg:
                    analysis['roles_found'].add(str(msg[role_field]))
            
            # Look for message type indicators
            for type_field in ['type', 'commandType', 'messageType']:
                if type_field in msg:
                    analysis['message_types'].add(str(msg[type_field]))
    
    # Determine common fields (appear in most messages)
    total_sample = len(sample_messages)
    analysis['common_fields'] = {
        field: count for field, count in field_counts.items() 
        if count >= total_sample * 0.8  # Appears in 80%+ of messages
    }
    
    # Heuristic: likely messages if they have text content and some structure
    text_fields = ['text', 'content', 'message', 'prompt', 'response']
    has_text_field = any(field in analysis['common_fields'] for field in text_fields)
    has_structure = len(analysis['common_fields']) >= 2
    
    analysis['likely_messages'] = has_text_field and has_structure
    analysis['roles_found'] = list(analysis['roles_found'])
    analysis['message_types'] = list(analysis['message_types'])
    
    return analysis


def analyze_message_dates(messages: List[Any]) -> Optional[Dict[str, str]]:
    """Analyze date ranges in messages."""
    dates = []
    
    # Look for various date fields
    date_fields = ['timestamp', 'date', 'created', 'time', 'createdAt', 'updatedAt']
    
    for msg in messages:
        if isinstance(msg, dict):
            for field in date_fields:
                if field in msg:
                    try:
                        # Try to parse various date formats
                        date_value = msg[field]
                        if isinstance(date_value, (int, float)):
                            # Assume Unix timestamp (seconds or milliseconds)
                            if date_value > 1000000000000:  # Milliseconds
                                date_value = date_value / 1000
                            parsed_date = datetime.fromtimestamp(date_value)
                            dates.append(parsed_date)
                        elif isinstance(date_value, str):
                            # Try parsing ISO format
                            try:
                                parsed_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                                dates.append(parsed_date)
                            except:
                                pass
                    except:
                        pass
    
    if dates:
        dates.sort()
        return {
            'earliest': dates[0].isoformat(),
            'latest': dates[-1].isoformat(),
            'total_dates_found': len(dates)
        }
    
    return None


def answer_critical_questions(key_findings: Dict[str, Any]) -> Dict[str, Any]:
    """Answer the critical research questions based on findings."""
    questions = {}
    
    # Question 1: Is aiService.prompts ALL chat history or just user prompts?
    prompts_data = key_findings.get('aiService.prompts', {})
    if prompts_data.get('found'):
        if prompts_data.get('roles_found'):
            questions['q1_prompts_content'] = {
                'answer': 'Contains multiple roles' if len(prompts_data.get('roles_found', [])) > 1 else 'Likely just prompts',
                'evidence': f"Roles found: {prompts_data.get('roles_found', [])}",
                'message_count': prompts_data.get('message_count', 'unknown')
            }
        else:
            questions['q1_prompts_content'] = {
                'answer': 'Structure unclear - needs deeper investigation',
                'evidence': 'No clear role indicators found',
                'message_count': prompts_data.get('message_count', 'unknown')
            }
    else:
        questions['q1_prompts_content'] = {
            'answer': 'aiService.prompts not found',
            'evidence': 'Key does not exist in this database'
        }
    
    # Question 2: Where are the AI responses stored?
    generations_data = key_findings.get('aiService.generations', {})
    if generations_data.get('found'):
        questions['q2_ai_responses'] = {
            'answer': 'Potentially in aiService.generations',
            'evidence': f"Found aiService.generations with {generations_data.get('message_count', 'unknown')} items",
            'structure': generations_data.get('common_fields', {})
        }
    else:
        # Check other keys for AI responses
        potential_response_keys = [k for k, v in key_findings.items() 
                                 if v.get('found') and 'assistant' in v.get('roles_found', [])]
        if potential_response_keys:
            questions['q2_ai_responses'] = {
                'answer': f'Potentially in: {", ".join(potential_response_keys)}',
                'evidence': 'Found assistant role in these keys'
            }
        else:
            questions['q2_ai_responses'] = {
                'answer': 'AI responses location unclear',
                'evidence': 'No clear assistant/AI role indicators found'
            }
    
    # Question 3: Message counts and date ranges
    all_message_counts = {}
    all_date_ranges = {}
    for key, data in key_findings.items():
        if data.get('found') and data.get('message_count'):
            all_message_counts[key] = data['message_count']
        if data.get('date_range'):
            all_date_ranges[key] = data['date_range']
    
    questions['q3_counts_and_dates'] = {
        'message_counts': all_message_counts,
        'date_ranges': all_date_ranges
    }
    
    # Question 4: Truncation patterns
    large_datasets = {k: v for k, v in key_findings.items() 
                     if v.get('found') and v.get('message_count', 0) > 100}
    questions['q4_truncation'] = {
        'large_datasets': large_datasets,
        'analysis': 'Need to check for round numbers or cutoff patterns'
    }
    
    # Question 5: Role indicators and threading
    role_info = {}
    for key, data in key_findings.items():
        if data.get('roles_found'):
            role_info[key] = data['roles_found']
    
    questions['q5_roles_and_threading'] = {
        'roles_by_key': role_info,
        'threading_evidence': 'Check common_fields for conversation/thread IDs'
    }
    
    return questions


def generate_summary_insights(key_findings: Dict[str, Any]) -> Dict[str, Any]:
    """Generate high-level insights from the analysis."""
    insights = {
        'chat_keys_found': [],
        'total_messages_estimate': 0,
        'primary_chat_location': None,
        'data_completeness_assessment': 'unknown'
    }
    
    # Find all keys that contain chat-like data
    for key, data in key_findings.items():
        if data.get('found') and data.get('likely_messages'):
            insights['chat_keys_found'].append({
                'key': key,
                'message_count': data.get('message_count', 0),
                'roles': data.get('roles_found', [])
            })
            insights['total_messages_estimate'] += data.get('message_count', 0)
    
    # Determine primary chat location
    if insights['chat_keys_found']:
        primary = max(insights['chat_keys_found'], key=lambda x: x['message_count'])
        insights['primary_chat_location'] = primary['key']
        insights['primary_message_count'] = primary['message_count']
    
    return insights


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
    """Main exploration function with enhanced Task 45.7 analysis."""
    print("🚀 Cursor Database Explorer - Enhanced for Task 45.7")
    print("=" * 60)
    
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
    
    # Explore each database with enhanced analysis
    all_results = []
    deep_analysis_results = []
    
    for db_path in databases:
        print(f"\n{'='*80}")
        
        # Basic structure (existing functionality)
        structure = explore_database_structure(db_path)
        
        if 'error' in structure:
            continue
            
        if not structure.get('has_item_table'):
            print("⚠️  No ItemTable found - skipping detailed exploration")
            continue
        
        # NEW: Deep chat data analysis for Task 45.7
        deep_analysis = deep_analyze_chat_data(db_path)
        deep_analysis_results.append(deep_analysis)
        
        # Sample keys (existing)
        keys = sample_item_table_keys(db_path, limit=15)
        
        # Basic chat examination (existing) 
        chat_data = examine_chat_keys(db_path)
        
        # Health check (existing)
        health = check_database_health(db_path)
        
        # Compile results
        results = {
            'structure': structure,
            'sample_keys': keys,
            'chat_data': chat_data,
            'health': health,
            'deep_analysis': deep_analysis  # NEW
        }
        
        all_results.append(results)
    
    # Enhanced summary for Task 45.7
    print(f"\n{'='*80}")
    print("📋 TASK 45.7 RESEARCH SUMMARY")
    print(f"   Databases analyzed: {len(deep_analysis_results)}")
    
    # Aggregate findings across all databases
    aggregate_findings = aggregate_research_findings(deep_analysis_results)
    print_research_summary(aggregate_findings)
    
    print("\n💡 Next steps for Task 46:")
    print("   1. Review research findings above")
    print("   2. Update docs/cursor-chat-database-research.md")
    print("   3. Design chat data extraction based on confirmed format")
    print("   4. Implement parsing for confirmed storage keys")


def aggregate_research_findings(deep_analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate findings from multiple database analyses."""
    aggregated = {
        'total_databases': len(deep_analysis_results),
        'keys_found_across_databases': {},
        'consistent_patterns': {},
        'critical_question_consensus': {}
    }
    
    # Track which keys are found across databases
    for result in deep_analysis_results:
        if 'key_findings' in result:
            for key, data in result['key_findings'].items():
                if data.get('found'):
                    if key not in aggregated['keys_found_across_databases']:
                        aggregated['keys_found_across_databases'][key] = []
                    aggregated['keys_found_across_databases'][key].append({
                        'database': result.get('database_path', 'unknown'),
                        'message_count': data.get('message_count'),
                        'roles': data.get('roles_found', [])
                    })
    
    # Calculate consistency
    for key, instances in aggregated['keys_found_across_databases'].items():
        consistency_rate = len(instances) / aggregated['total_databases']
        aggregated['consistent_patterns'][key] = {
            'found_in_percent': f"{consistency_rate * 100:.1f}%",
            'found_in_count': f"{len(instances)}/{aggregated['total_databases']}",
            'instances': instances
        }
    
    return aggregated


def print_research_summary(aggregate_findings: Dict[str, Any]) -> None:
    """Print a comprehensive research summary."""
    print(f"\n🔍 RESEARCH FINDINGS SUMMARY")
    print(f"   Total databases analyzed: {aggregate_findings['total_databases']}")
    
    print(f"\n📊 KEY CONSISTENCY ACROSS DATABASES:")
    for key, pattern in aggregate_findings['consistent_patterns'].items():
        print(f"   {key}: {pattern['found_in_percent']} ({pattern['found_in_count']})")
        if pattern['instances']:
            total_messages = sum(inst.get('message_count', 0) for inst in pattern['instances'] if inst.get('message_count'))
            if total_messages > 0:
                print(f"      Total messages across instances: {total_messages}")
            
            # Show role patterns
            all_roles = set()
            for inst in pattern['instances']:
                all_roles.update(inst.get('roles', []))
            if all_roles:
                print(f"      Roles found: {list(all_roles)}")
    
    # Highlight the most consistent findings
    print(f"\n⭐ MOST RELIABLE FINDINGS:")
    reliable_keys = [k for k, v in aggregate_findings['consistent_patterns'].items() 
                    if len(v['instances']) == aggregate_findings['total_databases']]
    
    if reliable_keys:
        print(f"   Keys found in 100% of databases: {', '.join(reliable_keys)}")
    else:
        print("   No keys found in 100% of databases")
    
    # Show partial consistency
    partial_keys = [k for k, v in aggregate_findings['consistent_patterns'].items() 
                   if len(v['instances']) > aggregate_findings['total_databases'] * 0.5]
    
    if partial_keys:
        print(f"   Keys found in >50% of databases: {', '.join(partial_keys)}")


if __name__ == "__main__":
    main() 