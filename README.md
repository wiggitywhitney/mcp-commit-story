# MCP Commit Story: Your Engineering Journey, Remembered

## What is MCP Commit Story?

MCP Commit Story is a personal engineering journal for developers who want to capture not just what they built, but how it felt and why it mattered.  

It's a tool-in-progress, built by and for developers who care about the story behind the code.

MCP Commit Story runs as a Model Context Protocol (MCP) server, designed to work hand-in-hand with AI agents. These agents help gather and summarize the real context from your development workflow—so your journal entries are always grounded in what actually happened.

---

## Why Build This?

As a developer, it's easy to forget the "why" behind your work—what challenged you, what you learned, and how you grew.  
MCP Commit Story helps you:

- **Capture the narrative:** Each commit becomes a journal entry, recording not just the technical changes, but the decisions, frustrations, and small wins along the way.
- **Remember how it felt:** The journal includes mood and emotional context, so you can look back and see not just what you did, but how you experienced it.
- **Surface stories and insights:** By collecting real context from your workflow (AI Agent chat, terminal, code changes, commit messages), you can spot threads of challenge and triumph—perfect for blog posts, conference talks, or just understanding your own growth (no small thing!)
- **Support retrospectives and reviews:** Summaries and insights make it easier to reflect, ask for career advancement, or explain why certain choices were made.

---

## What Does a Day Look Like?

Here's an example daily summary, generated from real development data:

```markdown
# Daily Summary - June 4, 2025

## Summary
June 4th was a day of strategic evolution from "making it work" to "making it production-ready" - a journey that revealed the hidden complexities of building robust systems. The day progressed from adding comprehensive MCP best practices to breakthrough insights about AI orchestration patterns, culminating in the humbling realization that AI content quality requires more sophisticated approaches than initially anticipated. This represents the classic progression from proof-of-concept excitement to production engineering reality.

## Key Insights & Breakthrough Moments
**The Production Readiness Awakening**: Creating seven new production readiness tasks revealed the gap between "functional" and "deployable." The realization that issues like stdout pollution, performance validation, and logging infrastructure could break MCP client compatibility demonstrates how production systems require thinking beyond core functionality to operational excellence.

**AI Orchestration Architecture Insight**: The breakthrough that AI Function Pattern functions needed centralized orchestration rather than individual context detection represents a significant architectural insight. The discovery that calling AI functions directly always returned stubs, regardless of context, led to the realization that AI capability needs to be handled at the system boundary rather than embedded in individual functions.

**The Quality vs. Speed Trade-off Reality**: Multiple iterative attempts to improve AI content quality revealed the fundamental challenge of building reliable AI-powered systems. The discovery that AI agents needed increasingly explicit instructions to avoid shortcuts and hallucinations shows how AI system reliability requires different engineering approaches than traditional deterministic systems.

## Strategic Thinking Highlights
**Scope Management Evolution**: The tension between "thoroughness and scope creep" when adding production readiness tasks demonstrates mature project thinking. The recognition that MVP delivery requires balancing best practices against shipping velocity shows the evolution from technical perfectionism to product delivery focus.

**Architecture Pattern Discovery**: The AI orchestration solution established a reusable pattern for building AI-powered MCP tools. Rather than trying to make every function AI-aware, centralizing AI capability at the system boundary creates cleaner separation of concerns and more maintainable systems.

## Discussion Highlights
> **Human:** "Follow this task completion workflow for task 9"

This simple instruction led to discovering the value of systematic archival processes for maintaining development velocity and system performance.

> **Human:** "CLI Architecture: You suggest extending CLI with operational commands, but our current architecture is 'setup-only CLI' per the docs"

This correction revealed the importance of architectural consistency and how easy it is to drift from established patterns when planning new features.

> **User Reflection**: "I'm not happy with the summary generated... The recency bias problem persists and the AI seems to be taking shortcuts despite explicit instructions not to."

This honest assessment captures the ongoing challenge of building reliable AI systems - the gap between what we instruct AI to do and what it actually does in practice.

## Conference Talk Material
This day perfectly illustrates the evolution from "feature development" to "system engineering." The initial excitement of implementing MCP handlers and completing features gives way to the sobering realization that production systems require comprehensive infrastructure: logging, performance monitoring, error handling, and operational tooling.

The AI orchestration breakthrough demonstrates how architectural insights often come from implementation failures rather than theoretical design. The discovery that centralized AI orchestration works better than distributed AI awareness shows how real-world constraints drive architectural evolution.
```

