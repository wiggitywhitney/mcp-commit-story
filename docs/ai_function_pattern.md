# AI Function Patterns

This codebase uses **two distinct AI function patterns** depending on the use case and context requirements. Understanding when and how to use each pattern is crucial for maintaining consistency and leveraging the appropriate AI integration approach.

---

## Pattern 1: AI Agent Contract Pattern

**Use Case:** Journal section generation where the AI agent has **full conversational context** and memory.

### How It Works
- Place the canonical AI prompt in the function docstring. The prompt should fully describe the extraction/generation task, anti-hallucination rules, and output format.
- Return a placeholder value (e.g., an empty TypedDict or list, or an empty string for simple sections).
- Do not perform any logic or AI calls in the function body. The function is a contract for the AI agent.
- The AI agent, when invoked, reads the docstring and executes the instructions, returning the real value in place of the placeholder.

### AI Execution Model
When the AI agent encounters a function following this pattern during execution:
1. **Read the docstring** as the complete AI prompt/instruction set
2. **Execute the described task** using full conversational context and memory
3. **Return the real data** in the specified format instead of the placeholder
4. **Do NOT** execute the function body - treat it as a placeholder contract only

The function body serves only as a type hint and placeholder - the AI agent completely replaces the return value with actual generated content.

### When to Use Pattern 1
- Journal section generation (summaries, insights, accomplishments)
- Content creation requiring conversational context
- Tasks where AI agent's memory and ongoing conversation are valuable
- Simple extraction tasks with well-defined output formats

### Benefits
- Leverages the AI's full conversational context and memory (especially for chat/terminal history extraction).
- Avoids unnecessary serialization, prompt building, or API complexity.
- Ensures anti-hallucination and narrative fidelity by working directly with the real context.
- Provides a consistent, simple, and robust developer experience.

### Example
```python
def collect_chat_history() -> ChatHistory:
    """[Elaborate AI Prompt Here]"""
    return ChatHistory(messages=[])  # AI agent replaces this with real data

def generate_summary_section(journal_context: JournalContext) -> SummarySection:
    """[Elaborate AI Prompt Here]"""
    return SummarySection(summary="")  # AI agent replaces this with real data
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

### Use Pattern 1 (AI Agent Contract) When:
- ✅ AI agent has full conversational context
- ✅ Task benefits from ongoing conversation memory
- ✅ Simple, well-defined output format
- ✅ Content creation or narrative generation
- ✅ Working within an active AI conversation

### Use Pattern 2 (Direct AI API Call) When:
- ✅ Need controlled, predictable AI behavior
- ✅ Require structured input/output validation
- ✅ Complex analysis with specific processing requirements
- ✅ Need immediate processing independent of agent context
- ✅ Error handling and fallback behavior is critical
- ✅ Production systems requiring reliability

### Examples in the Codebase

**Pattern 1 Usage:**
- `journal.py` - All section generation functions
- Content creation for journal entries
- Narrative synthesis tasks

**Pattern 2 Usage:**
- `ai_context_filter.py` - `filter_chat_for_commit()`
- Boundary detection and chat filtering
- Structured analysis with validation

---

## Implementation Guidelines

### For Pattern 1 Functions:
- Keep docstrings comprehensive and self-contained
- Include anti-hallucination rules in prompts
- Specify exact output format requirements
- Return properly typed placeholder values

### For Pattern 2 Functions:
- Always use appropriate telemetry decorators
- Implement comprehensive error handling
- Validate all AI responses before returning
- Provide conservative fallback behavior
- Document the specific AI behavior required

### Common Anti-Patterns:
- ❌ Mixing both patterns in a single function
- ❌ Making API calls in Pattern 1 functions
- ❌ Skipping validation in Pattern 2 functions
- ❌ Missing telemetry on Pattern 2 functions
- ❌ Poor error handling in production Pattern 2 functions

This dual-pattern approach provides flexibility for different AI integration needs while maintaining consistency and reliability across the codebase. 