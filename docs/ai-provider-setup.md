# AI Provider Setup Guide

This guide explains how to configure AI for the MCP Commit Story system. The system uses AI in two distinct patterns for different types of operations.

## AI Usage Patterns

The system employs **two distinct AI function patterns**:

1. **Pattern 1 (Direct AI Invocation for Journal Generators)**: Used for journal section generation. These functions extract prompts from docstrings, format context as JSON, and make direct calls to `invoke_ai()` with graceful error handling.

2. **Pattern 2 (Direct AI API Call for Specialized Processing)**: Used for specialized processing like chat filtering and boundary detection. These functions make direct API calls with structured validation and error handling.

For detailed information about these patterns, see the [AI Function Patterns documentation](ai_function_pattern.md).

## AI Provider

The system uses **OpenAI's API** for all AI operations.

## Setup

### Required Environment Variable

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Model Used

The system uses OpenAI's `gpt-4o-mini` model for all AI operations.

## OpenAI API Key Setup

1. **Get API Key**: Visit [OpenAI API Keys](https://platform.openai.com/account/api-keys)
2. **Set Environment Variable**: `export OPENAI_API_KEY="your-key"`
3. **Verify Setup**: The system will check for this variable when making AI calls

## Usage Context

### Pattern 1 Operations (Journal Generation)
- Summary generation
- Technical synopsis creation
- Discussion notes extraction
- Accomplishment identification

These operations leverage the AI agent's full conversational context and memory for rich, contextually-aware content generation.

### Pattern 2 Operations (Structured Processing)
- Chat history filtering (`filter_chat_for_commit`)
- Boundary detection in conversations

These operations make direct API calls to OpenAI for immediate, structured responses.

## Testing Your Setup

You can verify your OpenAI API key is working by running any AI-enabled function. If the `OPENAI_API_KEY` environment variable is missing, the system will raise a `ValueError`.

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Verify `OPENAI_API_KEY` environment variable is set
   - Check for typos in the variable name
   - Restart your shell/application after setting the variable

2. **API Authentication Errors**
   - Verify your OpenAI API key is valid
   - Check that your OpenAI account has sufficient credits
   - Ensure your API key hasn't expired

3. **Rate Limiting**
   - OpenAI has rate limits based on your account tier
   - Consider upgrading your OpenAI plan if you hit limits frequently

## Best Practices

1. **Security**:
   - Never commit API keys to version control
   - Use environment variables to store the API key
   - Rotate API keys regularly

2. **Performance**:
   - Monitor your OpenAI API usage and costs
   - The system uses `gpt-4o-mini` which is cost-effective for most operations

3. **Reliability**:
   - The system includes graceful degradation - if AI calls fail, journal generation continues with programmatic sections only

## See Also

- **[AI Function Patterns](ai_function_pattern.md)** - Detailed documentation of the two AI patterns
- **[Implementation Guide](implementation-guide.md)** - Development patterns and best practices 