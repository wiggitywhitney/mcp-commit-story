import pytest
import re

# --- Minimal stubs for TDD ---
def agent_model_parse(md):
    if not md or not md.strip():
        raise Exception("Empty entry")
    entry = {}
    # Remove leading/trailing whitespace and split into lines
    lines = [line for line in md.strip().splitlines() if line.strip()]
    if not lines:
        raise Exception("Empty entry")
    first_line = lines[0]
    # Reflection entry
    if 'Reflection' in first_line:
        entry['is_reflection'] = True
        m = re.match(r'### ([\d:APM ]+) — Reflection', first_line)
        entry['timestamp'] = m.group(1) if m else None
        # Get the text after the heading
        entry['text'] = lines[1].strip() if len(lines) > 1 else ''
        return entry
    # Commit entry
    entry['is_reflection'] = False
    m = re.match(r'### ([\d:APM ]+) — Commit ([a-f0-9]+)', first_line)
    if not m:
        raise Exception("Malformed entry")
    entry['timestamp'] = m.group(1)
    entry['commit_hash'] = m.group(2)
    # Use the original md for section parsing
    summary_match = re.search(r'## Summary\s*(.+?)(\n## |\Z)', md, re.DOTALL)
    entry['summary'] = summary_match.group(1).strip() if summary_match else ''
    acc_match = re.search(r'## Accomplishments\s*([\s\S]+?)(\n## |\Z)', md)
    if acc_match:
        entry['accomplishments'] = [line.strip('- ').strip() for line in acc_match.group(1).splitlines() if line.strip()]
    else:
        entry['accomplishments'] = []
    frus_match = re.search(r'## Frustrations or Roadblocks\s*([\s\S]+?)(\n## |\Z)', md)
    if frus_match:
        entry['frustrations'] = [line.strip('- ').strip() for line in frus_match.group(1).splitlines() if line.strip()]
    else:
        entry['frustrations'] = []
    refl_match = re.search(r'## Reflections\s*([\s\S]+?)(\n## |\Z)', md)
    if refl_match:
        entry['reflections'] = [line.strip('- ').strip() for line in refl_match.group(1).splitlines() if line.strip()]
    else:
        entry['reflections'] = []
    return entry

def agent_model_generate_summary(md):
    match = re.search(r'## Summary\s*(.+)', md, re.DOTALL)
    if match:
        summary = match.group(1).strip()
        summary = re.split(r'\n## |\n### ', summary)[0].strip()
        return summary
    return ''
# --- End stubs ---

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


def test_agent_model_parse_daily_note():
    entry = agent_model_parse(DAILY_NOTE_MD)
    assert entry['timestamp'] == '2:17 PM'
    assert entry['commit_hash'] == 'def456'
    assert 'Implemented feature X' in entry['accomplishments']
    assert 'Spent hours debugging config' in entry['frustrations']
    assert entry['summary'].startswith('A friendly, succinct summary')
    assert entry['reflections'][0] == 'This was a tough one!'


def test_agent_model_parse_reflection():
    entry = agent_model_parse(REFLECTION_MD)
    assert entry['is_reflection']
    assert entry['timestamp'] == '4:45 PM'
    assert 'importance of clear error messages' in entry['text']


def test_agent_model_generate_summary():
    summary = agent_model_generate_summary(SUMMARY_MD)
    assert summary.startswith('Today was a productive day.')
    assert len(summary) > 100  # Should be lengthy, human-readable


def test_agent_model_handle_empty_entry():
    with pytest.raises(Exception):
        agent_model_parse(EMPTY_MD)


def test_agent_model_handle_malformed_entry():
    with pytest.raises(Exception):
        agent_model_parse(MALFORMED_MD) 