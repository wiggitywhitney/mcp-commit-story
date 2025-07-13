#!/usr/bin/env python3
"""
Script to generate a journal entry for a specific commit using journal_workflow.py
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_commit_story.git_utils import get_repo
from mcp_commit_story.config import load_config
from mcp_commit_story.context_collection import collect_git_context, collect_chat_history, collect_recent_journal_context
from mcp_commit_story.context_types import JournalContext
from mcp_commit_story.journal_generate import (
    generate_summary_section, generate_technical_synopsis_section,
    generate_accomplishments_section, generate_frustrations_section,
    generate_tone_mood_section, generate_discussion_notes_section,
    generate_discussion_notes_section_simple, generate_commit_metadata_section
)

def test_single_function(function_name, generator_func, journal_context):
    """Test a single generator function"""
    print(f"\n{'='*50}")
    print(f"Testing: {function_name}")
    print(f"{'='*50}")
    
    try:
        # Check context size before calling
        context_str = str(journal_context)
        context_size = len(context_str)
        print(f"Context size: {context_size:,} characters")
        
        if context_size > 100000:
            print(f"⚠️  Context is very large - AI call will likely timeout/fail")
        
        result = generator_func(journal_context)
        print(f"✅ SUCCESS: {function_name}")
        print(f"Result: {result}")
        
        # Check if result looks like AI-generated or fallback
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, str) and value:
                    if "Generated from commit" in value or "Modified" in value:
                        print(f"  → {key}: FALLBACK content")
                    elif len(value) > 100:
                        print(f"  → {key}: Potentially AI-generated content ({len(value)} chars)")
                    else:
                        print(f"  → {key}: Short content ({len(value)} chars)")
                elif isinstance(value, list) and value:
                    if any("Completed:" in str(item) for item in value):
                        print(f"  → {key}: FALLBACK content ({len(value)} items)")
                    else:
                        print(f"  → {key}: Potentially AI-generated content ({len(value)} items)")
                elif not value:
                    print(f"  → {key}: Empty (AI likely failed silently)")
        
        return result
    except Exception as e:
        print(f"❌ FAILED: {function_name}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    commit_hash = "f541e5f"
    
    try:
        # Get the repository and commit object
        repo = get_repo()
        commit = repo.commit(commit_hash)
        
        print(f"Testing individual generator functions for commit: {commit_hash}")
        print(f"Commit message: {commit.message.strip()}")
        print(f"Author: {commit.author}")
        print(f"Date: {commit.committed_datetime}")
        
        # Load configuration and collect context
        config = load_config()
        journal_path = config.get('journal', {}).get('path', 'sandbox-journal')
        
        print(f"\n📦 Collecting context...")
        
        # Collect context like the workflow does
        context_data = {}
        
        try:
            context_data['chat_history'] = collect_chat_history(since_commit=commit.hexsha, max_messages_back=150)
            print("✅ Chat history collected")
        except Exception as e:
            print(f"⚠️  Chat history failed: {e}")
            context_data['chat_history'] = None
        
        try:
            context_data['git_context'] = collect_git_context(commit_hash=commit.hexsha, journal_path=journal_path)
            print("✅ Git context collected")
        except Exception as e:
            print(f"⚠️  Git context failed: {e}")
            context_data['git_context'] = None
        
        try:
            context_data['journal_context'] = collect_recent_journal_context(commit)
            print("✅ Journal context collected")
        except Exception as e:
            print(f"⚠️  Journal context failed: {e}")
            context_data['journal_context'] = None
        
        # Build JournalContext
        journal_context = JournalContext(
            chat=context_data['chat_history'],
            git=context_data['git_context'],
            journal=context_data['journal_context']
        )
        
        # Test each generator function individually
        generators = [
            ("Summary", generate_summary_section),
            ("Technical Synopsis", generate_technical_synopsis_section),
            ("Accomplishments", generate_accomplishments_section),
            ("Frustrations", generate_frustrations_section),
            ("Tone/Mood", generate_tone_mood_section),
            ("Discussion Notes", generate_discussion_notes_section),
            ("Discussion Notes Simple", generate_discussion_notes_section_simple),
            ("Commit Metadata", generate_commit_metadata_section),
        ]
        
        results = {}
        for name, func in generators:
            result = test_single_function(name, func, journal_context)
            results[name] = result
        
        print(f"\n🎯 SUMMARY")
        print(f"{'='*50}")
        successful = [name for name, result in results.items() if result is not None]
        failed = [name for name, result in results.items() if result is None]
        
        print(f"✅ Successful ({len(successful)}): {', '.join(successful)}")
        print(f"❌ Failed ({len(failed)}): {', '.join(failed)}")
        
        # Create a journal entry from the results
        print(f"\n📝 Creating journal entry...")
        from mcp_commit_story.journal_generate import JournalEntry
        from datetime import datetime
        
        # Extract content from results
        summary_content = results.get("Summary", {}).get('summary', '')
        
        # Handle technical_synopsis - could be string or list
        tech_synopsis = results.get("Technical Synopsis", {}).get('technical_synopsis', '')
        if isinstance(tech_synopsis, list):
            technical_synopsis_content = '\n\n'.join(tech_synopsis)
        else:
            technical_synopsis_content = tech_synopsis
            
        accomplishments_content = results.get("Accomplishments", {}).get('accomplishments', [])
        frustrations_content = results.get("Frustrations", {}).get('frustrations', [])
        tone_mood_content = results.get("Tone/Mood", {})
        discussion_notes_content = results.get("Discussion Notes", {}).get('discussion_notes', [])
        discussion_notes_simple_content = results.get("Discussion Notes Simple", {}).get('discussion_notes', [])
        commit_metadata_content = results.get("Commit Metadata", {}).get('commit_metadata', {})
        
        # Create journal entry
        timestamp = commit.committed_datetime.strftime("%I:%M %p").lstrip('0')
        
        # Fix tone_mood format - convert indicators list to string if needed
        tone_mood_formatted = None
        if tone_mood_content and (tone_mood_content.get('mood') or tone_mood_content.get('indicators')):
            indicators = tone_mood_content.get('indicators', '')
            if isinstance(indicators, list):
                indicators = '\n'.join(f"- {item}" for item in indicators)
            
            tone_mood_formatted = {
                'mood': tone_mood_content.get('mood', ''),
                'indicators': indicators
            }
        
        journal_entry = JournalEntry(
            timestamp=timestamp,
            commit_hash=commit.hexsha,
            summary=summary_content,
            technical_synopsis=technical_synopsis_content,
            accomplishments=accomplishments_content,
            frustrations=frustrations_content,
            tone_mood=tone_mood_formatted,
            discussion_notes=discussion_notes_content,
            discussion_notes_simple=discussion_notes_simple_content,
            commit_metadata=commit_metadata_content
        )
        
        # Write to file
        output_file = f"journal_entry_{commit_hash}.md"
        with open(output_file, 'w') as f:
            f.write(journal_entry.to_markdown())
        
        print(f"✅ Journal entry written to: {output_file}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()