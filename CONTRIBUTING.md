# Contributing to MCP Commit Story

This guide covers the complete development workflow, standards, and collaboration approach for the MCP Commit Story project. All contributors (human and AI) should read this to understand how to effectively work on this project and produce high-quality results.

## Essential Communication Pattern

**ALWAYS provide options, tradeoffs, and recommendations** when answering questions or making suggestions:

- **Options**: Present 2-3 clear alternatives with descriptive names
- **Tradeoffs**: Explain pros and cons for each option  
- **Recommendations**: State which option you recommend and why
- **Discussion**: Wait for response before proceeding to next question

**Example format:**
```
Options:
- Option A: [Description] 
  - Tradeoff: [Pro vs Con]
- Option B: [Description]
  - Tradeoff: [Pro vs Con]

My recommendation: Option A because [reasoning]

What's your preference?
```

This pattern is fundamental to productive collaboration and must be used consistently.

## Core Philosophy

### Development Approach
- **Solo OSS developer** valuing simple solutions over complex architectures
- **Zero users currently** - backwards compatibility is not a concern
- **Strict TDD methodology** - tests must be written before implementation
- **MVP-focused** - ship working software rather than pursue architectural perfection
- **Critical thinking preferred** - provide honest assessments, not just positive reinforcement

### AI Collaboration Model
- **Two AI system**: PAI (Planning AI) and IAI (Implementation AI) working with developer
- **Clear role separation**: PAI handles planning and design decisions, IAI handles implementation
- **Message composition**: Developer often asks PAI to compose messages to IAI with specific instructions
- **Flexible roles**: While PAI typically plans and IAI implements, either AI may take on different roles based on context

## Communication Style

### Question and Discussion Pattern
- **During planning discussions, ask ONE question at a time** - never present multiple design decisions simultaneously
- **When providing suggestions, provide options with tradeoffs** - present 2-3 options with clear pros/cons analysis
- **Include recommendations** - always state which option you recommend and why
- **Discuss before proceeding** - wait for developer response and discussion before moving to next question
- **Be concise** - avoid lengthy explanations, focus on essential information

### Response Style
- **Critical answers preferred** - honest assessment over diplomatic responses
- **Direct communication** - no unnecessary preamble or corporate speak
- **Concrete language** - specific problems and solutions rather than abstract buzzwords
- **External reader accessibility** - write so someone outside the project can understand

## Task and Subtask Planning

### Two-Phase Task Creation Workflow

**Phase 1: Create Parent Task**
- Create task file with complete header: ID, Title, Status, Dependencies, Priority, Description
- Write clear Requirements section (what needs to be accomplished)
- Add Notes section with any initial context or constraints
- Include "Design Decisions for Future Consideration" section for open questions
- **Do NOT create subtasks yet** - leave Subtasks section empty or with placeholder

