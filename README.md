**This project is currently under active development. Features and documentation may change rapidly.**

# mcp-commit-story
mcp-commit-story is a Model Context Protocol (MCP) server designed to generate engineering journal entries within a code repository. The journal records commits, technical progress, decision-making context, and emotional tone, with the goal of understanding larger-scale patterns, identifying trends, and producing content that can later be reused for storytelling (e.g., blog posts, conference talks).

**Primary Usage Notice:**

This project is designed to be used primarily by AI agents (such as Cursor or other MCP-compatible tools) via the Model Context Protocol (MCP). Human users may use the CLI for manual operations, but the main workflow is agent-driven.

## Badges

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Test Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

## Quick Start

### MCP Server Integration
The MCP server must be discoverable by compatible clients via a standard configuration mechanism. Here's an example configuration:

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
---

## User Story: Real-World Impact (Fictional Example)

In this fictional scenario, Bonnie—a senior engineer—transformed her daily work into a powerful resource for professional growth using the MCP Journal 
tool. Instead of scrambling to remember what happened during a project, she could quickly generate blog posts, spot recurring themes, and prepare 
compelling stories for conference talks using her automatically organized engineering journal.

The tool made it easy for Bonnie to become a thought leader: she always had concrete examples and lessons learned at her fingertips. When her team 
faced new challenges, they could review past journal entries to avoid repeating mistakes and to build on previous solutions. Over time, Bonnie's 
journal became a springboard for content creation, knowledge sharing, and continuous improvement—turning everyday engineering into lasting impact.

---
## Installation

```bash
pip install mcp-commit-story
```

## Configuration

A minimal configuration file is automatically generated when you initialize the project:

```bash
mcp-journal init
```

The configuration file `.mcp-journalrc.yaml` contains essential settings:

```yaml
# Journal settings
journal:
  # Base path for all journal files (relative to repo root)
  path: "journal/"

# Git repository settings
git:
  # Files to exclude from analysis in journal entries
  exclude_patterns:
    - "journal/**"        # Ignore journal directory to prevent recursion
    - ".mcp-journalrc.yaml"  # Ignore config file itself

# Telemetry settings
telemetry:
  # Whether to collect anonymous usage data
  enabled: false
```

If you want to customize your configuration before initialization, you can copy the provided example file.

## Commit Processing
- Commits that only modify journal files are skipped (no journal entry generated)
- For mixed commits (code + journal files), only code changes are analyzed for the journal entry
- This recursion prevention logic is always-on and not configurable

## Goals
- Record accurate, structured engineering activity and emotional context
- Enable narrative storytelling across daily, weekly, and monthly timelines
- Identify patterns and trends in development work over time
- Keep entries truthful (anti-hallucination), useful, and minimally intrusive
- Integrate seamlessly with Git workflows and existing dev tools

## Project Structure

```
journal/
├── daily/
│   ├── YYYY-MM-DD.md
│   └── ...
├── summaries/
│   ├── daily/
│   ├── weekly/
│   ├── monthly/
│   └── yearly/
└── .mcp-journalrc.yaml
```

## Development

### Setting Up Test Environment

This project follows Test-Driven Development (TDD) principles. To set up the test environment:

```bash
# Setup the test environment (creates virtual environment and installs dependencies)
./scripts/setup_test_env.sh

# Run tests
./scripts/run_tests.sh
```

For more details on testing standards and practices, see [Testing Standards](docs/testing_standards.md).

## License

MIT License. See [LICENSE](LICENSE) for details.
