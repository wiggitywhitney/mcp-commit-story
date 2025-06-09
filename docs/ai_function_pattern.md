# Canonical AI-Driven Function Pattern

All AI-driven functions in this codebase (including context collection and section generators) must follow this pattern:

- Place the canonical AI prompt in the function docstring. The prompt should fully describe the extraction/generation task, anti-hallucination rules, and output format.
- Return a placeholder value (e.g., an empty TypedDict or list, or an empty string for simple sections).
- Do not perform any logic or AI calls in the function body. The function is a contract for the AI agent.
- The AI agent, when invoked, reads the docstring and executes the instructions, returning the real value in place of the placeholder.

**AI Execution Model:**
When the AI agent encounters a function following this pattern during execution:
1. **Read the docstring** as the complete AI prompt/instruction set
2. **Execute the described task** using full conversational context and memory
3. **Return the real data** in the specified format instead of the placeholder
4. **Do NOT** execute the function body - treat it as a placeholder contract only

The function body serves only as a type hint and placeholder - the AI agent completely replaces the return value with actual generated content.

**Benefits:**
- Leverages the AI's full conversational context and memory (especially for chat/terminal history extraction).
- Avoids unnecessary serialization, prompt building, or API complexity.
- Ensures anti-hallucination and narrative fidelity by working directly with the real context.
- Provides a consistent, simple, and robust developer experience.

**Example:**
```python
def collect_chat_history() -> ChatHistory:
    """[Elaborate AI Prompt Here]"""
    return ChatHistory(messages=[])  # AI agent replaces this with real data

def generate_summary_section(journal_context: JournalContext) -> SummarySection:
    """[Elaborate AI Prompt Here]"""
    return SummarySection(summary="")  # AI agent replaces this with real data
```

This pattern is required for all new AI-driven functions in this project. 