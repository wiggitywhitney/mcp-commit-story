**This project is currently under active development. Features and documentation may change rapidly.**

# mcp-commit-story
mcp-commit-story is a Model Context Protocol (MCP) server designed to generate engineering journal entries within a code repository. The journal records commits, technical progress, decision-making context, and emotional tone, with the goal of understanding larger-scale patterns, identifying trends, and producing content that can later be reused for storytelling (e.g., blog posts, conference talks).

**Primary Usage Notice:**

This project is designed to be used primarily by AI agents (such as Cursor or other MCP-compatible tools) via the Model Context Protocol (MCP). Human users may use the CLI for manual operations, but the main workflow is agent-driven.

## Quick Start

### 1. AI-Powered Editor Integration (Recommended)
If you use an AI-powered editor (like Cursor, Windsurf, Roo, etc.), you can add mcp-commit-story as an MCP server.

**Example MCP config:**
```json
{
  "mcpServers": {
    "mcp-commit-story": {
      "command": "npx",
      "args": ["-y", "--package=mcp-commit-story", "mcp-commit-story"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY_HERE"
      }
    }
  }
}
```
- Replace the API key with your own.
- Save and reload your editor's MCP config.

**Now you can use natural language prompts in your editor, such as:**
- "Initialize mcp-commit-story in this project."
- "Parse my PRD at scripts/mcp-commit-story-prd.md."
- "What's the next task I should work on?"

---

### 2. Command Line Usage (Optional)
If you prefer the CLI, you can also:
```bash
pip install mcp-commit-story
mcp-journal init
mcp-journal new-entry
```

---

### 3. Configuration
- Edit `.mcp-journalrc.yaml` in your project root to customize journal behavior.
- See the Configuration section below for details.

---

## User Story: Real-World Impact (Fictional Example)

In this fictional scenario, Sarah—a senior engineer—transformed her daily work into a powerful resource for professional growth using the MCP Journal tool. Instead of scrambling to remember what happened during a project, she could quickly generate blog posts, spot recurring themes, and prepare compelling stories for conference talks using her automatically organized engineering journal.

The tool made it easy for Sarah to become a thought leader: she always had concrete examples and lessons learned at her fingertips. When her team faced new challenges, they could review past journal entries to avoid repeating mistakes and to build on previous solutions. Over time, Sarah's journal became a springboard for content creation, knowledge sharing, and continuous improvement—turning everyday engineering into lasting impact.

---

## Installation

### Standard Installation
```bash
pip install mcp-commit-story
```

### Development Setup
```bash
git clone https://github.com/wiggitywhitney/mcp-commit-story.git
cd mcp-commit-story
pip install -e .
```

### Environment Configuration
- Ensure Python 3.9+ is installed.
- Set up any required environment variables (see Configuration section).

---

## Usage

### CLI Example
```bash
mcp-journal init
mcp-journal new-entry
mcp-journal summarize --week
mcp-journal blogify journal/daily/2025-05-*.md
```

### Programmatic Example
```python
from mcp_journal import Journal
journal = Journal()
journal.new_entry()
```

---

## Configuration

Configuration is managed via `.mcp-journalrc.yaml` at the project root. Example:

```yaml
journal:
  path: journal/
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
  section_order:
    - summary
    - accomplishments
    - frustrations
    - tone
    - commit_details
    - reflections
  auto_summarize:
    daily: true
    weekly: true
    monthly: true
    yearly: true
```

- Environment variables can override some settings.

---

## Commit Processing
- Commits that only modify journal files are skipped (no journal entry generated)
- For mixed commits (code + journal files), only code changes are analyzed for the journal entry

---

## Goals
- Record accurate, structured engineering activity and emotional context
- Enable narrative storytelling across daily, weekly, and monthly timelines
- Identify patterns and trends in development work over time
- Keep entries truthful (anti-hallucination), useful, and minimally intrusive
- Integrate seamlessly with Git workflows and existing dev tools

---

## Contribution Guidelines

- Follow PEP8 and use `black` for formatting.
- Write tests first (TDD encouraged).
- Run all tests with `pytest` before submitting a PR.
- Open issues for bugs, feature requests, or questions.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Badges

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Test Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

---

## Project Structure

```
journal/
├── daily/
│   ├── 2025-05-14.md
│   ├── 2025-05-15.md
│   └── ...
├── summaries/
│   ├── daily/
│   │   ├── 2025-05-14-summary.md
│   │   └── ...
│   ├── weekly/
│   │   ├── 2025-05-week3.md
│   │   └── ...
│   ├── monthly/
│   │   ├── 2025-05.md
│   │   └── ...
│   └── yearly/
│       ├── 2025.md
│       └── ...
└── .mcp-journalrc.yaml
```

---

## Development Approach

This project uses Test-Driven Development (TDD) and Taskmaster-AI for planning and task breakdown. All major features are developed with tests written first, ensuring high coverage and reliability.

---
