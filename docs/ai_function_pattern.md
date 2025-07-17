# AI Function Patterns

This codebase uses **two distinct AI function patterns** depending on the use case and context requirements. Understanding when and how to use each pattern is crucial for maintaining consistency and leveraging the appropriate AI integration approach.

---

## Pattern 1: Direct AI Invocation Pattern (Journal Generators)

**Use Case:** Journal section generation using direct AI API calls with structured context and parsing.

### How It Works
- Extract AI prompt from the function docstring using `inspect.getdoc()`
- Format the `JournalContext` as JSON and inject it into the prompt
- Make direct AI API calls using `invoke_ai()` with the formatted prompt
- Parse the AI response according to the expected output format (text, list, or complex)
- Return structured data with proper error handling and telemetry

### Implementation Pattern
```python
def generate_summary_section(journal_context: JournalContext) -> SummarySection:
    """[AI Prompt in docstring describing the task]"""
    try:
        # Extract prompt from docstring
        prompt = inspect.getdoc(generate_summary_section)
        
        # Format context as JSON and inject into prompt
        context_json = json.dumps(journal_context, indent=2, default=str)
        full_prompt = f"{prompt}\n\nThe journal_context object has the following structure:\n{context_json}"
        
        # Make direct AI call
        response = invoke_ai(full_prompt, {})
        
        # Parse response (simple text for summary)
        return SummarySection(summary=response.strip())
        
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        return SummarySection(summary="")  # Graceful fallback
```

### When to Use Pattern 1
- Journal section generation (summaries, insights, accomplishments)
- Content creation requiring git/chat context
- Tasks with well-defined output formats (text, list, complex parsing)
- Functions that need to work with `JournalContext` structure

### Benefits
- **Direct AI integration** with full context visibility
- **Structured parsing** for different output types (text, list, complex)
- **Graceful error handling** with fallback values
- **Telemetry integration** for monitoring and debugging
- **Consistent context formatting** across all journal generators

### Response Parsing Types
- **Simple text**: Use response directly (summary, technical_synopsis)
- **Simple list**: Split by newlines, strip, filter empty (accomplishments, frustrations)
- **Complex parsing**: Use regex/custom logic (tone_mood with mood/indicators)

### Example
```python
def generate_accomplishments_section(journal_context: JournalContext) -> AccomplishmentsSection:
    """Generate a list of accomplishments from the journal context..."""
    try:
        prompt = inspect.getdoc(generate_accomplishments_section)
        context_json = json.dumps(journal_context, indent=2, default=str)
        full_prompt = f"{prompt}\n\nThe journal_context object has the following structure:\n{context_json}"
        
        response = invoke_ai(full_prompt, {})
        
        # Parse as list: split by newlines, strip, filter empty
        accomplishments = [
            line.strip().lstrip('•').lstrip('-').strip() 
            for line in response.split('\n') 
            if line.strip()
        ]
        
        return AccomplishmentsSection(accomplishments=accomplishments)
        
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        return AccomplishmentsSection(accomplishments=[])
```

---

## Pattern 2: Direct AI API Call Pattern

**Use Case:** Specialized processing requiring **controlled AI behavior** with specific input/output contracts and validation.

### How It Works
- Construct prompts programmatically with specific input data and context
- Make direct API calls using `invoke_ai()` or AI provider functions
- Parse and validate AI responses with structured output contracts
- Return processed data immediately with full error handling
- Use `@trace_mcp_operation` decorator for comprehensive telemetry

### When to Use Pattern 2
- Complex analysis requiring specific input/output contracts
- Multi-step AI processing with validation and error handling
- Specialized filtering, boundary detection, or data transformation
- When AI needs structured response format (JSON, specific schemas)
- When you need immediate processing and cannot rely on agent context
- Analysis tasks requiring precise control over AI behavior

### Benefits
- **Controlled AI behavior** with validation and error handling
- **Structured input/output contracts** with type safety
- **Immediate processing** and return with no dependency on agent context
- **Full telemetry integration** for monitoring and debugging
- **Precise error handling** for production reliability

### Implementation Requirements
1. **Use telemetry decorator:** `@trace_mcp_operation("descriptive.operation.name")`
2. **Construct detailed prompts:** Include comprehensive context and explicit instructions
3. **Validate AI responses:** Parse and verify output format and content
4. **Handle errors gracefully:** Provide fallback behavior for AI failures
5. **Follow structured patterns:** Consistent approach across similar functions

