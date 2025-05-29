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

## Migration from CLI-First

### What Changed

1. **Removed Commands**: `mcp-commit-story new-entry` and `mcp-commit-story add-reflection` 
2. **Renamed Entry Point**: `mcp-commit-story` → `mcp-commit-story-setup`
3. **Enhanced MCP**: All operational functionality moved to MCP server with proper tool registration

### What Stayed

1. **Setup Commands**: `journal-init` and `install-hook` remain in CLI for human setup
2. **All Functionality**: No features were removed, only relocated to appropriate interfaces
3. **Backward Compatibility**: MCP operations maintain same contracts and behavior

## Benefits

1. **Clearer Value Proposition**: Obvious separation between setup and operations
2. **Better Integration**: AI agents can use MCP operations without CLI complexity
3. **Reduced Confusion**: No ambiguity about which interface to use for what purpose
4. **Simplified Maintenance**: Smaller CLI surface area with focused responsibilities

## Usage Patterns

### Initial Setup (Human)
```bash
# One-time setup
mcp-commit-story-setup journal-init
mcp-commit-story-setup install-hook
```

### Operational Usage (AI/Automated)
```python
# AI agent via MCP
await mcp.call("journal/new-entry", {
    "git": git_context,
    "chat": chat_history,
    "terminal": terminal_commands
})
```

### Automated Journaling (Git Hook)
```bash
# Happens automatically after each commit
git commit -m "feat: implement new feature"
# → post-commit hook → MCP journal/new-entry → automated journal entry
```

This architecture ensures that:
- Humans handle setup once
- AI handles operations ongoing  
- Automation works seamlessly
- Integration is straightforward

---

## Related Documentation

- **[MCP API Specification](mcp-api-specification.md)** - Detailed MCP operations, data formats, and integration patterns
- **[Journal Behavior](journal-behavior.md)** - How journal entries are generated, structured, and configured
- **[Implementation Guide](implementation-guide.md)** - Technical implementation details, patterns, and development workflow
- **[Testing Standards](testing_standards.md)** - Testing approaches and quality standards
- **[On-Demand Directory Pattern](on-demand-directory-pattern.md)** - File system organization patterns 