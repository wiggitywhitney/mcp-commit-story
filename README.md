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

Here's an example daily summary, generated from real sample data:

```markdown
# 2025-05-28-daily.md

## Summary
A productive day focused on implementing the on-demand directory creation pattern and 
completing major architectural changes. The developer created an intelligent task 
archival system that reduced the active tasks.json file from 275KB to 62KB, addressing 
file size concerns. Task 25 was completed, implementing the MCP-first architecture 
decision by eliminating operational CLI commands. The day included multiple commits for 
on-demand directory creation, comprehensive test updates, and task management improvements.

## Key Accomplishments
The developer solved a practical file size problem by creating an archival system for 
completed tasks. After experiencing issues with Taskmaster MCP tools (resolved by 
refreshing), the developer created `scripts/archive_completed_tasks.py` to automatically 
archive complete task units, reducing the active task file significantly.

The architectural decision from Task 25 was implemented - removing operational CLI 
commands (`new-entry`, `add-reflection`) while keeping setup commands, and renaming the 
entry point to `mcp-commit-story-setup`. This reflects the insight that journal 
operations require AI analysis that humans cannot meaningfully perform manually.

Multiple commits advanced the on-demand directory creation pattern, replacing upfront 
directory creation with just-in-time creation using the `ensure_journal_directory` 
utility function.

## Technical Progress (Detailed Implementation)
- **Task Archival System**: Created `scripts/archive_completed_tasks.py` with validation 
  logic ensuring complete task units (main task + all subtasks marked "done") before 
  archival
- **File Size Optimization**: Reduced `tasks/tasks.json` from 275KB to 62KB, archived 
  12 complete task units while preserving 12 active tasks
- **Architectural Implementation**: Completed Task 25 - eliminated operational CLI 
  commands, renamed entry point to `mcp-commit-story-setup`, updated MCP server with 
  proper tool registration
- **Directory Pattern Implementation**: Completed on-demand directory creation pattern 
  with `ensure_journal_directory` utility, comprehensive TDD coverage, and removal of 
  all upfront directory creation logic

## Challenges Overcome
- **Taskmaster MCP Tool Issues**: Experienced timeout issues with Taskmaster MCP tools, 
  resolved by refreshing the connection
- **Import Path Complexities**: Encountered Python import issues during TDD 
  implementation requiring PYTHONPATH configuration and test structure adjustments
- **Test Coordination**: Required careful updates across CLI tests, integration tests, 
  and documentation to maintain consistency through architectural changes

## Learning & Insights
- **Psychology of Progress**: Visual task completion provides significant psychological 
  motivation - the developer noted satisfaction in seeing the task list shrink
- **File Size Impact**: Large task files create practical problems - the 275KB to 62KB 
  reduction addressed real usability issues
- **AI Tool Quality**: Switching to Claude 4 Sonnet provided dramatically better 
  development partnership and problem-solving capabilities

## Discussion Highlights
- **Human**: "Something went awry and the engineering spec got to be 6000+ lines long"
- **Human**: "Tbh it is really satisfying to see my list of open tasks get smaller. 
  I was already wishing for a way to visually see them getting checked off"
- **Human**: "I'm disappointed that the subtask plans in task 4 are not as detailed as 
  the ones in the planning doc"

## Developer Reflections
- **17:47**: "I switched to claude-4-sonnet and omg it is so much better, sweet baby 
  jesus"
- **18:47**: "I really like the discussion notes that Claude 4 Sonnet is capturing. 
  It adds a lot of color and interest. I want the most interesting of these to bubble 
  up into the daily summary. I also want the daily summary to include ALL manual 
  reflections, ver betim. These are gold."
```

---

## How Does It Work?

- **Automatic context collection:** The MCP server works with AI agents to pull in commit messages, code changes, terminal commands, and AI chat history, building a rich, evidence-based journal entry.
- **Granular section generation:** Each section of the journal entry (summary, accomplishments, frustrations, tone, terminal, discussion, commit details) is generated by a dedicated function that uses all available context—git commit info, terminal activity, and AI chat discussion—ensuring every section is as complete and accurate as possible.
- **No hallucinated summaries:** Everything in your journal is grounded in real actions and conversations.
- **Mood and emotion:** The journal reflects your mood and tone based on how you talk to the AI agent or what you write in commit messages—so if you vent, celebrate, or reflect, those feelings are captured authentically.
- **Summaries and threads:** Daily, weekly, monthly, and yearly summaries help you spot patterns, track progress, and find the stories worth sharing.

For a technical deep dive into the architecture, workflow, and engineering decisions behind MCP Commit Story, see the **[Technical Documentation](docs/)** which includes:

- **[Architecture Overview](docs/architecture.md)** - System design and architectural decisions
- **[MCP API Specification](docs/mcp-api-specification.md)** - Complete API reference for integration
- **[Implementation Guide](docs/implementation-guide.md)** - Development patterns and technical details
- **[Journal Behavior](docs/journal-behavior.md)** - How entries are generated and structured

For the complete engineering specification, see [engineering-mcp-journal-spec-final.md](engineering-mcp-journal-spec-final.md).

---

## The Story in Action

Bonnie, a developer, used MCP Commit Story for several months. When her manager asked about a past architecture decision, she didn't have to rely on memory or dig through old tickets. Her journal had the exact discussion, the alternatives considered, and the rationale—complete with the commands and tests that backed it up.

Later, Bonnie used her journal to write a conference talk. She found not just the technical steps, but the frustrations, breakthroughs, and lessons learned along the way. Her talk resonated because it was grounded in real experience, not just a list of features.

Over time, Bonnie's journal became a resource for performance reviews, onboarding new teammates, and even her own career growth. The value wasn't in any single entry, but in the cumulative story of her engineering journey.

---

## Unobtrusive by Design: Works Silently in the Background

MCP Commit Story is triggered automatically by a Git hook with each commit. It works silently in the background, capturing context and generating journal entries—plus daily, weekly, monthly, and yearly summaries—without disrupting your workflow. There's no need for manual intervention—just commit as usual, and your engineering story is recorded for you.

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
- **[Signal Format](docs/signal-format.md)** - File-based signaling mechanism for git hook to AI client communication
- **[On-Demand Directory Pattern](docs/on-demand-directory-pattern.md)** - File system organization patterns

#### **Implementation Patterns**
- **[AI Function Pattern](docs/ai_function_pattern.md)** - Patterns for AI-powered functionality integration
- **[Journal Initialization](docs/journal_init.md)** - Setup process and configuration management

#### **Complete Documentation Hub**
- **[Full Technical Documentation](docs/)** - All documentation organized by category and use case
