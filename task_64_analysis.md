# Task 64.1 Analysis: AI Invocation System

## Current Architecture Analysis

### How `ai_function_executor.py` Works
- **Purpose**: Abstraction layer that converts any function into an AI-powered generator
- **Process**: 
  1. Takes function + `JournalContext` parameters
  2. Extracts function docstring using `inspect.getdoc()`
  3. Formats context as JSON and appends to prompt
  4. Calls `invoke_ai()` from `ai_invocation.py`
  5. Parses response using function name to determine return type
  6. Returns appropriate TypedDict section type or defaults on failure

### Generator Functions and Return Types
**Location**: `src/mcp_commit_story/journal.py`

| Function | Return Type | Parsing Logic |
|----------|-------------|---------------|
| `generate_summary_section` | `SummarySection` | Single paragraph response |
| `generate_technical_synopsis_section` | `TechnicalSynopsisSection` | Single paragraph response |
| `generate_accomplishments_section` | `AccomplishmentsSection` | Split by newlines → list |
| `generate_frustrations_section` | `FrustrationsSection` | Split by newlines → list |
| `generate_tone_mood_section` | `ToneMoodSection` | Regex parsing for "Mood:" and "Indicators:" |
| `generate_discussion_notes_section` | `DiscussionNotesSection` | Split by newlines → list |
| `generate_commit_metadata_section` | `CommitMetadataSection` | Parse key:value pairs → dict |

### Telemetry Patterns Used
- All generators have `@trace_mcp_operation` decorators
- Telemetry helper functions in `journal.py`:
  - `_add_ai_generation_telemetry()` - records start time and context size
  - `_record_ai_generation_metrics()` - records duration, success/failure, error categories
- Standard attributes: `operation_type`, `section_type`, `ai.success`, `ai.latency_ms`

### Current Callers Analysis
**CRITICAL FINDING**: `ai_function_executor.py` is NOT actively used in the main workflow!

**Actual Usage**:
1. **`journal_workflow.py`** - Calls generators directly from `journal.py`
2. **`journal_orchestrator.py`** - Has its own `execute_ai_function()` that calls `ai_agent_call()` (placeholder)
3. **Tests only** - `ai_function_executor.py` is only imported by test files

**Files importing `ai_function_executor`**:
- `tests/unit/test_ai_function_executor.py` - Test suite
- `tests/unit/test_collect_recent_journal_context.py` - Compatibility tests
- **NO production code imports it!**

### Shared OpenAI Utilities Available
**`ai_invocation.py`** - Already provides what we need:
- `invoke_ai(prompt: str, context: Dict[str, Any]) -> str`
- Built-in retry logic (3 attempts, 1-second delays)
- Graceful degradation (returns empty string on failure)
- Telemetry tracking with `@trace_mcp_operation`
- Error handling for auth vs network failures

**`ai_provider.py`** - OpenAI API interface:
- Direct OpenAI client wrapper
- Uses GPT-4o-mini model
- Structures prompts as system/user messages
- 30-second timeout

### Current Generator Implementation Status
**All generators in `journal.py` are currently STUBS**:
- They have comprehensive docstrings with AI prompts
- They generate realistic placeholder content based on git context
- They do NOT use `ai_function_executor.py` or make real AI calls
- They preserve telemetry patterns and error handling

## Migration Strategy

### What Needs to Change
1. **Update 7 generator functions** to call `invoke_ai()` directly
2. **Remove `ai_function_executor.py`** file (only used by tests)
3. **Update test files** to import generators directly
4. **Preserve exact parsing logic** from `ai_function_executor.parse_response()`

### What Stays the Same
- All telemetry decorators and patterns
- Error handling and graceful degradation
- Function signatures and return types
- Docstring prompts (already comprehensive)
- The shared utilities (`ai_invocation.py`, `ai_provider.py`)

### Key Implementation Details
- **Prompt Format**: Use docstring + JSON context (same as current)
- **Parsing Logic**: Copy exact parsing from `ai_function_executor.parse_response()`
- **Error Handling**: Return same default values on failure
- **Telemetry**: Keep `_add_ai_generation_telemetry()` and `_record_ai_generation_metrics()`

## Parsing Requirements for Each Generator

### Simple List Generators
**Pattern**: Split by newlines, strip whitespace, filter empty lines
- `generate_accomplishments_section` → `AccomplishmentsSection(accomplishments=lines)`
- `generate_frustrations_section` → `FrustrationsSection(frustrations=lines)`  
- `generate_discussion_notes_section` → `DiscussionNotesSection(discussion_notes=lines)`

### Simple Text Generators  
**Pattern**: Use response text directly
- `generate_summary_section` → `SummarySection(summary=response)`
- `generate_technical_synopsis_section` → `TechnicalSynopsisSection(technical_synopsis=response)`

### Complex Parsing Generators
**Pattern**: Specialized parsing logic
- `generate_tone_mood_section` → Regex search for "Mood:" and "Indicators:" patterns
- `generate_commit_metadata_section` → Parse "key: value" pairs into dictionary

### Default Fallback Values
```python
# From ai_function_executor._get_default_result()
defaults = {
    "generate_summary_section": SummarySection(summary=""),
    "generate_technical_synopsis_section": TechnicalSynopsisSection(technical_synopsis=""),
    "generate_accomplishments_section": AccomplishmentsSection(accomplishments=[]),
    "generate_frustrations_section": FrustrationsSection(frustrations=[]),
    "generate_tone_mood_section": ToneMoodSection(mood="", indicators=""),
    "generate_discussion_notes_section": DiscussionNotesSection(discussion_notes=[]),
    "generate_commit_metadata_section": CommitMetadataSection(commit_metadata={})
}
```

## Migration Checklist for All Generators

### ✅ Completed
- [x] Created shared utility function for prompt formatting
- [x] Implemented `format_ai_prompt()` with TDD approach
- [x] All utility tests passing (5/5)

### 🔄 Next Steps (Subtask 64.2)
- [ ] Update simple list generators (accomplishments, frustrations, discussion_notes)
- [ ] Update simple text generators (summary, technical_synopsis)
- [ ] Update complex generators (tone_mood, commit_metadata)
- [ ] Remove `ai_function_executor.py` imports from tests
- [ ] Remove `ai_function_executor.py` file
- [ ] Update documentation

## Files to Modify
- `src/mcp_commit_story/journal.py` (7 generator functions)
- `tests/unit/test_ai_function_executor.py` (import updates)
- `tests/unit/test_collect_recent_journal_context.py` (import updates)
- `docs/ai_function_pattern.md` (documentation)

## Benefits After Refactoring
- **Simpler architecture** - removes abstraction layer
- **Direct OpenAI calls** - no interception or AI agent dependency
- **Better performance** - one less function call per generator
- **Easier debugging** - direct path from generator to AI
- **Maintained functionality** - same input/output behavior 