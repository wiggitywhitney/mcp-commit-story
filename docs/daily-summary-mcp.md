# Daily Summary MCP Tool

## Overview

The Daily Summary MCP Tool (`journal/generate-daily-summary`) automatically generates comprehensive daily summaries from journal entries using AI. This tool synthesizes a full day's worth of development work into structured summaries with 8 standardized sections.

## Key Features

- **AI-Powered Synthesis**: Uses sophisticated AI prompts to analyze and summarize journal entries
- **8-Section Structure**: Standardized format covering all aspects of development work
- **Manual Reflection Preservation**: Prioritizes and preserves user-written reflections verbatim
- **File-Creation Trigger System**: Smart logic to determine when summaries should be generated
- **Robust Error Handling**: Graceful handling of missing entries, file system errors, and invalid dates
- **Telemetry Integration**: Full spans and tracing for monitoring and debugging

## MCP Tool Schema

### Request: `GenerateDailySummaryRequest`
```typescript
{
  date: string;  // Required: YYYY-MM-DD format
}
```

### Response: `GenerateDailySummaryResponse`
```typescript
{
  status: "success" | "no_entries" | "error";
  file_path: string | "";     // Path to generated summary file
  content: string | "";       // Markdown content of summary
  error: string | null;       // Error message if status is "error"
}
```

## Summary Structure

Each daily summary contains 8 standardized sections:

1. **Summary** - High-level overview of the day's work
2. **Reflections** - Manual user reflections (preserved verbatim) + AI insights
3. **Progress Made** - Concrete accomplishments and completed work
4. **Key Accomplishments** - Most significant achievements as bullet points
5. **Technical Synopsis** - Technical details, implementations, and architecture decisions
6. **Challenges and Learning** - Problems encountered and knowledge gained
7. **Discussion Highlights** - Important conversations and decision points
8. **Tone/Mood** - Emotional context and team dynamics
9. **Daily Metrics** - Quantitative measures (commits, files, time spent)

## Implementation Details

### Core Functions

- **`generate_daily_summary_mcp_tool()`** - Main MCP handler
- **`generate_daily_summary()`** - Core AI generation logic  
- **`load_journal_entries_for_date()`** - Loads entries for specified date
- **`save_daily_summary()`** - Saves summary to markdown file
- **`_extract_manual_reflections()`** - Extracts user reflections with regex
- **`_call_ai_for_daily_summary()`** - AI generation with comprehensive prompts

### AI Prompt Engineering

The tool uses a 100+ line sophisticated AI prompt with:
- **Content Quality Guidelines**: Rules for rich, thoughtful summaries
- **Anti-Hallucination Rules**: Strict requirements for evidence-based content
- **Section-Specific Instructions**: Detailed requirements for each summary section
- **Formatting Standards**: Consistent markdown output structure

### File Creation Triggers

Smart logic determines when to generate summaries:
- **Triggered by**: New journal file creation
- **Analyzes**: Most recent previous date without existing summary
- **Prevents**: Duplicate generation and unnecessary processing

### Error Handling

Robust error handling for common scenarios:
- **No Entries Found**: Returns `status="no_entries"` (not an error condition)
- **Invalid Date Format**: Validates YYYY-MM-DD format
- **File System Errors**: Graceful handling of permission and path issues
- **AI Generation Failures**: Fallback to mock responses for testing

## Usage Examples

### Basic Usage
```python
from mcp_commit_story.daily_summary import generate_daily_summary_mcp_tool

request = {"date": "2025-01-15"}
response = generate_daily_summary_mcp_tool(request)

if response["status"] == "success":
    print(f"Summary saved to: {response['file_path']}")
elif response["status"] == "no_entries":
    print("No journal entries found for this date")
else:
    print(f"Error: {response['error']}")
```

### Manual Reflection Extraction
```python
from mcp_commit_story.daily_summary import _extract_manual_reflections

entries = load_journal_entries_for_date("2025-01-15", config)
reflections = _extract_manual_reflections(entries)
# Returns list of user-written reflections preserved verbatim
```

## File Locations

- **Implementation**: `src/mcp_commit_story/daily_summary.py`
- **MCP Registration**: `src/mcp_commit_story/server.py`
- **Type Definitions**: `src/mcp_commit_story/journal_workflow_types.py`
- **Tests**: `tests/unit/test_daily_summary_mcp.py`
- **Summary Output**: `{journal_path}/summaries/daily/{date}-summary.md`

## Testing

Comprehensive test suite covering:
- TypedDict schema validation
- MCP tool registration and integration
- AI generation mocking and content validation
- Error handling scenarios
- Manual reflection preservation
- File system operations
- Telemetry integration

### Running Tests
```bash
python -m pytest tests/unit/test_daily_summary_mcp.py -v
```

## Integration Points

### Journal System
- Uses `JournalEntry` objects from journal core
- Integrates with `get_journal_file_path()` utilities
- Follows established file path patterns

### MCP Server
- Registered as `journal/generate-daily-summary` tool
- Exposed through FastMCP server architecture
- Consistent error handling with other MCP tools

### Configuration
- Uses `load_config()` for configuration management
- Respects journal path settings
- Integrates with AI model configuration

### Telemetry
- Full OpenTelemetry integration with spans
- Operation tracing and performance monitoring
- Error tracking and metrics collection

## Best Practices

1. **Date Handling**: Always use YYYY-MM-DD format for consistency
2. **Error Recovery**: Check status before processing response content
3. **Performance**: Summary generation can take 30-60 seconds due to AI processing
4. **Content Quality**: Manual reflections take priority over AI-generated content
5. **File Management**: Summaries are stored in standardized paths for easy discovery

## Future Enhancements

- Weekly/monthly/quarterly summary generation
- Summary comparison and trending analysis
- Integration with external knowledge systems
- Advanced content filtering and categorization
- Real-time summary updates as entries are added 