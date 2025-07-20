#!/usr/bin/env python3
"""
Generate missing V2 daily summaries for sandbox journal entries.

This script identifies missing daily summaries in sandbox-journal/summariesV2/daily/
and generates them from corresponding journal files in sandbox-journal/daily/.
"""

import os
import sys
from datetime import datetime

# Add src to path to import modules
sys.path.insert(0, 'src')

from mcp_commit_story.daily_summary import generate_daily_summary_standalone, load_journal_entries_for_date, generate_daily_summary, save_daily_summary
from mcp_commit_story.config import Config

def create_sandbox_config():
    """Create a config object pointing to sandbox journal directory."""
    config_data = {
        'journal': {
            'path': 'sandbox-journal/',  # Point to sandbox instead of journal/
            'auto_generate': True,
            'include_terminal': True,
            'include_chat': True,
            'include_mood': True
        },
        'ai': {
            'openai_api_key': os.environ.get('OPENAI_API_KEY', '')
        },
        'git': {
            'exclude_patterns': ['journal/**', '.mcp-commit-storyrc.yaml']
        },
        'telemetry': {
            'enabled': False
        }
    }
    return Config(config_data)

def get_missing_dates():
    """Find dates that have journal files but no V2 summary."""
    # Get all journal dates
    journal_dir = 'sandbox-journal/daily'
    journal_files = [f for f in os.listdir(journal_dir) if f.endswith('-journal.md')]
    journal_dates = set()
    for f in journal_files:
        date_part = f.replace('-journal.md', '')
        journal_dates.add(date_part)

    # Get all existing V2 summary dates  
    summary_dir = 'sandbox-journal/summariesV2/daily'
    summary_files = [f for f in os.listdir(summary_dir) if f.endswith('-summary.md')]
    summary_dates = set()
    for f in summary_files:
        date_part = f.replace('-summary.md', '')
        summary_dates.add(date_part)

    # Find missing dates
    missing_dates = sorted(list(journal_dates - summary_dates))
    
    # Exclude the most recent date since it will be generated automatically by git hooks
    if missing_dates:
        most_recent = missing_dates[-1]  # Last date in sorted list
        missing_dates.remove(most_recent)
        print(f"ℹ️  Excluding {most_recent} (will be generated automatically by git hooks)")
    
    return missing_dates

def test_single_date(date_str):
    """Test summary generation for a single date."""
    print(f"\n=== Testing summary generation for {date_str} ===")
    
    try:
        # Create sandbox config
        config = create_sandbox_config()
        
        # Load journal entries
        print(f"Loading journal entries for {date_str}...")
        journal_entries = load_journal_entries_for_date(date_str, config)
        
        if not journal_entries:
            print(f"❌ No journal entries found for {date_str}")
            return False
        
        print(f"✅ Found {len(journal_entries)} journal entries")
        
        # Generate summary
        print(f"Generating daily summary...")
        summary = generate_daily_summary(journal_entries, date_str, config)
        
        # The save function expects summariesV2, but current logic goes to summaries
        # Let me check what path it actually generates
        print(f"Summary generated, saving...")
        
        # Create custom save path for V2 summaries
        summary_path = f"sandbox-journal/summariesV2/daily/{date_str}-summary.md"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        
        # Format and save manually to V2 location
        from mcp_commit_story.daily_summary import _format_summary_as_markdown
        content = _format_summary_as_markdown(summary)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Summary saved to {summary_path}")
        print(f"✅ Test successful for {date_str}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating summary for {date_str}: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_all_missing_summaries():
    """Generate summaries for all missing dates."""
    missing_dates = get_missing_dates()
    
    if not missing_dates:
        print("✅ No missing summaries found!")
        return
    
    print(f"Found {len(missing_dates)} missing summaries: {missing_dates}")
    
    successful = 0
    failed = 0
    
    config = create_sandbox_config()
    
    for i, date_str in enumerate(missing_dates, 1):
        print(f"\n[{i}/{len(missing_dates)}] Processing {date_str}...")
        
        try:
            # Load journal entries
            journal_entries = load_journal_entries_for_date(date_str, config)
            
            if not journal_entries:
                print(f"⚠️  No journal entries found for {date_str}, skipping")
                continue
            
            print(f"Found {len(journal_entries)} journal entries, generating summary...")
            
            # Generate summary
            summary = generate_daily_summary(journal_entries, date_str, config)
            
            # Save to V2 location
            summary_path = f"sandbox-journal/summariesV2/daily/{date_str}-summary.md"
            os.makedirs(os.path.dirname(summary_path), exist_ok=True)
            
            from mcp_commit_story.daily_summary import _format_summary_as_markdown
            content = _format_summary_as_markdown(summary)
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Summary saved to {summary_path}")
            successful += 1
            
        except Exception as e:
            print(f"❌ Error processing {date_str}: {e}")
            failed += 1
    
    print(f"\n=== Summary Generation Complete ===")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(missing_dates)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate missing V2 daily summaries")
    parser.add_argument("--test", help="Test with a specific date (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Generate all missing summaries")
    
    args = parser.parse_args()
    
    if args.test:
        test_single_date(args.test)
    elif args.all:
        generate_all_missing_summaries()
    else:
        # Default: test with first missing date
        missing_dates = get_missing_dates()
        if missing_dates:
            print(f"Testing with first missing date: {missing_dates[0]}")
            success = test_single_date(missing_dates[0])
            if success:
                print(f"\n✅ Test successful! Run with --all to generate all {len(missing_dates)} missing summaries")
            else:
                print(f"\n❌ Test failed. Please check the error above before proceeding.")
        else:
            print("✅ No missing summaries found!") 