### Example
```python
@trace_mcp_operation("ai_context_filter.filter_chat")
def filter_chat_for_commit(
    messages: List[ChatMessage], 
    commit: Commit, 
    git_context: Optional[Dict[str, Any]] = None
) -> List[ChatMessage]:
    """Use AI to filter chat messages to only those relevant to the commit.
    
    Analyzes the conversation to identify the boundary where work for the
    current commit begins, using AI to understand context and transitions.
    """
    if not messages:
        return []

    try:
        # Construct comprehensive prompt with all context
        prompt = construct_analysis_prompt(messages, commit, git_context)
        
        # Make direct AI API call
        ai_response = invoke_ai(prompt, {})
        
        # Parse and validate the structured response
        boundary_result = parse_ai_response(ai_response)
        
        # Validate bubbleId exists in messages
        if boundary_result['bubbleId'] not in {msg['bubbleId'] for msg in messages}:
            logger.warning(f"AI returned invalid bubbleId, using fallback")
            return messages  # Conservative fallback
        
        # Apply filtering based on AI decision
        return filter_messages_from_boundary(messages, boundary_result)
        
    except Exception as e:
        logger.error(f"AI filtering failed: {e}")
        return messages  # Conservative error handling
```

### Error Handling Pattern
```python
try:
    # AI processing
    result = invoke_ai(prompt, context)
    validated_result = parse_and_validate(result)
    return validated_result
except Exception as e:
    logger.error(f"AI operation failed: {e}")
    # Conservative fallback - return safe default
    return safe_fallback_value
```

---

## Choosing the Right Pattern

### Use Pattern 1 (Direct AI Invocation for Journal Generators) When:
- ✅ Journal section generation from `JournalContext`
- ✅ Content creation requiring structured context formatting
- ✅ Well-defined output formats (text, list, complex parsing)
- ✅ Functions that can gracefully fall back to empty/default values
- ✅ Working with git/chat/journal context data

### Use Pattern 2 (Direct AI API Call for Specialized Processing) When:
- ✅ Need controlled, predictable AI behavior with custom prompts
- ✅ Complex analysis requiring specific input/output contracts
- ✅ Multi-step processing with custom validation logic
- ✅ Functions requiring immediate processing with custom error handling
- ✅ Specialized filtering, boundary detection, or data transformation
- ✅ MCP tools requiring AI context capture or analysis
- ✅ Production systems requiring custom reliability patterns

### Examples in the Codebase

**Pattern 1 Usage:**
- `journal_generate.py` - All journal section generation functions
  - `generate_summary_section()`
  - `generate_accomplishments_section()`
  - `generate_frustrations_section()`
  - `generate_tone_mood_section()`
  - `generate_discussion_notes_section()`
  - `generate_technical_synopsis_section()`

**Pattern 2 Usage:**
- `ai_context_filter.py` - `filter_chat_for_commit()`
- `journal_handlers.py` - `generate_ai_context_dump()` (MCP context_capture tool)
- Boundary detection and chat filtering
- Structured analysis with custom validation

---

## Implementation Guidelines

### For Pattern 1 Functions:
- Keep docstrings comprehensive and self-contained (they become AI prompts)
- Include anti-hallucination rules and output format requirements in docstrings
- Use `inspect.getdoc()` to extract prompts from docstrings
- Format `JournalContext` as JSON consistently across all generators
- Implement proper response parsing for output type (text, list, complex)
- Return graceful fallback values on AI failures (empty strings, empty lists)
- Always use try/catch blocks around AI calls for error handling

### For Pattern 2 Functions:
- Always use appropriate telemetry decorators
- Implement comprehensive error handling
- Validate all AI responses before returning
- Provide conservative fallback behavior
- Document the specific AI behavior required

### Common Anti-Patterns:
- ❌ Mixing both patterns in a single function
- ❌ Inconsistent context formatting in Pattern 1 functions
- ❌ Missing error handling in Pattern 1 AI calls
- ❌ Skipping validation in Pattern 2 functions
- ❌ Missing telemetry on Pattern 2 functions
- ❌ Poor error handling in production Pattern 2 functions
- ❌ Hardcoding prompts instead of using docstrings in Pattern 1

This dual-pattern approach provides flexibility for different AI integration needs while maintaining consistency and reliability across the codebase. 