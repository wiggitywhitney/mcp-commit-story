# AI Knowledge Capture Guide

## Overview

AI Knowledge Capture solves a fundamental problem in AI-assisted development: valuable insights and knowledge generated during AI conversations get lost between sessions. Without a way to preserve this knowledge, subsequent AI interactions start from scratch, missing important context about project decisions, patterns, and lessons learned.

This feature captures AI-generated project insights and automatically integrates them into your development journal, creating a persistent knowledge base that enriches future journal entries and development sessions.

## The Problem

During AI-assisted development, valuable insights emerge:
- Technical decisions and their reasoning
- Implementation patterns that work for your project
- Lessons learned from debugging sessions
- Best practices discovered through experimentation
- Architectural insights and trade-offs

Without preservation, this knowledge vanishes when the AI session ends, forcing you to rediscover the same insights repeatedly.

## The Solution

AI Knowledge Capture provides a simple MCP tool that:
1. **Captures** AI-generated insights about your project
2. **Stores** them in your daily journal under "AI Knowledge Capture" sections
3. **Enriches** future journal entries by including relevant captured knowledge as context

This creates a persistent knowledge repository that grows with your project.

## How to Use

### Capturing Knowledge

Use the `journal/capture-context` MCP tool to save important AI insights:

```
journal/capture-context with text: "Key insight about React state management: Use useCallback for expensive computations in list items to prevent unnecessary re-renders. This pattern reduces rendering time by 60% in our product catalog."
```

### When to Capture Knowledge

Capture knowledge when you discover:
- **Technical Solutions**: "Found that using Redis caching for product queries reduces database load by 40%"
- **Implementation Patterns**: "Error boundary pattern works best when placed at the route level for our architecture"
- **Debugging Insights**: "Memory leaks in our app were caused by event listeners not being cleaned up in useEffect"
- **Architecture Decisions**: "Chose microservices over monolith because team size and deployment complexity favor independent services"
- **Best Practices**: "Database migrations should always be backward compatible to enable zero-downtime deployments"

### Where Captured Knowledge Appears

Captured knowledge automatically appears in your journal in dedicated sections:

```markdown
### 2:30 PM — AI Knowledge Capture

Key insight about React state management: Use useCallback for expensive 
computations in list items to prevent unnecessary re-renders. This pattern 
reduces rendering time by 60% in our product catalog.
```

### How It Enriches Future Entries

When generating new journal entries, the system:
1. Scans recent captured knowledge from your journal
2. Includes relevant insights as context for AI generation
3. Creates richer, more informed journal entries that reference past learnings

## Example Workflow

**Morning Development Session:**
```
journal/capture-context with text: "Discovered that our API rate limiting works best with exponential backoff starting at 100ms. Linear backoff caused too many failed requests."
```

**Afternoon Commit:**
When you commit code related to API calls, your journal entry automatically includes context about the rate limiting insight, creating a comprehensive record of both what you implemented and why.

## Benefits

### Persistent Learning
- AI insights persist across sessions
- Build a knowledge base specific to your project
- Avoid rediscovering the same solutions

### Richer Journal Entries
- Future entries include relevant past insights
- More comprehensive development records
- Better context for understanding decisions

### Team Knowledge Sharing
- Captured insights are visible to team members
- Reduces knowledge silos
- Creates searchable development wisdom

### Decision Documentation
- Important technical decisions are preserved
- Reasoning behind choices is maintained
- Future developers understand the "why" behind code

## Integration with Journal System

AI Knowledge Capture seamlessly integrates with the existing journal workflow:

- **Daily Journal Files**: Captured knowledge appears in your regular daily journal files
- **Automatic Context**: The journal generation system automatically includes relevant captured knowledge
- **Consistent Format**: Uses the same timestamp and section formatting as other journal entries
- **Git Integration**: Knowledge captures are preserved alongside code commits

## Best Practices

### What to Capture
- **Be Specific**: Instead of "React is good", capture "React's useCallback prevents unnecessary re-renders in our 1000-item product list"
- **Include Context**: Mention specific files, functions, or scenarios where insights apply
- **Capture Trade-offs**: "Chose PostgreSQL over MongoDB because our data is highly relational, though MongoDB would be faster for simple queries"

### When to Capture
- **After Solving Complex Problems**: Document the solution and reasoning
- **During Architecture Decisions**: Record why you chose one approach over another
- **When Learning New Patterns**: Save patterns that work well for your specific project
- **After Performance Optimizations**: Document what worked and the impact

### Writing Effective Captures
- Use concrete metrics when possible: "Reduced load time by 200ms"
- Mention specific technologies: "Using Redis for session storage"
- Include negative learnings: "Tried approach X but it caused Y problem"
- Reference specific code locations when relevant

## Technical Details

The AI Knowledge Capture feature operates through:
- **MCP Tool**: `journal/capture-context` for manual knowledge capture
- **Journal Integration**: Automatic inclusion in daily journal files
- **Context Collection**: Retrieval of relevant knowledge for future journal generation
- **File Management**: Seamless integration with existing journal file structure

Captured knowledge follows the same file organization and timestamp formatting as regular journal entries, ensuring consistency across your development documentation. 