---

## How Does It Work?

- **Background Generation:** Git commits automatically trigger journal entry creation that happens silently in the background. No workflow interruption, no waiting.
- **Rich Context Collection:** The system automatically pulls in commit messages, code changes, AI chat history, and your project's README, building a rich, evidence-based journal entry where the AI always understands your project's goals.
- **Intelligent Chat Collection:** Captures all AI conversations between commits using Cursor's AI chat, providing complete chronological context for each code change. See the [Chat Integration User Guide](docs/chat-integration-guide.md) for complete details.
- **AI Knowledge Preservation:** Capture AI assistant insights during development to enrich future journal entries. Prevents rediscovering the same solutions and builds a persistent knowledge base that grows with your project.
- **User Control:** While generation happens automatically, you control the context. Add manual reflections or capture your AI assistant's current knowledge directly into your journal.
- **No Hallucinated Summaries:** Everything in your journal is grounded in real actions and conversations.
- **Mood and Emotion:** The journal reflects your mood and tone based on how you talk to the AI agent or what you write in commit messages—so if you vent, celebrate, or reflect, those feelings are captured authentically.
- **Automatic Summaries:** Daily summaries are generated automatically, with weekly, monthly, quarterly, and yearly summaries planned to help you spot patterns, track progress, and find the stories worth sharing.

## AI Knowledge Preservation in Action

During AI-assisted development, valuable insights often emerge but get lost when the conversation ends. MCP Commit Story's AI Knowledge Preservation feature solves this with a simple workflow:

**Example Use Case:**
1. **Discovery**: You're debugging with your AI assistant and discover that React's useCallback should be used for expensive list computations to prevent re-renders
2. **Capture**: Use the `journal/capture-context` tool to save this insight: *"Use useCallback for expensive computations in list items - reduces rendering time by 60% in product catalogs"*
3. **Integration**: The insight is stored in your daily journal file with proper timestamp
4. **Enrichment**: When you commit your next React optimization, the journal generation system automatically includes this previous insight as context
5. **Result**: Your commit journal entry references the earlier discovery, creating richer documentation that builds on previous learning

This creates a continuous learning cycle where today's insights inform tomorrow's journal entries, preventing knowledge loss and building a persistent understanding of your project's evolving patterns and solutions.

For a technical deep dive into the architecture, workflow, and engineering decisions behind MCP Commit Story, see the **[Technical Documentation](docs/)** which includes:

- **[Architecture Overview](docs/architecture.md)** - System design and architectural decisions
- **[AI Context Capture Guide](docs/ai-context-capture-guide.md)** - Complete usage guide for knowledge preservation
- **[MCP API Specification](docs/mcp-api-specification.md)** - Complete API reference for integration
- **[Implementation Guide](docs/implementation-guide.md)** - Development patterns and technical details
- **[Journal Behavior](docs/journal-behavior.md)** - How entries are generated and structured

For the complete engineering specification, see [engineering-mcp-journal-spec-final.md](engineering-mcp-journal-spec-final.md).

---

## The Story in Action

Bonnie, a developer, used MCP Commit Story for several months. When her manager asked about a past architecture decision, she didn't have to rely on memory or dig through old tickets. Her journal had the exact discussion, the alternatives considered, and the rationale—complete with the commands and tests that backed it up.

Later, Bonnie used her journal to write a conference talk. She found not just the technical steps, but the frustrations, breakthroughs, and lessons learned along the way. Her talk resonated because it was grounded in real experience, not just a list of features.

Over time, Bonnie's journal became a resource for performance reviews, onboarding new teammates, and even her own career growth. The value wasn't in any single entry, but in the cumulative story of her engineering journey.

