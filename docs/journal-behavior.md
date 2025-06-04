# Journal Behavior and Content Generation

This document defines how the mcp-commit-story system generates journal entries, collects context, and structures content.

## Table of Contents

1. [Entry Triggering](#entry-triggering)
2. [Data Sources and Collection](#data-sources-and-collection)
3. [Chat History Collection](#chat-history-collection)
4. [Terminal Command Collection](#terminal-command-collection)
5. [Anti-Hallucination Rules](#anti-hallucination-rules)
6. [Recursion Prevention](#recursion-prevention)
7. [Journal Entry Structure](#journal-entry-structure)
8. [Content Quality Guidelines](#content-quality-guidelines)
9. [Configuration Options](#configuration-options)

---

## Entry Triggering

### Default Behavior
- **One journal entry per Git commit**
- Entries written to daily Markdown files, named `YYYY-MM-DD.md`
- Timestamps included per entry (e.g., `4:02 PM — Commit abc123`)
- Files appended in chronological order

### Automatic Generation
- Triggered by post-commit hook
- Can be manually triggered via MCP operations
- Backfill mechanism for missed commits

---

## Data Sources and Collection

### Required Data Sources
- Git commit message and metadata
- File diffs (simplified summaries with line counts)

### Optional Data Sources (if available)
- Chat history with dev agents
- Discussion excerpts from chat history showing decision-making context
- AI session terminal commands executed during the work session

### Collection Boundaries
- **Chat history**: From current commit backward until finding previous commit reference OR 150-message safety limit
- **AI session commands**: Commands executed by AI assistants during current work session
- **No filtering**: Include all commands/messages within boundaries

---

## Chat History Collection

### Primary Method
- AI scans backward through current conversation
- Uses AI's own chat history within the current session
- No external file access required

### Boundary Detection
- Look back until finding previous commit reference
- 150-message safety limit to prevent excessive scanning
- Stop at clear conversation boundaries

### Usage in Entries
- Inform summary, accomplishments, frustrations sections
- Include relevant discussion notes
- Capture decision-making context and tone/mood indicators

### Discussion Excerpts
- Include relevant conversation snippets in Discussion Notes section
- Show decision-making context
- Preserve speaker attribution when available

---

## Terminal Command Collection

### AI Session Commands
- **Primary method**: Directly prompt the AI assistant for terminal session history
- **Example prompts**: 
  - "Can you give me a history of your terminal session?"
  - "What commands did you execute during this work session?"
- **No file parsing or API integration required** - works through conversation
- Format commands chronologically as executed
- Deduplicate only adjacent identical commands (e.g., "npm test x3")

### Implementation Pattern
```python
def format_terminal_commands(commands):
    """Deduplicate adjacent identical commands"""
    if not commands:
        return []
    
    formatted = []
    current_cmd = commands[0]
    count = 1
    
    for cmd in commands[1:]:
        if cmd == current_cmd:
            count += 1
        else:
            formatted.append(f"{current_cmd} x{count}" if count > 1 else current_cmd)
            current_cmd = cmd
            count = 1
    
    # Add final command
    formatted.append(f"{current_cmd} x{count}" if count > 1 else current_cmd)
    return formatted
```

### Graceful Degradation
- Always attempt collection, but fail silently if unsupported
- When successful, provides rich context about problem-solving process
- When unavailable, journal entry proceeds without terminal section

---

## Anti-Hallucination Rules

### Core Principles
- Never infer *why* something was done unless evidence exists
- Mood/tone must be backed by language cues ("ugh", "finally", etc.)
- If data is unavailable (e.g., terminal history), omit that section
- Base all content on observable evidence from available data sources

### Evidence-Based Content
- Only include mood indicators when there are clear linguistic signals
- Discussion notes must be based on actual conversation content
- Technical details must be derived from commit data and file changes
- Accomplishments and frustrations should be evident from context

---

## Recursion Prevention

### Initial Filtering
- Examine all files in commit
- **If commit only modifies journal files** → skip journal entry generation entirely
- **If commit modifies both code and journal files** → proceed to create entry

### Content Generation
- When creating the entry content
- When generating file diffs and stats, exclude journal files from analysis
- Only show changes for non-journal files
- Allows journal files to be git-tracked while preventing recursive entries

### Built-in Behavior
- No configuration needed - this behavior is automatic
- Maintains clean journal content focused on actual development work

---

## Journal Entry Structure

### Canonical Format
```markdown
### {timestamp} — Commit {commit_hash}

## Summary
{summary text}

## Technical Synopsis
{technical details about code changes}

## Accomplishments
- {accomplishment 1}
- {accomplishment 2}

## Frustrations or Roadblocks
- {frustration 1}
- {frustration 2}

## Tone/Mood
> {mood}
> {indicators}

## Discussion Notes (from chat)
> **Human:** {note text}
> **Agent:** {note text}
> {plain string note}

## Terminal Commands (AI Session)
Commands executed by AI during this work session:
```bash
{command 1}
{command 2}
```

## Commit Metadata
- **files_changed:** {number}
- **insertions:** {number}
- **deletions:** {number}
```

### Section Rules
- All sections are omitted if empty
- Terminal commands are always rendered as a bash code block with a descriptive line
- Discussion notes are blockquotes; if a note is a dict with `speaker` and `text`, use `> **Speaker:** text`
- Multiline notes are supported
- Tone/Mood is only included if there is clear evidence and is always for the human developer only
- Render as two blockquote lines: mood and indicators
- Never hallucinate or assume mood; always base on evidence
- Markdown is the canonical format for all journal entries

---

## Content Quality Guidelines

### Focus on Signal vs. Noise

**Signal** (include):
- Unique decisions and their rationales
- Technical challenges encountered and solutions
- Emotional context that influenced work approach
- Lessons learned that weren't obvious at the start
- Insights gained during development

**Noise** (avoid):
- Routine process notes that are always true
- Standard workflow descriptions already documented
- Obvious statements that add no value

### Examples

#### Good (Signal)
- ❌ "Followed TDD methodology by writing tests first" (noise, standard practice)
- ✅ "Test-first approach revealed an edge case in the API response handler" (signal, specific insight)

- ❌ "Used git to commit changes" (noise, obvious from context)
- ✅ "Split work into three focused commits to separate concerns" (signal, shows thought process)

### Highlighting What's Unique

Each journal entry should capture what was distinctive about this development session:
- Technical challenges and how they were addressed
- Design decisions made and their rationales
- Insights gained that weren't obvious at the start
- Emotional context that influenced the work approach

The Summary section should focus on these unique aspects rather than restating routine workflow steps.

---

## Configuration Options

### AI Tone/Style Configuration

Control the tone and style of AI-generated summaries by setting the `ai_tone` field in `.mcp-commit-storyrc.yaml`.

#### Supported Values
- `neutral` (default): Objective, factual, and balanced. No strong personality.
- `concise`: Short, direct, and minimal. Focuses on brevity and essentials.
- `explanatory`: Clear, step-by-step, and focused on making things easy to understand.
- `technical`: Uses precise, domain-specific language. For advanced/engineering audiences.
- `reflective`: Thoughtful, introspective, and focused on lessons learned.
- `friendly`: Warm, encouraging, and positive—but still professional.

If an unsupported value is set, the system will fall back to `neutral` and log a warning.

#### Configuration Example
```yaml
journal:
  path: journal/
  ai_tone: reflective
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
  auto_summarize:
    daily: true
    weekly: true
    monthly: true
    quarterly: true
    yearly: true
```

### Auto-Summarization Options
- `daily`: Generate daily summary on first commit of new day
- `weekly`: Generate weekly summary on first commit of week (Monday)
- `monthly`: Generate monthly summary on first commit of month
- `quarterly`: Generate quarterly summary on first commit of quarter
- `yearly`: Generate yearly summary on first commit of year

### Content Inclusion Toggles
- `include_terminal`: Whether to attempt terminal command collection
- `include_chat`: Whether to scan for chat history
- `include_mood`: Whether to infer mood from available context

All inclusion options default to `true` but degrade gracefully if data is unavailable. 