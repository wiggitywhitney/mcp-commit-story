# Task 50: Direct Git Hook Journal Generation

**Description:** Convert git_hook_worker.py from signal-based to direct journal generation using existing infrastructure.

## Requirements

### 1. Replace Signal Creation with Direct Journal Calls
- **Current:** 3 `create_tool_signal_safe()` calls at lines 684, 700, 714
- **Change to:** Call `journal_workflow.generate_journal_entry()` directly
- **Preserve:** All existing error handling and telemetry patterns

### 2. Bridge Git Repository Data
- **Current:** `main()` receives repo path string
- **Needed:** Convert to commit object + config for `journal_workflow.generate_journal_entry()`
- Use existing git_utils.py for commit object lookup
- Use existing config.py for configuration loading

### 3. Maintain Graceful Operation
- Preserve "never block git operations" principle
- Keep all existing logging and telemetry patterns
- Add fallback handling if journal generation fails
- Use existing `*_safe()` wrapper pattern for new direct calls

## Verification Against Codebase

✅ **journal_workflow.generate_journal_entry() exists** - line 20 in journal_workflow.py  
✅ **Context collection ready** - context_collection.py, context_types.py complete  
✅ **AI generators exist** - journal_generate.py (standalone via Task 64)  
✅ **Git utilities available** - git_utils.py for commit object conversion  
✅ **Signal locations identified** - lines 684, 700, 714 in git_hook_worker.py  
✅ **Configuration system exists** - config.py for loading journal settings  
✅ **Error handling patterns established** - existing `*_safe()` wrapper functions  

**Missing:** CLI argument parsing (needs to be added to main())

## Dependencies

- **Task 64** must be complete (AI generator standalone operation)
- **Tasks 63, 65** as specified in original dependencies

## Design Decisions Made

1. **CLI Structure**: No CLI needed - focus only on replacing signals with direct calls
2. **Directory Detection**: Use current working directory (consistent with git_utils patterns)  
3. **Scope**: Remove CLI scope creep - manual journal generation belongs in MCP tools

## Detailed Subtask Plan

### Subtask 50.1: Create Direct Journal Generation Wrapper
**Objective**: Implement a safe wrapper function that converts git_hook_worker's repo path input into the commit object and config required by journal_workflow.generate_journal_entry().

#### TDD Steps:

1. **WRITE TESTS FIRST**
   - Create `tests/unit/test_git_hook_worker_journal_integration.py`
   - Test `generate_journal_entry_safe()` function
   - Test cases: successful generation, git repo detection failure, config loading failure, journal generation failure, None inputs
   - Mock `journal_workflow.generate_journal_entry()` to test integration
   - Test telemetry recording for both success and failure cases
   - **RUN TESTS - VERIFY THEY FAIL**

2. **IMPLEMENT FUNCTIONALITY**
   - Implement `generate_journal_entry_safe()` in `src/mcp_commit_story/git_hook_worker.py`
   - Convert repo path string to commit object using existing git_utils
   - Load configuration using existing config utilities
   - Call `journal_workflow.generate_journal_entry()` with proper parameters
   - Follow existing `*_safe()` wrapper patterns for error handling
   - Add comprehensive telemetry for generation attempts, success/failure rates, and timing
   - **RUN TESTS - VERIFY THEY PASS**

3. **DOCUMENT AND COMPLETE**
   - Add detailed docstring explaining the wrapper's role in bridging git hook and journal workflow
   - Document error handling approach and telemetry patterns
   - **Run the entire test suite and make sure all tests are passing**
   - Double check all subtask requirements are met before marking this subtask as complete
   - **MARK COMPLETE**

### Subtask 50.2: Replace Signal Creation with Direct Journal Calls
**Objective**: Remove the 3 create_tool_signal_safe() calls in git_hook_worker.py and replace them with direct calls to generate_journal_entry_safe(), eliminating the signal-based indirection.

#### TDD Steps:

1. **WRITE TESTS FIRST**
   - Extend `tests/unit/test_git_hook_worker_journal_integration.py`
   - Test that `main()` calls `generate_journal_entry_safe()` instead of `create_tool_signal_safe()`
   - Test cases: normal git hook operation, daily summary trigger, signal creation disabled
   - Mock all dependencies to verify the call flow
   - Test telemetry shows direct generation instead of signal creation
   - **RUN TESTS - VERIFY THEY FAIL**

2. **IMPLEMENT FUNCTIONALITY**
   - Replace the 3 `create_tool_signal_safe()` calls at lines 684, 700, 714 in `git_hook_worker.py`
   - Replace with calls to `generate_journal_entry_safe()` using appropriate parameters
   - Preserve all existing error handling and logging patterns
   - Update telemetry to reflect direct generation vs signal-based generation
   - Remove unused signal creation imports if no longer needed
   - **RUN TESTS - VERIFY THEY PASS**

3. **DOCUMENT AND COMPLETE**
   - Update function docstrings to reflect the direct generation approach
   - Remove any references to signal creation in comments
   - **Run the entire test suite and make sure all tests are passing**
   - Double check all subtask requirements are met before marking this subtask as complete
   - **MARK COMPLETE**

### Subtask 50.3: Integration Testing and Git Hook Worker Cleanup
**Objective**: Verify the complete standalone operation works end-to-end and remove the replaced signal creation code from git_hook_worker.py (comprehensive signal cleanup is handled by Task 54).

#### Steps:

1. **RUN FULL TEST SUITE**
   - Run entire test suite to ensure nothing broke after signal replacement
   - Document any test failures and fix them
   - Pay special attention to:
     - Git hook worker tests
     - Journal generation workflow tests  
     - Any tests that interact with signal creation
   - **VERIFY ALL TESTS PASS**

2. **VERIFY END-TO-END FUNCTIONALITY**
   - Test that journal generation works end-to-end with direct calls
   - Verify that git hook integration still functions correctly
   - Test error scenarios and graceful degradation
   - Confirm that no signals are created during operation
   - Use existing test infrastructure, don't create new test files

3. **CLEAN UP REPLACED CODE IN GIT_HOOK_WORKER.PY**
   - Remove the old `create_tool_signal_safe()` function if no longer used elsewhere
   - Remove unused signal-related imports from `git_hook_worker.py` (e.g., signal_management imports)
   - Remove any signal creation constants or configuration specific to git_hook_worker.py
   - **Note:** Comprehensive signal architecture cleanup is handled by Task 54

4. **DOCUMENT AND COMPLETE**
   - Update git_hook_worker.py module documentation to reflect direct generation approach
   - Document integration verification results
   - **Run the entire test suite one final time**
   - Update this task document to reflect implementation completion
   - Double check all subtask requirements are met before marking this subtask as complete
   - **MARK COMPLETE**

## Key Dependencies and Notes

- **Task 64** must be complete before 50.2 (AI generators must be standalone)
- Each subtask includes comprehensive telemetry implementation
- All subtasks follow TDD approach with tests before implementation
- Maintains "never block git operations" principle throughout
- Preserves all existing error handling patterns
- Git hook functionality remains exactly the same - just removes signal indirection

## Scope

This is **not** building new functionality. It's removing signal-based indirection from the existing git hook worker while maintaining exactly the same git hook behavior.

The core change: `create_tool_signal_safe()` → `journal_workflow.generate_journal_entry()` direct calls.