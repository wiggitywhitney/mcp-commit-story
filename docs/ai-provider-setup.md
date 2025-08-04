# AI Provider Setup

The system uses **OpenAI's API** for all AI operations.

## Setup

### Configuration

Add your OpenAI API key to `.mcp-commit-storyrc.yaml`:

```yaml
ai:
  openai_api_key: "${OPENAI_API_KEY}"  # Uses environment variable interpolation
```

### Environment Variable

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

## Quick Start

1. **Get API Key**: Visit [OpenAI API Keys](https://platform.openai.com/account/api-keys)
2. **Set Environment Variable**: `export OPENAI_API_KEY="your-key"`
3. **Update Config File**: Add the AI section to your `.mcp-commit-storyrc.yaml`

## Troubleshooting

### Common Issues

1. **Configuration Not Found**
   - Verify `.mcp-commit-storyrc.yaml` exists in your project root
   - Ensure the `ai` section is present with `openai_api_key` field

2. **Environment Variable Issues**
   - Verify the environment variable exists: `echo $OPENAI_API_KEY`
   - Restart your shell after setting the variable

3. **API Authentication Errors**
   - Verify your OpenAI API key is valid
   - Check that your OpenAI account has sufficient credits

## Best Practices

1. **Security**:
   - Never commit API keys to version control
   - Use environment variable interpolation in config
   - Rotate API keys regularly

2. **Configuration**:
   - Keep settings in `.mcp-commit-storyrc.yaml`
   - Use environment variables for sensitive values

## See Also

- [Server Setup](server_setup.md)
- [Implementation Guide](implementation-guide.md) 