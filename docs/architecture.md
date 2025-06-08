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

## 4-Layer Journal Generation Architecture

The journal generation process follows a **4-layer architecture** with an orchestration layer that coordinates all operations:

### Layer 1: MCP Server (Delegation)
- **Entry Point**: `server.py` - MCP tool handlers
- **Responsibility**: Validate requests, delegate to orchestration layer
- **Key Function**: `handle_journal_new_entry()` → delegates to `orchestrate_journal_generation()`

### Layer 2: Orchestration (Coordination + Telemetry)
- **Module**: `journal_orchestrator.py` 
- **Responsibility**: Coordinate all phases with comprehensive telemetry
- **Key Functions**:
  - `orchestrate_journal_generation()` - Main orchestration with `@trace_mcp_operation`
  - `execute_ai_function()` - Individual AI function execution pattern
  - `collect_all_context_data()` - Context collection coordination
  - `assemble_journal_entry()` - Final assembly with validation
- **Features**:
  - Individual AI function calls (8 functions from journal.py)
  - Graceful degradation with specific fallbacks per section type
  - Comprehensive telemetry using `get_mcp_metrics()` and `record_counter()`
  - Error handling with categorization and contextual information

### Layer 3: Context Collection (Data Gathering)
- **Modules**: `context_collection.py`, `git_utils.py`
- **Responsibility**: Gather context from three sources with graceful degradation
- **Sources**:
  - **Git Context**: `collect_git_context()` (Python implementation - most reliable)
  - **Chat History**: `collect_chat_history()` (AI implementation - may fail)
  - **Terminal Commands**: `collect_ai_terminal_commands()` (AI implementation - may fail)
- **Fallback Strategy**: Always provides at least git context, gracefully handles failures

### Layer 4: Content Generation (Individual AI Functions)
- **Module**: `journal.py`
- **Responsibility**: Generate specific journal sections using AI
- **Functions** (8 individual AI function calls):
  - `generate_summary_section()`
  - `generate_technical_synopsis_section()`
  - `generate_accomplishments_section()`
  - `generate_frustrations_section()`
  - `generate_tone_mood_section()`
  - `generate_discussion_notes_section()`
  - `generate_terminal_commands_section()`
  - `generate_commit_metadata_section()`

### Orchestration Benefits

1. **Reliability**: Individual AI function calls with specific error handling
2. **Observability**: Comprehensive telemetry at every layer
3. **Graceful Degradation**: Continues operation even with partial failures
4. **Type Safety**: Full validation and fallbacks for each section type
5. **Performance**: Optimized context collection and AI execution patterns

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
# → Orchestration layer coordinates all operations
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
- **[Telemetry](telemetry.md)** - Observability and monitoring