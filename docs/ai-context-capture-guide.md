# AI Context Capture Guide

*Preserve valuable AI insights between development sessions*

AI Context Capture solves a fundamental problem in AI-assisted development: valuable insights and knowledge generated during AI conversations get lost between sessions. Without a way to preserve this context, developers lose crucial understanding that could inform future decisions, architectural choices, and problem-solving approaches.

## The Problem

In AI-assisted development workflows, conversations with AI often generate:
- Deep insights about codebase architecture 
- Explanations of complex business logic
- Reasoning behind specific implementation decisions
- Understanding of system trade-offs and constraints
- Solutions to challenging technical problems

This knowledge is typically lost when:
- The AI conversation ends
- You switch between different development contexts  
- You return to work after time away from the project
- You collaborate with team members who weren't part of the original conversation

AI Context Capture provides a simple MCP tool that:
1. **Captures** valuable insights from your current AI conversation
2. **Stores** them in your daily journal under "AI Context Capture" sections
3. **Preserves** them for future reference and context building

## Quick Start

### Prerequisites
- MCP Commit Story journal system configured
- Access to MCP tools in your development environment (like Cursor)

### Basic Usage

**Capture context during an AI conversation:**
```bash
# In Cursor or other MCP-enabled environment
Use the "Capture Context" MCP tool with your insight:

"Just learned that the authentication system uses JWT tokens with 24-hour expiration. 
The refresh logic happens in src/auth/refresh.js and needs to handle edge cases 
where users might be offline when tokens expire."
```

**Result in your daily journal:**
```markdown
____

### 2:30 PM — AI Context Capture

Just learned that the authentication system uses JWT tokens with 24-hour expiration. 
The refresh logic happens in src/auth/refresh.js and needs to handle edge cases 
where users might be offline when tokens expire.
```

## Integration with Journal Workflow

AI Context Capture seamlessly integrates with the existing journal workflow:

1. **During Development**: Use the MCP tool to capture insights as they emerge
2. **Journal Generation**: Captured context automatically enriches future journal entries
3. **Context Building**: Previous captures provide valuable context for new AI conversations
4. **Knowledge Preservation**: Critical insights persist across development sessions

### Example Integration Flow

```bash
# 1. Working on feature, discover important insight
[AI conversation reveals complex caching behavior]

# 2. Capture the insight  
MCP Tool: "The Redis cache uses a 2-tier strategy: L1 is in-memory with 5min TTL, 
L2 is Redis with 1hr TTL. Cache invalidation happens via pub/sub on /cache/invalidate."

# 3. Continue development
[Insight is preserved in today's journal]

# 4. Later journal generation automatically includes this context
[New journal entries have richer context about caching decisions]

# 5. Future AI conversations can reference this preserved knowledge
[AI can build on previous understanding instead of starting from scratch]
```

## Architecture

The AI Context Capture feature operates through:

**MCP Tool Interface:**
- `journal/capture-context` - Primary capture tool
- Input: Text content to preserve  
- Output: Success confirmation with file location

**Storage Integration:**
- Appends to daily journal files (`journal/daily/YYYY-MM-DD-journal.md`)
- Uses consistent format with timestamp and separator
- Integrates with existing journal infrastructure

**Context Collection:**
- Journal generation automatically includes captured context
- Provides richer context for future AI conversations
- Builds cumulative knowledge base over time

## Best Practices

### When to Capture Context

**High-Value Scenarios:**
- Complex system explanations that took significant back-and-forth to understand
- Implementation decisions with important trade-offs
- Solutions to challenging technical problems  
- Discoveries about existing codebase architecture
- Understanding of business logic or domain-specific requirements

**Example Good Captures:**
```markdown
"Discovered that the payment processing system has a 3-step verification: 
1) Client-side validation, 2) Server-side amount verification, 3) External 
payment gateway confirmation. Step 2 happens in src/payment/verify.js and 
must complete within 30 seconds or the transaction fails."
```

### Capture Format Tips

**Be Specific:**
- Include file paths, function names, or system components
- Mention specific values, timeouts, or configuration details
- Reference actual code locations when relevant

**Provide Context:**
- Explain not just what, but why something works a certain way
- Include reasoning behind architectural decisions
- Note any important edge cases or constraints

**Keep it Concise but Complete:**
- Aim for 1-3 paragraphs maximum
- Include enough detail for future you to understand
- Focus on insights that aren't obvious from reading code alone

## Advanced Usage

### Bulk Context Capture
For extensive knowledge transfer sessions, capture multiple insights:

```bash
# Multiple captures during extended AI conversation
Capture 1: "Database schema insights..."
Capture 2: "API design patterns used..." 
Capture 3: "Testing strategy discoveries..."
```

### Integration with Development Workflow
```bash
# Pattern: Discovery → Capture → Implementation
1. Investigate complex system behavior with AI
2. Capture key insights as they emerge  
3. Implement solution using preserved knowledge
4. Knowledge persists for future reference
```

---

*The AI Context Capture system ensures valuable insights from AI conversations become permanent knowledge assets rather than ephemeral conversation artifacts.* 