**Real Example:** The development of MCP Commit Story itself provides a concrete example of what this kind of documentation enables. Months of journal entries capturing the technical work, emotional journey, and architectural discoveries were transformed into ["Building a Castle on Unstable Ground: My Month of Misleading AI Advice"](blog-post-castle-unstable-ground.md) - a detailed account of discovering fundamental flaws in the original AI-guided architecture and the recovery process that led to a better system. The blog post demonstrates how automated journaling can capture not just what you built, but the complete story of why and how, including the failures and pivots that traditional documentation often omits.

---

## Background Generation: Capture Now, Process Silently

MCP Commit Story uses a git hook to automatically generate journal entries and daily summaries in the background after each commit. The system collects git context, extracts relevant AI chat history, loads recent journal entries, and includes your project's README to provide comprehensive context to a fresh AI agent that always understands your project's purpose and goals. This generates rich, contextually-aware journal entries without interrupting your workflow. You maintain full control by adding manual reflections or capturing your AI assistant's current context when needed.

---

## Why Use It?

- **For yourself:**  
  - Remember why you made certain choices, and how you overcame obstacles.
  - See your growth as a developer, not just a list of commits.
  - Reflect on your work with more honesty and clarity.

- **For content creation:**  
  - Identify threads of challenge and triumph to turn into blog posts, talks, or portfolio pieces.
  - Capture the real story behind your technical journey—perfect for developer advocacy, teaching, or sharing with your future self.

- **For retrospectives and reviews:**  
  - Quickly find evidence of your impact, challenges, and decisions.
  - Make performance reviews, career advancement, or team retrospectives more meaningful and less stressful.

---

## Project Status

This project is under active development by a solo developer.  
The core journal engine, context collection, and summary generation are being built and tested with a TDD-first approach.  
Installation and CLI instructions will be added as the tool matures.

---

## Prerequisites

### OpenAI API Key (Required for AI Features)

MCP Commit Story uses OpenAI's API to generate rich, contextual journal entries. To use the AI-powered features, you'll need:

1. **OpenAI API Key**: Visit [OpenAI Platform](https://platform.openai.com/api-keys) and create a new API key
2. **Set Environment Variable**:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

**Without an API key**: The system will still work, but journal entries will contain empty AI-generated sections (Summary, Technical Synopsis, etc.) while preserving the structural format and non-AI content.

**Cost**: The system uses OpenAI's cost-effective `gpt-4o-mini` model. Typical usage costs are minimal (usually under $1/month for active development).

---

## Getting Started

MCP Commit Story is still in early development and not yet ready for general use. If you're interested in engineering storytelling, developer experience, or just want to follow the project's progress, feel free to watch the repo or open an issue with your thoughts, questions, or suggestions. Your feedback and curiosity are welcome as the project evolves!

---

## License

MIT

---

**MCP Commit Story: Because your engineering work is more than just code.**

### Technical Details

#### **Start Here**
- **[Architecture Overview](docs/architecture.md)** - System design, architectural decisions, and component relationships
- **[Complete Engineering Spec](engineering-mcp-journal-spec-final.md)** - Comprehensive reference (900+ lines)

#### **API & Integration**
- **[MCP API Specification](docs/mcp-api-specification.md)** - Complete MCP operations, data formats, and client integration guide
- **[Implementation Guide](docs/implementation-guide.md)** - Development patterns, technical implementation, and best practices

#### **Core System Documentation** 
- **[Journal Core](docs/journal-core.md)** - Journal entry generation system, AI integration, and content guidelines
- **[Context Collection](docs/context-collection.md)** - Data gathering system, type definitions, and performance optimization
- **[Reflection Core](docs/reflection-core.md)** - Manual reflection addition with validation and telemetry
- **[Journal Behavior](docs/journal-behavior.md)** - Entry structure, configuration options, and generation workflow

#### **Observability & Monitoring**
- **[Telemetry](docs/telemetry.md)** - Comprehensive OpenTelemetry integration and monitoring
- **[Structured Logging](docs/structured-logging.md)** - JSON logging with trace correlation and sensitive data protection
- **[Multi-Exporter](docs/multi-exporter.md)** - OpenTelemetry exporter configuration with environment precedence

#### **Development & Testing**
- **[Testing Standards](docs/testing_standards.md)** - Complete testing strategy (532 tests, 80% coverage, TDD patterns)
- **[Server Setup](docs/server_setup.md)** - MCP server configuration and deployment guide