**Phase 2: Design Discussion and Subtask Creation**
- Discuss design decisions [one question at a time](#essential-communication-pattern) 
- Update Notes section with "Design Decisions Made" as choices are finalized
- Requirements may evolve during design discussions - update them as understanding improves
- Convert Requirements section to checklist format once requirements are finalized
- Create detailed subtasks only after design decisions are resolved
- Use appropriate subtask structure ([TDD vs simplified](#subtask-structure-requirements) based on task type)
- Add [verification checklists](#good-subtask-implementation-plans) to all subtasks

This two-phase approach prevents AI from making premature design assumptions and ensures all implementation approaches are explicitly discussed and approved.

**Example**: See [Task 53 Gold Standard](#task-53-example) for a complete demonstration of this workflow.

### Planning Preferences
- **High-level approach first** - don't dive into implementation details immediately
- **Avoid over-engineering** - keep solutions simple and focused on working software
- **No prescriptive implementation details** - plan the what and why, leave the how for implementation
- **Design decisions during implementation** - don't lock in specific approaches ahead of time
- **MVP path focus** - prioritize shipping working software over architectural perfection
- **Use existing code when possible** - search codebase before creating new functionality
- **Verify assumptions with codebase** - check actual code instead of guessing what exists
- **Follow existing patterns** - examine similar implementations for consistency

### Subtask Structure Requirements

All subtasks must follow this exact pattern:

#### 1. GET APPROVAL FOR DESIGN CHOICES (if needed)
```
**PAUSE FOR MANUAL APPROVAL**: [Specific design choice 1]
**PAUSE FOR MANUAL APPROVAL**: [Specific design choice 2]
```
- Include this section only if design decisions are needed
- The developer prefers to answer design questions during planning phase rather than having pauses in implementation plans

#### 2. WRITE TESTS FIRST
```
- Create tests/[unit|integration]/test_[module_name].py
- Test [function_name]() function  
- Test cases: [specific scenarios - success, failures, edge cases]
- RUN TESTS - VERIFY THEY FAIL
```

#### 3. IMPLEMENT FUNCTIONALITY
```
- Implement [function_name]() in src/[module_path]/[file_name].py
- Handle all error cases identified in tests
- Include comprehensive telemetry with specific metrics/spans
- RUN TESTS - VERIFY THEY PASS
```

#### 4. DOCUMENT AND COMPLETE
```
- Add documentation in code docstrings
  1. Do not reference tasks
  2. Do not reference historical implementations or development processes  
  3. Write for the reader: A user with no prexisting project knowledge
- Do not remove existing information unless it's incorrect
- No approval needed - make documentation edits directly
- Run the entire test suite and make sure all tests are passing
- Verify that all requirements have been met
- Double check all subtask requirements are met before marking this subtask as complete
- MARK COMPLETE
```

### Task Structure Guidelines

**Requirements Section**: High-level "what" needs to be accomplished
- External contract - what deliverables must be produced
- Success criteria that can be verified by others
- Functional requirements that define completion
- Example: "Convert daily summary generation from MCP-based to standalone"

**Implementation Strategy Section**: Specific "how" approaches and technical details  
- Internal guidance for implementation choices
- Technical decisions already made during planning
- Specific files, functions, or patterns to use/follow
- Example: "Reuse 5 clean functions from daily_summary.py"

### Subtask Naming Convention
Follow the established pattern from existing tasks:
- **Subtask ID**: [TaskNumber].[SubtaskNumber] (e.g., 53.1, 53.2, 53.3)
- **Title**: Descriptive name for the subtask
- **Dependencies**: Clear dependency relationships
- **Description**: Brief overview of what the subtask accomplishes

### Standard Subtask Types
Most tasks should include these three boilerplate subtasks:
1. **Integration Testing** - End-to-end workflow testing plus robust telemetry validation
2. **Telemetry Verification** - Specific telemetry patterns and metrics validation  
3. **Documentation Updates** - Update all relevant documentation to reflect changes

**Important TDD Note**: Core code changes require strict TDD methodology (tests-first), but boilerplate subtasks should use simplified structure. **TDD is REQUIRED for**: creating/modifying application logic, adding new functions, changing business logic. **Simplified structure for**: integration testing, documentation updates, cleanup tasks, telemetry verification.

**Example**: See Task 53 subtasks below for a concrete example demonstrating this distinction between core code changes requiring TDD vs boilerplate subtasks.

## Telemetry Requirements

### Telemetry Philosophy
- **Datadog background** - developer works at Datadog and values robust but reasonable instrumentation
- **Instrument more than usual but sensibly** - detailed telemetry without over-engineering
- **Every subtask needs telemetry** - all new functionality must include appropriate telemetry

### Required Telemetry Components

#### Metrics
- **Duration histograms** for operations: `[component].[operation]_duration_seconds`
- **Operation counters** with success/failure labels: `[component].[operation]_total`
- **Error categorization** with specific error types
- **Performance correlation** tracking (e.g., context size vs duration)

#### Spans and Tracing
- **Operation tracing** with `@trace_mcp_operation` decorators
- **Semantic attributes** with component-specific context
- **Error capture** with proper error categorization
- **Trace continuity** through operation chains

#### Integration Testing
Follow the exact pattern from `docs/telemetry.md`:
- Use `TelemetryCollector` for isolated telemetry testing
- Use assertion helpers: `assert_operation_traced`, `assert_trace_continuity`, `assert_performance_within_bounds`
- Test both successful and error scenarios
- Validate trace relationships and span attributes

### Telemetry Standards Reference
See `docs/telemetry.md` for comprehensive telemetry implementation patterns, testing infrastructure, and best practices.

## Documentation Standards

### Core Principle
**Write for a future developer with zero project knowledge who needs to understand and modify this system.**

### Required Elements
- **Function-level docstrings** for all new functions following the core principle
- **Module-level docstrings** for new modules explaining their purpose and approach
- **Complete examples** that are copy-pasteable and work
- **Technical context** explaining why decisions were made when it affects future changes

### Documentation Updates for Code Changes
- **Evaluate existing documentation** before creating new files - determine if new information should be added to existing docs rather than creating separate files
- **When code is changed** (as opposed to net-new), these must be evaluated and updated if needed:
  - Documentation files
  - README.md
  - Engineering specifications
  - PRD (Product Requirements Document)

### Forbidden Content
- **Process references** - No task IDs, sprint numbers, team workflows
- **Historical narrative** - Skip "we tried X then Y" stories  
- **Assumed knowledge** - No insider team decisions or project history
- **Personal references** - No names, meetings, or timeline details

### Quality Test
**Could a new developer use this documentation successfully without asking questions?**

## Code Quality Standards

### Existing Code Usage
- **Use existing code when possible** - don't reinvent existing functionality
- **Don't add unneeded complexity** - simple solutions preferred
- **Follow existing patterns** - maintain consistency with established codebase patterns

### TDD Requirements
- **Tests before implementation** - this is non-negotiable
- **Test all error cases** - comprehensive error scenario coverage
- **Integration tests** - verify end-to-end workflows work correctly

## Anti-Patterns to Avoid

### Planning Anti-Patterns
- **Making design assumptions** instead of asking the developer
- **Over-engineering solutions** with unnecessary complexity
- **Prescriptive implementation details** that lock in approaches too early
- **Multiple questions at once** instead of one-at-a-time discussion
- **Guessing at existing functionality** instead of searching codebase
- **Asking questions answered by preferences** (e.g., "Should we use existing utilities?" - always yes)
- **Asking questions answered by existing code** (e.g., "What pattern should we follow?" - check similar implementations)

### Communication Anti-Patterns  
- **Abstract corporate speak** instead of concrete problem descriptions
- **Meaningless task references** instead of describing actual accomplishments
- **Diplomatic non-answers** instead of critical honest feedback
- **Lengthy explanations** when concise answers would suffice

### Implementation Anti-Patterns
- **Skipping tests** or writing implementation before tests
- **Missing telemetry** on new functionality
- **Poor documentation** that references development process instead of explaining functionality
- **Breaking existing patterns** instead of following established conventions
- **Forcing TDD on boilerplate subtasks** like integration testing, documentation, or cleanup tasks

## Success Indicators

### Good Planning Session
- Developer gets clear options with tradeoffs for each design decision
- One question at a time with productive discussion
- Recommendations are justified and helpful
- Final plan is implementable without further design decisions

### Good Subtask Implementation Plans
- Uses TDD pattern for core code changes (tests first, implementation, documentation)
- Uses simplified structure for boilerplate tasks (integration testing, documentation, cleanup)
- Includes specific telemetry requirements for the operation
- Has clear completion criteria and verification steps
- Can be executed by IAI without additional clarification

### Good Communication
- Developer gets honest, critical feedback when appropriate
- Complex topics are broken down into digestible pieces
- External readers could understand the context and decisions
- Focus stays on shipping working software rather than perfect architecture

## Parent Task Design Checklist

**Phase 1 - Initial Task Creation:**
[ ] Create task file with complete header (ID, Title, Status, Dependencies, Priority, Description)
[ ] Write clear Requirements section as bullet points (will convert to checklist in Phase 2)
[ ] Add Notes section with initial context or constraints
[ ] Include "Design Decisions for Future Consideration" section for open questions
[ ] **Search codebase for similar implementations** to understand existing patterns
[ ] **Verify existing utilities** before planning new functionality
[ ] Leave Subtasks section empty or with placeholder
[ ] Do NOT create subtasks yet

## Subtask Planning Checklist

**Phase 2 - Design Discussion and Subtask Creation:**
[ ] Discuss design decisions [one question at a time](#essential-communication-pattern)
[ ] Update Notes section with "Design Decisions Made" as choices are finalized
[ ] Update Requirements section as understanding improves
[ ] **Convert Requirements section to checklist format** once requirements are finalized
[ ] **Check existing code patterns** for similar subtask implementations
[ ] Create detailed subtasks only after design decisions are resolved
[ ] Use TDD structure for core code changes (WRITE TESTS FIRST → IMPLEMENT → VERIFICATION CHECKLIST)
[ ] Use simplified Steps structure for boilerplate tasks (integration testing, documentation, cleanup)
[ ] Add verification checklists to ALL subtasks using "[ ]" format (not "- [ ]")
[ ] Add "## Task Completion" section with "Final verification: [ ] All requirements above completed"

## Complete Task Example: Task 53

The following example demonstrates the complete two-phase workflow, proper task structure, TDD vs simplified subtask approaches, verification checklists, and requirements conversion from bullets to checklist format.

```markdown
# Task ID: 53
# Title: Refactor Daily Summary Generation
# Status: pending
# Dependencies: 67
# Priority: high
# Description: Refactor existing daily summary generation from MCP-based to background, non-MCP generation using the same standalone approach as journal entries.
# Requirements:
- Convert daily summary generation from MCP-based to standalone background generation
- Follow the same pattern established in Task 50 for journal entries
- Preserve all existing trigger logic and scheduling
- Maintain same output format and quality as MCP-based version
- Remove MCP dependencies while reusing existing helper functions where possible
- Update git hook integration to call standalone version instead of MCP-based version
- Implement comprehensive testing including unit, integration, and comparison testing
- Add robust telemetry for daily summary operations and performance tracking
- Update documentation to reflect standalone approach

# Notes:
## Design Decisions Made:
1. **Approach**: Create `daily_summary_standalone.py` with clean functions (Option B)
2. **Function Scope**: Copy 5 MCP-free functions, skip MCP wrapper (Option B)  
3. **Entry Point**: Create `generate_daily_summary_standalone(date=None)` (Option A)
4. **Git Hook Integration**: Preserve existing trigger logic, replace signal calls with direct calls (Option A)

## Implementation Strategy:
- Reuse 5 clean functions from `daily_summary.py`: `load_journal_entries_for_date()`, `save_daily_summary()`, `should_generate_daily_summary()`, `should_generate_period_summaries()`, `generate_daily_summary()` 
- Create main entry point that orchestrates the full workflow
- Add robust telemetry with specific metrics for operations, duration, and file operations
- Preserve all existing trigger logic and conditions

---

# Subtasks

---

## Subtask 53.1: Create Standalone Daily Summary Module
### Dependencies: None
### Description: Create daily_summary_standalone.py with core functions and standalone entry point, including robust telemetry for daily summary operations.

### Details:

#### WRITE TESTS FIRST
- Create `tests/unit/test_daily_summary_standalone.py`
- Test `generate_daily_summary_standalone()` function
- Test cases: successful generation with entries, successful generation with no entries, date parameter handling, configuration loading failure, journal entry loading failure, AI generation failure, file saving failure
- Test `load_journal_entries_for_date()`, `should_generate_daily_summary()`, `save_daily_summary()` functions work in standalone context
- Mock all external dependencies (file operations, AI generation, configuration)
- RUN TESTS - VERIFY THEY FAIL

#### IMPLEMENT FUNCTIONALITY
- Create `src/mcp_commit_story/daily_summary_standalone.py`
- Copy 5 clean functions from `daily_summary.py`:
  - `load_journal_entries_for_date()`
  - `save_daily_summary()`
  - `should_generate_daily_summary()`
  - `should_generate_period_summaries()`
  - `generate_daily_summary()` (core AI logic)
- Create `generate_daily_summary_standalone(date=None)` entry point that orchestrates the full workflow
- Add robust telemetry with specific metrics:
  - `daily_summary.generation_duration_seconds` (histogram) - total generation time
  - `daily_summary.operations_total` (counter) - operations with success/failure labels
  - `daily_summary.entry_count` (histogram) - number of journal entries processed
  - `daily_summary.file_operations_total` (counter) - file save operations
- Add telemetry spans with `@trace_mcp_operation("daily_summary.generate_standalone")`
- Include semantic attributes: `summary.date`, `summary.entry_count`, `summary.generation_type`
- Handle all error cases identified in tests with proper error categorization
- RUN TESTS - VERIFY THEY PASS

#### VERIFICATION CHECKLIST
[ ] Function `generate_daily_summary_standalone()` exists in `src/mcp_commit_story/daily_summary_standalone.py`
[ ] All 5 required functions copied from `daily_summary.py`: `load_journal_entries_for_date()`, `save_daily_summary()`, `should_generate_daily_summary()`, `should_generate_period_summaries()`, `generate_daily_summary()`
[ ] Test file `tests/unit/test_daily_summary_standalone.py` exists with all required test cases
[ ] All telemetry metrics implemented: `daily_summary.generation_duration_seconds`, `daily_summary.operations_total`, `daily_summary.entry_count`, `daily_summary.file_operations_total`
[ ] Telemetry spans implemented with `@trace_mcp_operation("daily_summary.generate_standalone")`
[ ] Module-level docstring added explaining standalone daily summary generation approach
[ ] Function-level docstrings added for all new functions (following documentation standards: no task references, no historical processes, external reader accessible)
[ ] Full test suite passes
[ ] All subtask requirements verified complete
[ ] MARK COMPLETE

[... remaining subtasks follow same pattern ...]

---

## Task Completion

Final verification:
[ ] All requirements above completed
```

## Task Archival Process

When a task is completely finished, follow this archival process:

**Step 1: Verify Completion**
[ ] All requirements in the task are met (check the Requirements checklist)
[ ] All subtasks are marked complete
[ ] Full test suite passes
[ ] All deliverables are working as specified

**Step 2: Archive Task File**
[ ] Move task file from `tasks/task_XXX.md` to `tasks/completed_tasks/task_XXX.md`
[ ] Preserve all task content and history in the archived file

**Step 3: Clean Up Dependencies**
[ ] Search all active task files in `tasks/` directory for dependencies on the completed task
[ ] Remove the completed task number from dependency lists of active tasks
[ ] Update any task descriptions that reference the completed task if needed

This process ensures completed work is preserved while keeping active task dependencies clean and accurate.

This guide should enable any AI instance to quickly understand the developer's working style and produce implementation plans that match their expectations and quality standards.