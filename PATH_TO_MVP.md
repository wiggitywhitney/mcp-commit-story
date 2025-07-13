# Path to MVP

## Overview

This document outlines our strategy for getting mcp-commit-story to a minimum viable product (MVP) that can be demonstrated and shipped to beta testers. The goal is to deliver working software that validates the core value proposition without getting lost in architectural perfection.

## Core Value Proposition

**Automated development journaling powered by AI** - Git commits automatically trigger AI-generated journal entries that capture what you accomplished, how you felt, and what you learned during development sessions.

## MVP Definition

### Minimum for Presentation Demo
- **Task 50**: Git hook triggers standalone journal generation
- **Working end-to-end flow**: Commit code → AI analyzes changes → Journal entry appears in markdown file
- **2 useful MCP tools**: Manual reflections and AI context capture (not broken/redundant tools)

This alone demonstrates the complete value proposition and will impress colleagues.

### Stretch Goal for Beta Distribution
If time permits, extend to a downloadable package:
- **Task 67**: Code diff collection (dramatically improves journal quality)
- **Task 53**: Standalone daily summaries
- **Task 69**: Remove broken/obsolete MCP tools and signal architecture
- **Task 52**: YAML frontmatter for machine-readable metadata
- **Task 70**: pip-installable distribution with CLI setup

## Implementation Strategy

### Phase 1: Core Foundation (Required for Demo)
1. **Task 50** - Convert git hooks to standalone journal generation
   - Remove signal-based indirection
   - Direct calls to journal workflow
   - Preserves all existing quality and error handling

### Phase 2: Quality Enhancement (High Impact)
2. **Task 67** - Add code diff collection to git context
   - AI can see actual code changes, not just file names
   - Transforms journals from generic to specific technical commentary
   - Game-changing improvement for journal usefulness

3. **Task 53** - Standalone daily summaries
   - Convert existing MCP-based daily summaries to background generation
   - Benefits from enhanced git context from Task 67

### Phase 3: Architecture Cleanup (User Experience)
4. **Task 69** - Clean up obsolete MCP and signal architecture
   - Remove 4 broken/redundant MCP tools that would embarrass us in beta
   - Keep only `journal_add_reflection` and `journal_capture_context`
   - Eliminate signal-based code that's no longer needed
   - May be broken into smaller tasks when we reach it

### Phase 4: Polish (Nice to Have)
5. **Task 52** - YAML frontmatter for machine-readable journals
   - Enables tooling integration and analysis
   - Good for power users who want to analyze development patterns

6. **Task 70** - Package for distribution
   - Make it pip-installable
   - CLI for setup and configuration
   - External project initialization
   - Clean dependency management

## Decision Framework

### When to Ship vs. Continue
- **After Task 50**: Great demo, validates core concept
- **After Task 67**: Significantly better journal quality
- **After Task 53**: Complete standalone system
- **After Task 69**: Clean, professional beta experience
- **After Task 52**: Machine-readable journals with metadata
- **After Task 70**: Full production-ready distribution

### Stay on Track Principles
1. **Demo over perfection** - Task 50 alone is impressive and proves the concept
2. **User feedback over assumptions** - Real beta testers will tell us what matters
3. **Working software over architectural purity** - Ship functional tools, not perfect abstractions
4. **Iterative improvement** - Prompts and features can be refined through actual use

## Why This Approach Works

### Addresses Real Constraints
- **Presentation deadline** - Task 50 gives us a complete, impressive demo
- **Limited time** - Each task is independent, can ship at any point
- **Unknown user needs** - Beta feedback will guide what to prioritize next

### Avoids Common Traps
- **Feature creep** - Clear MVP definition prevents endless "just one more thing"
- **Architectural rabbit holes** - Focus on user value, not perfect code organization
- **Analysis paralysis** - Ship working software, improve based on real usage

### Maximizes Learning
- **Early validation** - Demo proves the concept works
- **Real feedback** - Beta testers reveal actual pain points
- **Iterative improvement** - Each task adds measurable value

## Success Metrics

### Demo Success
- [ ] Git commit triggers journal generation without manual intervention
- [ ] Generated journal entries are readable and useful
- [ ] No broken MCP tools visible to users
- [ ] Colleagues are impressed and want to try it

### Beta Success
- [ ] Users successfully install and set up the system
- [ ] Users generate journal entries through normal development workflow
- [ ] Users find the journal entries valuable enough to keep using the system
- [ ] Users provide feedback on what features matter most

## Remember

**The goal is learning what users actually want, not building what we think they need.** Every hour spent on architectural perfection before user feedback is potentially wasted. Get working software in front of real users as quickly as possible, then iterate based on their actual needs.

**This document exists to keep us focused on shipping value, not perfect code.**