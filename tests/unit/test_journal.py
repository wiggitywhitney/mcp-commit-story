import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from mcp_commit_story import journal

# Sample markdown for a daily note entry
DAILY_NOTE_MD = '''
### 2:17 PM — Commit def456

## Summary
A friendly, succinct summary that captures what was accomplished.

## Accomplishments
- Implemented feature X
- Fixed bug Y

## Frustrations or Roadblocks
- Spent hours debugging config

## Terminal Commands (AI Session)
- `git status`
- `pytest`

## Discussion Notes (from chat)
> "Should we use PostgreSQL or MongoDB? I'm leaning toward PostgreSQL because we need ACID compliance for financial data..."

## Tone + Mood (inferred)
> Mood: Focused and energized

## Behind the Commit
- Commit hash: def456
- Message: "feat: add feature X"
- Files touched: src/feature_x.py

## Reflections
- This was a tough one!
'''

# Sample markdown for a manual reflection entry
REFLECTION_MD = '''
### 4:45 PM — Reflection

Today I learned about the importance of clear error messages.
'''

# Sample markdown for a summary entry (lengthy, human-readable)
SUMMARY_MD = '''
## Summary
Today was a productive day. I implemented feature X, fixed a long-standing bug in the config system, and learned a lot about error handling. The main challenge was tracking down a subtle bug that only appeared in certain edge cases. After several hours of debugging, I finally identified the root cause and fixed it. I also spent some time refactoring the codebase to improve readability and maintainability. Overall, I'm happy with the progress made today and look forward to tackling the next set of features tomorrow.
'''

# Edge case: empty entry
EMPTY_MD = ''

# Edge case: malformed entry (missing required sections)
MALFORMED_MD = '## Accomplishments\n- Did something\n'


def test_parse_daily_note_entry():
    entry = journal.JournalParser.parse(DAILY_NOTE_MD)
    assert entry.timestamp == '2:17 PM'
    assert entry.commit_hash == 'def456'
    assert 'Implemented feature X' in entry.accomplishments
    assert 'Spent hours debugging config' in entry.frustrations
    assert entry.summary.startswith('A friendly, succinct summary')


def test_handle_empty_entry():
    with pytest.raises(journal.JournalParseError):
        journal.JournalParser.parse(EMPTY_MD)


def test_handle_malformed_entry():
    with pytest.raises(journal.JournalParseError):
        journal.JournalParser.parse(MALFORMED_MD) 