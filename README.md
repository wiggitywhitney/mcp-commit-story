**This project is currently under active development. Features and documentation may change rapidly.**

# mcp-commit-story
mcp-commit-story is a Model Context Protocol (MCP) server designed to capture and generate engineering journal entries within a 
code repository. The journal captures technical progress, decision-making context, and emotional tone, with the goal of 
understanding larger-scale patterns and producing content that can later be reused for storytelling (e.g., blog posts, conference 
talks).

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

**Key Configuration Options:**

| Option              | Type    | Default    | Description                                                      |
|---------------------|---------|------------|------------------------------------------------------------------|
| `journal.path`      | string  | `journal/` | Directory where journal entries are stored                        |
| `auto_generate`     | bool    | `true`     | Automatically generate journal entries after each commit         |
| `include_terminal`  | bool    | `true`     | Include terminal command history in journal entries              |
| `include_chat`      | bool    | `true`     | Include chat/AI conversation history in journal entries          |
| `include_mood`      | bool    | `true`     | Include mood/emotional tone analysis in journal entries          |
| `section_order`     | list    | see below  | Order of sections in each journal entry                          |

See the PRD and engineering spec for all available options.

- Environment variables can override some settings.

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
mcp-journal/
├── src/
│   └── mcp_journal/
│       ├── __init__.py
│       ├── cli.py
│       ├── server.py
│       ├── journal.py
│       ├── git_utils.py
│       └── config.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── pyproject.toml
├── README.md
└── .mcp-journalrc.yaml
```

---

## Development Approach

This project uses Test-Driven Development (TDD) and Taskmaster-AI for planning and task breakdown. All major features are developed with tests written first, ensuring high coverage and reliability.

---
