# MCP Commit Story Architecture

## Overview

MCP Commit Story follows an **MCP-first architecture** with a minimal setup-only CLI. This design prioritizes automation and AI-agent integration over manual command-line operations.

## Architecture Rationale

### Why MCP-First?

1. **AI-Native Design**: Core journal functionality requires AI analysis of chat, terminal, and git context that humans cannot meaningfully perform manually
2. **Automation Focus**: The primary value proposition is "set and forget" automated journaling triggered by git commits
3. **Simplified Product**: Clear separation between setup (human) and operations (AI) reduces complexity and maintenance overhead
4. **Integration-Ready**: MCP protocol enables seamless integration with AI agents, IDEs, and development tools

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Setup CLI     │    │   MCP Server     │    │   Git Hooks     │
│  (Human Setup)  │    │ (AI Operations)  │    │  (Automation)   │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ journal-init    │    │ journal/new-entry│    │ post-commit     │
│ install-hook    │    │ journal/add-refl │    │ (triggers MCP)  │
└─────────────────┘    │ journal/init     │    └─────────────────┘
                       │ journal/install-h│
                       └──────────────────┘
```

## Setup CLI (Human Interface)

**Entry Point**: `mcp-commit-story-setup`

**Commands**:
- `journal-init`: Initialize journal configuration and directory structure
- `install-hook`: Install git post-commit hook for automated entries

**Purpose**: One-time setup tasks that require human decision-making and filesystem access.

## MCP Server (AI Interface)

**Operations**:
- `journal/new-entry`: Create AI-generated journal entries from git/chat/terminal context
- `journal/add-reflection`: Add manual reflections to existing entries
- `journal/init`: Programmatic journal initialization
- `journal/install-hook`: Programmatic hook installation

**Purpose**: Operational tasks designed for AI agents and automated workflows.

## Git Integration

**Post-Commit Hook**: Automatically triggers `journal/new-entry` via MCP after each commit, enabling fully automated journaling without human intervention.

## Usage Patterns

### Initial Setup (Human)
```bash
# One-time setup in a repository
mcp-commit-story-setup journal-init
mcp-commit-story-setup install-hook
```

### Operational Usage (AI/Automated)
```python
# Via MCP operations (AI agents, editors)
await mcp_client.call_tool("journal/new-entry", {
    "git": git_context,
    "chat": chat_context,
    "terminal": terminal_context
})

await mcp_client.call_tool("journal/add-reflection", {
    "reflection": "Today I learned about...",
    "date": "2025-01-15"
})
```

### Automated Journaling (Git Hook)
```bash
# Automatically triggered after each commit
git commit -m "Implement user authentication"
# → Triggers journal/new-entry via MCP
# → Creates journal/daily/2025-01-15.md entry
```

## Benefits

### For Development Teams
- **Automated Documentation**: No manual effort required for basic journaling
- **Rich Context**: Captures git, chat, and terminal context automatically
- **Consistent Format**: Standardized journal entries across all developers
- **Retrospective Ready**: Weekly/monthly summaries for sprint reviews

### For AI Integration
- **Native MCP Support**: Seamless integration with AI agents and IDEs
- **Structured Data**: Clear contracts for all operations
- **Telemetry Built-in**: Performance and usage analytics
- **Extensible**: Easy to add new journal operations

### For Individual Developers
- **Zero Friction**: Set once, works automatically
- **Rich Storytelling**: Transform technical entries into blog posts
- **Pattern Recognition**: Identify development patterns and blockers
- **Career Documentation**: Long-term record of accomplishments

## Related Documentation

- **[MCP API Specification](mcp-api-specification.md)** - Complete API reference
- **[Implementation Guide](implementation-guide.md)** - Technical implementation details
- **[Journal Behavior](journal-behavior.md)** - Content generation rules
- **[Server Setup](server_setup.md)** - Deployment and configuration
- **[Testing Standards](testing_standards.md)** - Quality assurance