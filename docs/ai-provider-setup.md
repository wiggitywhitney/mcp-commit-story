# AI Provider Setup Guide

This guide covers setting up and using the AI provider integration for journal generation in the mcp-commit-story project.

## Overview

The project uses OpenAI's API for AI-powered journal section generation. The integration is designed for simplicity and reliability, with graceful degradation when AI services are unavailable.

## Chosen Provider: OpenAI

**Selected Model**: `gpt-4o-mini`
- **Cost-effective**: Significantly cheaper than GPT-4 while maintaining good quality
- **Fast**: Quick response times suitable for git hook environments  
- **Reliable**: OpenAI has excellent API uptime and stability
- **Sufficient**: More than adequate for journal content generation

## Setup Instructions

### 1. Get an OpenAI API Key

1. **Create an OpenAI Account**:
   - Visit [platform.openai.com](https://platform.openai.com)
   - Sign up for an account or log in if you already have one

2. **Generate an API Key**:
   - Navigate to [API Keys](https://platform.openai.com/api-keys)
   - Click "Create new secret key"
   - Give it a descriptive name (e.g., "mcp-commit-story")
   - Copy the generated key (starts with `sk-...`)
   - **Important**: Store this key securely - you won't be able to see it again

3. **Add Billing Information** (if not already done):
   - Navigate to [Billing](https://platform.openai.com/account/billing)
   - Add a payment method
   - Consider setting usage limits to control costs

### 2. Configure API Key

#### For Local Development

Create a `.env` file in your project root:

```bash
# In project root directory
echo "OPENAI_API_KEY=your-api-key-here" >> .env
```

Make sure `.env` is in your `.gitignore` (it should already be there):
```bash
# Verify .env is ignored
grep -q "\.env" .gitignore && echo "✓ .env is properly ignored" || echo "⚠️  Add .env to .gitignore"
```

#### For CI/CD and Production

Set the environment variable in your deployment environment:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

For GitHub Actions, add it as a repository secret and reference it in your workflow.

### 3. Verify Setup

Test your setup by running the OpenAI provider tests:

```bash
# Make sure dependencies are installed
pip install -e .

# Run the OpenAI provider tests
python -m pytest tests/unit/test_openai_provider.py -v
```

If configured correctly, you should see all tests pass.

## API Interface

The AI integration provides two layers for journal generation:

### High-Level AI Invocation (Recommended)

Use the `invoke_ai` function for production calls with retry logic:

```python
from src.mcp_commit_story.ai_invocation import invoke_ai

# Make a robust call with retries and telemetry
response = invoke_ai(
    prompt="Summarize these changes", 
    context={"commit": "abc123", "diff": "git diff content"}
)
```

**Features:**
- **Retry Logic**: 3 attempts with 1-second delays for temporary failures
- **Smart Error Handling**: No retries for auth errors (they won't resolve)
- **Graceful Degradation**: Returns empty string on all failures
- **Telemetry**: Automatically traced with `@trace_mcp_operation("ai.invoke")`
- **30-Second Timeout**: Per attempt, suitable for git hooks

### Low-Level Provider (Direct Access)

For specialized use cases, access the OpenAI provider directly:

```python
from src.mcp_commit_story.ai_provider import OpenAIProvider

# Direct provider access (no retries)
provider = OpenAIProvider()
response = provider.call(prompt="Summarize these changes", context="git diff content")
```

### Method Signatures

#### High-Level Invocation Function

```python
def invoke_ai(prompt: str, context: Dict[str, Any]) -> str:
    """
    Call AI provider with retry logic and telemetry.
    
    Args:
        prompt: The instruction/question for the AI
        context: Dictionary with additional context data
        
    Returns:
        AI-generated response as string, or empty string on failure
        
    Features:
        - Retries up to 3 times on temporary failures
        - No retries on auth errors 
        - 30-second timeout per attempt
        - Automatic telemetry tracing
        - Graceful degradation logging
    """
```

#### Direct Provider Method

```python
def call(self, prompt: str, context: Union[str, Dict[str, Any]]) -> str:
    """
    Call OpenAI's API directly with a prompt and context.
    
    Args:
        prompt: The instruction/question for the AI
        context: Additional context (string or dictionary)
        
    Returns:
        AI-generated response as string, or empty string on failure
        
    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
```

### Error Handling

The provider is designed for **graceful degradation**:

- **Missing API key**: Raises `ValueError` during initialization
- **Network errors**: Returns empty string (allows journal generation to continue)
- **API errors**: Returns empty string (allows journal generation to continue)  
- **Timeouts**: Returns empty string after 30 seconds (suitable for git hooks)

This ensures that journal generation never fails completely due to AI service issues.

### Configuration

The provider uses these settings:

- **Model**: `gpt-4o-mini` (hardcoded for cost-effectiveness)
- **Timeout**: 30 seconds (suitable for git hook environments)
- **Temperature**: 0.7 (balanced creativity/consistency)
- **Max Tokens**: 2000 (sufficient for journal sections)

## Cost Estimation

Based on OpenAI's pricing for `gpt-4o-mini`:

- **Input**: $0.15 per 1M tokens
- **Output**: $0.60 per 1M tokens

**Typical usage for active development:**
- Journal generation: ~2-5 calls per commit
- Average prompt + response: ~1,000 tokens total
- Daily cost for 10 commits: ~$0.01-0.03
- **Monthly estimate**: $0.30-1.00 for regular development

This is very cost-effective for individual developers and small teams.

## Troubleshooting

### Common Issues

**1. "ValueError: OpenAI API key not found"**
- Ensure `OPENAI_API_KEY` is set in your environment
- Check for typos in the environment variable name
- Verify the API key starts with `sk-`

**2. "Empty responses from AI"**
- Check your OpenAI account has billing set up
- Verify API key has sufficient permissions
- Check OpenAI API status at [status.openai.com](https://status.openai.com)

**3. "Tests failing with network errors"**
- This is expected for unit tests (they use mocks)
- For integration testing, check your internet connection
- Verify firewall isn't blocking OpenAI API calls

### Debug Mode

To debug API calls, you can enable OpenAI's debug logging:

```python
import openai
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
openai.log = "debug"
```

## Integration with Journal Generation

The AI provider is automatically used by journal section generators that have AI prompts in their docstrings. The integration happens in:

1. **Layer 2**: Conversation reconstruction (Task 58)
2. **Layer 4**: AI-powered section generators (summary, accomplishments, frustrations, etc.)

The journal generation system will automatically detect which sections need AI and call the provider appropriately.

## Security Considerations

- **Never commit API keys**: Always use environment variables
- **Rotate keys regularly**: Consider rotating your OpenAI API key monthly
- **Monitor usage**: Set up usage alerts in your OpenAI dashboard
- **Limit scope**: Use separate API keys for different projects/environments

## Future Enhancements

This MVP implementation focuses on OpenAI integration. Future enhancements could include:

- Support for multiple providers (Anthropic, local models)
- Dynamic model selection based on content type
- Response caching to reduce API calls
- Cost optimization through prompt engineering

For now, the simple OpenAI integration provides reliable, cost-effective AI capabilities for journal generation.

## AI Function Executor

The AI Function Executor provides a powerful abstraction for executing journal generation functions using their docstrings as AI prompts. This allows for automatic conversion from stubbed functions to AI-powered implementations.

### Key Features

- **Docstring-Based Execution**: Uses function docstrings as AI prompts automatically
- **JSON Context Injection**: Provides journal context as structured JSON
- **Minimal Parsing Strategy**: Trusts AI responses with light parsing
- **Graceful Degradation**: Returns appropriate defaults on failures
- **Type-Safe Returns**: Returns correct TypedDict structures for each section

### Usage

#### Basic Execution

```python
from src.mcp_commit_story.ai_function_executor import execute_ai_function
from src.mcp_commit_story.journal import generate_summary_section

# Execute any journal function using its docstring as prompt
result = execute_ai_function(generate_summary_section, journal_context)
# Returns: SummarySection(summary="AI-generated summary")
```

#### Supported Function Types

The executor automatically handles all journal section types:

```python
# String sections
generate_summary_section -> SummarySection(summary: str)
generate_technical_synopsis_section -> TechnicalSynopsisSection(technical_synopsis: str)

# List sections  
generate_accomplishments_section -> AccomplishmentsSection(accomplishments: List[str])
generate_frustrations_section -> FrustrationsSection(frustrations: List[str])
generate_discussion_notes_section -> DiscussionNotesSection(discussion_notes: List[str])

# Complex sections
generate_tone_mood_section -> ToneMoodSection(mood: str, indicators: str)
generate_commit_metadata_section -> CommitMetadataSection(commit_metadata: Dict[str, str])
```

### Context Injection Format

The executor uses **JSON format** for context injection, providing clean object structure access:

```python
# Context is automatically formatted as:
context_json = json.dumps(journal_context, indent=2, default=str)
full_prompt = f"""{docstring}

The journal_context object has the following structure:
```json
{context_json}
```"""
```

This allows AI prompts to reference fields directly like `journal_context.git.metadata.message`.

### Parsing Strategy

The executor uses **minimal parsing** that trusts AI responses:

- **Single strings**: Use entire AI response (summary, technical_synopsis)
- **Lists**: Split by newlines with minimal cleanup (accomplishments, frustrations)
- **Complex types**: Simple pattern matching (tone_mood looks for "Mood:" and "Indicators:")
- **Metadata**: Parse key-value pairs separated by colons

### Default Values

On any failure, the executor returns **empty defaults** matching existing stub implementations:

```python
# Default return values for graceful degradation
SummarySection(summary="")
AccomplishmentsSection(accomplishments=[])
FrustrationsSection(frustrations=[])
ToneMoodSection(mood="", indicators="")
DiscussionNotesSection(discussion_notes=[])
CommitMetadataSection(commit_metadata={})
```

### Integration Example

Replace stub implementations with AI-powered versions:

```python
# Before: Stub implementation
def generate_summary_section(journal_context) -> SummarySection:
    return SummarySection(summary="")

# After: AI-powered implementation
def generate_summary_section(journal_context) -> SummarySection:
    """
    AI Prompt for Summary Section Generation
    
    Generate a narrative paragraph that captures the essential story
    of what changed and why, using conversational language.
    
    [Detailed AI prompt continues...]
    """
    from .ai_function_executor import execute_ai_function
    return execute_ai_function(generate_summary_section, journal_context)
```

### Error Handling

The executor provides comprehensive error handling:

- **Missing docstring**: Returns appropriate default for function type
- **AI invocation failure**: Returns default value, logs warning
- **Parse errors**: Returns default value, logs warning  
- **Unknown function types**: Returns empty dict, logs warning

All errors are gracefully handled to ensure journal generation continues.

### Performance

- **Single AI call** per function execution
- **30-second timeout** per call (from underlying invoke_ai)
- **Structured context** minimizes prompt size
- **Minimal parsing** reduces processing overhead

### Development Workflow

1. **Write detailed docstring** with AI prompt instructions
2. **Add function signature** with appropriate return type annotation
3. **Call execute_ai_function** from within the function
4. **Test with real context** to verify AI responses

This pattern enables rapid development of AI-powered journal functions while maintaining type safety and error resilience. 