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
# 2025-05-24-daily.md

## Summary
A milestone day focused on formalizing the unified context model, implementing and testing all section generator scaffolds, and advancing the engineering journal MCP server's type safety and TDD rigor. The team completed foundational work on TypedDicts, section generator stubs, and comprehensive test fixtures, ensuring robust anti-hallucination compliance and future maintainability. All progress was meticulously tracked, with documentation, tests, and code kept in sync.

## Key Accomplishments
- Defined and documented TypedDicts for all context and section generator outputs (chat, terminal, git, journal, and all journal sections)
- Updated all context collection functions and downstream code to use the new types
- Implemented canonical AI-driven stubs for all section generators, each with a detailed, user-approved prompt and placeholder return
- Created comprehensive test fixtures and mock data for all section generators, covering edge cases and ensuring robust TDD
- Refactored journal entry structure to new canonical section order and renamed "Behind the Commit" to "Commit Metadata" throughout the codebase
- Updated engineering spec, PRD, and README to reflect the new unified context model and section order
- Added robust filtering of journal files to `collect_git_context` to prevent recursion and contamination
- Ensured all local/dev tests pass and AI/content tests are xfail as expected
- Maintained strict alignment between code, documentation, and Taskmaster task tracking

## Challenges Overcome
- Required careful coordination across code, tests, documentation, and task files to ensure consistency
- Addressed friction updating all references to renamed sections and new order
- Resolved test setup issues for git context filtering by ensuring all test files are created within the repo directory
- Managed complexity in scaffolding and testing all section generators in a single day

## Technical Progress
- 7+ commits made throughout the day
- Files changed: context_types.py, journal.py, git_utils.py, engineering-mcp-journal-spec-final.md, scripts/mcp-commit-story-prd.md, test_journal.py, test_journal_entry.py, test_git_utils.py, test_context_collection.py, summary_test_data.py, tasks.json, task_005.txt, README.md
- Test coverage: All structure, compliance, and placeholder tests passing; AI/content tests xfail as expected
- Major architectural improvements to section generator scaffolding, context model, and anti-hallucination safeguards

## Learning & Insights
- Canonical AI-driven function pattern (prompt in docstring, placeholder return) streamlines TDD and future AI integration
- Unified context model and strict type safety reduce errors and improve maintainability
- Comprehensive test fixtures and mock data are essential for robust, edge-case-driven TDD
- Filtering journal files from git context is critical for recursion prevention and narrative fidelity

## Mood & Tone Patterns
Overall mood: Thorough, systematic, and satisfied
Notable progression: Moved from foundational type/model work to broad implementation and test scaffolding, ending with robust, maintainable architecture
Emotional arc: Some friction with coordination and test setup, but resolved with methodical, best-practice solutions

## Decision Points
- Chose to formalize all context and section generator types before implementing content logic
- Opted for a unified context model and canonical section order for all journal entries
- Prioritized anti-hallucination compliance and test-driven development in all new code
- Added robust filtering to git context collection to prevent recursion

## Developer Reflections
No manual reflections were added to any entries today
```

---

## How Does It Work?

- **Automatic context collection:** The MCP server works with AI agents to pull in commit messages, code changes, terminal commands, and AI chat history, building a rich, evidence-based journal entry.
- **Granular section generation:** Each section of the journal entry (summary, accomplishments, frustrations, tone, terminal, discussion, commit details) is generated by a dedicated function that uses all available context—git commit info, terminal activity, and AI chat discussion—ensuring every section is as complete and accurate as possible.
- **No hallucinated summaries:** Everything in your journal is grounded in real actions and conversations.
- **Mood and emotion:** The journal reflects your mood and tone based on how you talk to the AI agent or what you write in commit messages—so if you vent, celebrate, or reflect, those feelings are captured authentically.
- **Summaries and threads:** Daily, weekly, monthly, and yearly summaries help you spot patterns, track progress, and find the stories worth sharing.

For a technical deep dive into the architecture, workflow, and engineering decisions behind MCP Commit Story, see the [engineering-mcp-journal-spec-final.md](engineering-mcp-journal-spec-final.md) document.

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

## Setup (CLI)

- `mcp-commit-story-setup journal-init` — Initialize the journal in your repo
- `mcp-commit-story-setup install-hook` — Install the post-commit hook

## Operational Workflow

All journal entry creation, reflection addition, and summarization are handled automatically by the MCP server and AI agent. There are no operational CLI commands for these tasks.

- Use the MCP server for all journal operations
- The AI agent is the primary interface for adding reflections, generating summaries, and managing journal entries

## Architecture Rationale

- Core functionality requires AI analysis and automation
- Simpler product, fewer interfaces to maintain
- Clear value proposition: "automatic engineering journal with AI analysis"
