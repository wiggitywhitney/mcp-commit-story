**This project is currently under active development. Features and documentation may change rapidly.**

# mcp-commit-story
mcp-commit-story is a Model Context Protocol (MCP) server designed to generate engineering journal entries within a code repository. The journal records commits, technical progress, decision-making context, and emotional tone, with the goal of understanding larger-scale patterns, identifying trends, and producing content that can later be reused for storytelling (e.g., blog posts, conference talks).

In addition to technical details, this journal system captures the emotional tone and context behind each engineering decision. By recording not just what happened, but how it felt, you'll be able to craft blog posts and conference talks that truly resonate with other engineers—turning dry changelogs into compelling stories of challenge, growth, and discovery.

**Primary Usage Notice:**

This project is designed to be used primarily by AI agents (such as Cursor or other MCP-compatible tools) via the Model Context Protocol (MCP). Human users may use the CLI for manual operations, but the main workflow is agent-driven.

## Badges

[![Build Status](https://github.com/wiggitywhitney/mcp-commit-story/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/wiggitywhitney/mcp-commit-story/actions/workflows/tests.yml)
<!-- [![codecov](https://codecov.io/gh/wiggitywhitney/mcp-commit-story/branch/main/graph/badge.svg)](https://codecov.io/gh/wiggitywhitney/mcp-commit-story) -->

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

She often included quick notes about her feelings—"I felt like an imposter all morning, but when my PR finally passed review, I wanted to high-five the whole team."—so her journal captured not just what she did, but how she experienced it.

When Bonnie prepared a blog post or conference talk, these emotional notes helped her transform technical summaries into engaging stories that connected with her audience and made her lessons memorable.

---
## Installation

```bash
pip install mcp-commit-story
```

## Configuration

A minimal configuration file is automatically generated when you initialize the project:

```bash
mcp-commit-story init
```

The configuration file `.mcp-commit-storyrc.yaml` contains essential settings:

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
    - ".mcp-commit-storyrc.yaml"  # Ignore config file itself

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
└── .mcp-commit-storyrc.yaml
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
