# Summary Generation System

## Overview

The MCP Commit Story summary generation system transforms individual journal entries into structured, hierarchical summaries across multiple time periods. The system creates an interconnected knowledge graph where users can navigate from high-level yearly summaries down to individual journal entries, with automatic source file linking enabling complete information traceability.

## Architecture

### Summary Hierarchy

The system implements a five-tier hierarchical structure:

```
Yearly Summary (2025)
├── Quarterly Summary (Q2 2025)
│   ├── Monthly Summary (2025-06)
│   │   ├── Weekly Summary (2025-06-week23)
│   │   │   ├── Daily Summary (2025-06-06)
│   │   │   │   └── Journal Entry (2025-06-06-journal.md)
│   │   │   └── Daily Summary (2025-06-07)
│   │   └── Weekly Summary (2025-06-week24)
│   └── Monthly Summary (2025-07)
└── Quarterly Summary (Q3 2025)
```

### Core Components

- **`daily_summary.py`** - AI-powered daily summary generation (fully implemented)
- **`summary_utils.py`** - Source file linking and hierarchy utilities (348 lines)
- **`weekly_summary.py`** - Weekly summary generation (placeholder implementation)
- **`monthly_summary.py`** - Monthly summary generation (placeholder implementation)
- **`quarterly_summary.py`** - Quarterly summary generation (placeholder implementation)
- **`yearly_summary.py`** - Yearly summary generation (placeholder implementation)

---

## Daily Summaries

### Overview

The Daily Summary system automatically generates comprehensive daily summaries from journal entries using AI. This tool synthesizes a full day's worth of development work into structured summaries with 8 standardized sections.

### Key Features

- **AI-Powered Synthesis**: Uses sophisticated AI prompts to analyze and summarize journal entries
- **8-Section Structure**: Standardized format covering all aspects of development work
- **Manual Reflection Preservation**: Prioritizes and preserves user-written reflections verbatim
- **File-Creation Trigger System**: Smart logic to determine when summaries should be generated
- **Robust Error Handling**: Graceful handling of missing entries, file system errors, and invalid dates
- **Source File Linking**: Automatic links to constituent journal entries
- **Telemetry Integration**: Full spans and tracing for monitoring and debugging

### MCP Tool Schema

#### Request: `GenerateDailySummaryRequest`
```typescript
{
  date: string;  // Required: YYYY-MM-DD format
}
```

#### Response: `GenerateDailySummaryResponse`
```typescript
{
  status: "success" | "no_entries" | "error";
  file_path: string | "";     // Path to generated summary file
  content: string | "";       // Markdown content of summary
  error: string | null;       // Error message if status is "error"
}
```

### Daily Summary Structure

Each daily summary contains 8 standardized sections plus source links and reflections:

1. **Summary** - High-level overview of the day's work
2. **Reflections** - Manual user reflections (preserved verbatim) + AI insights
3. **Progress Made** - Concrete accomplishments and completed work
4. **Key Accomplishments** - Most significant achievements as bullet points
5. **Technical Synopsis** - Technical details, implementations, and architecture decisions
6. **Challenges and Learning** - Problems encountered and knowledge gained
7. **Discussion Highlights** - Important conversations and decision points
8. **Tone/Mood** - Emotional context and team dynamics
9. **Daily Metrics** - Quantitative measures (commits, files, time spent)
10. **Source Files** - Links to constituent journal entries (automatic)
11. **REFLECTIONS** - Complete full reflections from journal entries (NEW)

### REFLECTIONS Section

The REFLECTIONS section is a new feature that extracts ALL full reflections from journal entries and adds them to the end of daily summaries under a `## REFLECTIONS` header. This section captures the complete reflection content that users manually add to their journal entries.

#### Key Features

- **Complete Extraction**: Extracts all reflections with `### H:MM AM/PM — Reflection` headers
- **Full Content**: Includes the entire reflection text, not just patterns or excerpts
- **Timestamp Preservation**: Maintains original reflection timestamps
- **Markdown Formatting**: Properly formatted with H3 headers and content blocks

#### Implementation

- **`extract_all_reflections_from_markdown()`** - Extracts reflections from raw markdown content
- **`extract_reflections_from_journal_file()`** - Loads and extracts reflections from journal file
- **`format_reflections_section()`** - Formats reflections into markdown section
- **Updated `generate_daily_summary()`** - Includes full reflection extraction
- **Updated `_format_summary_as_markdown()`** - Adds REFLECTIONS section to output

#### Format Example

```markdown
## REFLECTIONS

### 7:30 AM

This is my morning reflection about the work I'm planning to do today.
I'm feeling excited about the new features we're implementing.

### 2:30 PM

After lunch reflection - the architecture discussion went well.
We decided to use the microservice approach for better scalability.
```

#### Technical Details

The REFLECTIONS section is automatically generated when daily summaries are created. It:

1. Reads the journal markdown file for the specified date
2. Searches for reflection headers matching the pattern `### H:MM AM/PM — Reflection`
3. Extracts the complete content following each reflection header
4. Formats them into a structured markdown section
5. Appends the section to the end of the daily summary

This feature ensures that all user reflections are preserved in daily summaries, providing complete context for future reference and analysis.

### Implementation Details

#### Core Functions

- **`generate_daily_summary()`** - Core AI generation logic with real AI integration
- **`load_journal_entries_for_date()`** - Loads entries for specified date
- **`save_daily_summary()`** - Saves summary to markdown file  
- **`extract_all_reflections_from_markdown()`** - Extracts full reflections from markdown content
- **`extract_reflections_from_journal_file()`** - Loads and extracts reflections from files
- **`format_reflections_section()`** - Formats reflections into markdown section
- **`generate_daily_summary_standalone()`** - Standalone entry point for git hook integration

#### AI Prompt Engineering

The tool uses a 100+ line sophisticated AI prompt with:
- **Content Quality Guidelines**: Rules for rich, thoughtful summaries
- **Anti-Hallucination Rules**: Strict requirements for evidence-based content
- **Section-Specific Instructions**: Detailed requirements for each summary section
- **Formatting Standards**: Consistent markdown output structure

#### File Creation Triggers

Smart logic determines when to generate summaries:
- **Triggered by**: New journal file creation
- **Analyzes**: Most recent previous date without existing summary
- **Prevents**: Duplicate generation and unnecessary processing

---

## Source File Linking System

### Overview

The source file linking system creates a navigable hierarchy within the summary ecosystem. Each summary type automatically tracks and links to the constituent source files it was built from, enabling users to trace information provenance and navigate through the hierarchical structure.

### Core Architecture

**Primary Module**: `src/mcp_commit_story/summary_utils.py` (348 lines)
- Source file detection for all summary types
- Automatic link generation with existence checking
- Markdown integration for formatted output
- Error handling for missing files and invalid formats

**Integration Points**:
- `daily_summary.py`: Enhanced to include source linking via `add_source_links_to_summary()`
- New summary modules: `weekly_summary.py`, `monthly_summary.py`, `quarterly_summary.py`, `yearly_summary.py`
- Markdown generation: Automatic source links sections in summary output

### Source Detection Logic

#### Daily Summaries
- **Sources**: Journal entry files (`YYYY-MM-DD-journal.md`)
- **Location**: `daily/` directory
- **Example**: `daily/2025-06-06-journal.md`

#### Weekly Summaries
- **Sources**: Daily summary files for all 7 days of the week
- **Location**: `summaries/daily/` directory  
- **Logic**: Calculates Monday start date and generates 7 consecutive daily summary file references
- **Example**: `summaries/daily/2025-06-02-summary.md` through `summaries/daily/2025-06-08-summary.md`

#### Monthly Summaries
- **Sources**: Weekly summary files for all weeks that start within the month
- **Location**: `summaries/weekly/` directory
- **Logic**: Complex calendar mathematics to find all Mondays within the month boundaries
- **File Formats**: Supports multiple naming conventions:
  - `YYYY-MM-weekNN.md` (e.g., `2025-06-week23.md`)
  - `YYYY-weekNN.md` (e.g., `2025-week23.md`)
  - `YYYY-WWW.md` (e.g., `2025-W23.md`)

#### Quarterly Summaries
- **Sources**: Monthly summary files for the 3 months in the quarter
- **Location**: `summaries/monthly/` directory
- **Logic**: Maps quarter number to appropriate months (Q1: Jan-Mar, Q2: Apr-Jun, etc.)
- **Example**: Q2 2025 links to `2025-04.md`, `2025-05.md`, `2025-06.md`

#### Yearly Summaries
- **Sources**: Quarterly summary files for all 4 quarters
- **Location**: `summaries/quarterly/` directory
- **Example**: 2025 links to `2025-Q1.md`, `2025-Q2.md`, `2025-Q3.md`, `2025-Q4.md`

### Key Functions

```python
def determine_source_files_for_summary(summary_type: str, date_identifier: str, journal_path: str) -> List[Dict[str, Any]]:
    """Main entry point for source file detection."""

def add_source_links_to_summary(summary_obj: Any, summary_type: str, date_identifier: str, journal_path: str) -> Any:
    """Enhance summary objects with source file metadata."""

def generate_source_links_section(source_files: List[Dict[str, Any]], coverage_description: str) -> str:
    """Generate markdown-formatted source links sections."""

def enhance_summary_markdown_with_source_links(markdown_content: str, summary_type: str, date_identifier: str, journal_path: str) -> str:
    """Add source links to existing markdown content."""
```

### Source Link Markdown Output

Source links are automatically formatted as markdown sections:

```markdown
#### Source Files

**Coverage**: June 6, 2025

**Available Files**:
- [2025-06-06-journal.md](daily/2025-06-06-journal.md)

**Missing Files**:
- [2025-06-05-journal.md](daily/2025-06-05-journal.md) *(file not found)*
```

---

## Future Summary Types

### Weekly Summaries (Planned)

**Purpose**: Synthesize daily summaries into weekly patterns and themes
**Structure**:
- Weekly overview and key themes
- Progress highlights across the week
- Technical patterns and decisions
- Challenges and learning trends
- Team collaboration highlights
- Weekly metrics and productivity insights

**MCP Tool**: `journal/generate-weekly-summary`
**File Location**: `summaries/weekly/YYYY-weekNN-summary.md`
**Sources**: 7 daily summary files for the week period

### Monthly Summaries (Planned)

**Purpose**: Aggregate weekly summaries into monthly milestones and growth areas
**Structure**:
- Monthly achievements and milestones
- Technical skill development
- Project progression and outcomes
- Team and collaboration evolution
- Challenge resolution patterns
- Monthly productivity and impact metrics

**MCP Tool**: `journal/generate-monthly-summary`
**File Location**: `summaries/monthly/YYYY-MM-summary.md`
**Sources**: Weekly summary files for all weeks within the month

### Quarterly Summaries (Planned)

**Purpose**: Synthesize monthly summaries into quarterly review and planning insights
**Structure**:
- Quarterly goals and achievement assessment
- Major technical accomplishments
- Skill development and career growth
- Project impact and business value
- Team leadership and collaboration growth
- Strategic thinking and decision-making evolution

**MCP Tool**: `journal/generate-quarterly-summary`
**File Location**: `summaries/quarterly/YYYY-QN-summary.md`
**Sources**: 3 monthly summary files for the quarter

### Yearly Summaries (Planned)

**Purpose**: Create comprehensive annual reviews for career development and reflection
**Structure**:
- Annual career development summary
- Major technical achievements and impact
- Skill evolution and learning journey
- Leadership and mentorship growth
- Project portfolio and business impact
- Professional network and relationship building
- Strategic contributions and thought leadership

**MCP Tool**: `journal/generate-yearly-summary`
**File Location**: `summaries/yearly/YYYY-summary.md`
**Sources**: 4 quarterly summary files for the year

---

## File Organization

```
journal/
├── daily/
│   ├── 2025-06-06-journal.md
│   └── 2025-06-07-journal.md
└── summaries/
    ├── daily/
    │   ├── 2025-06-06-summary.md
    │   └── 2025-06-07-summary.md
    ├── weekly/
    │   └── 2025-06-week23-summary.md
    ├── monthly/
    │   └── 2025-06-summary.md
    ├── quarterly/
    │   └── 2025-Q2-summary.md
    └── yearly/
        └── 2025-summary.md
```

---

## Error Handling

The summary generation system includes comprehensive error handling:

- **Invalid Date Formats**: Graceful parsing error handling with logging
- **Missing Directories**: Robust file system error handling for missing `summaries/` subdirectories
- **File System Errors**: Graceful handling of permission and path issues
- **AI Generation Failures**: Fallback to mock responses for testing
- **No Entries Found**: Returns appropriate status (not an error condition)
- **Unknown Summary Types**: Warning logs for unrecognized summary types

## Testing

### Daily Summary Testing
Comprehensive test suite in `tests/unit/test_daily_summary_mcp.py`:
- TypedDict schema validation
- MCP tool registration and integration
- AI generation mocking and content validation
- Error handling scenarios
- Manual reflection preservation
- File system operations
- Telemetry integration

### Source Linking Testing
Comprehensive test suite in `tests/unit/test_summary_source_links.py`:
- **9 test scenarios** covering all summary types and edge cases
- **File existence testing** for both available and missing source files
- **Calendar edge cases** like month boundaries and leap years
- **Integration testing** with existing summary generation workflows

### Running Tests
```bash
python -m pytest tests/unit/test_daily_summary*.py -v
python -m pytest tests/unit/test_summary_source_links.py -v
```

---

## Usage Examples

### Daily Summary Generation
```python
from mcp_commit_story.daily_summary import generate_daily_summary

# Generate daily summary for specific date
summary = generate_daily_summary("2025-01-15")

if response["status"] == "success":
    print(f"Summary saved to: {response['file_path']}")
elif response["status"] == "no_entries":
    print("No journal entries found for this date")
else:
    print(f"Error: {response['error']}")
```

### Source File Detection
```python
from mcp_commit_story.summary_utils import determine_source_files_for_summary

# Get source files for a daily summary
source_files = determine_source_files_for_summary("daily", "2025-06-06", "/path/to/journal")

# Result:
[{
    'path': 'daily/2025-06-06-journal.md',
    'exists': True,
    'type': 'journal_entry'
}]
```

### Automatic Source Link Integration
```python
from mcp_commit_story.daily_summary import generate_daily_summary

summary = generate_daily_summary(entries, "2025-06-06", config)
# summary['source_files'] is automatically populated
```

---

## Integration Points

### Journal System
- Uses `JournalEntry` objects from journal core
- Integrates with `get_journal_file_path()` utilities
- Follows established file path patterns

### Standalone Generation
- Direct function calls for programmatic generation
- Future tools: weekly summaries, monthly summaries, etc.
- Consistent error handling with other journal functions

### Configuration
- Uses `load_config()` for configuration management
- Respects journal path settings
- Integrates with AI model configuration

### Telemetry
- Full OpenTelemetry integration with spans
- Operation tracing and performance monitoring
- Error tracking and metrics collection

---

## Benefits

1. **Information Traceability**: Complete provenance tracking from summaries to source data
2. **Hierarchical Navigation**: Seamless navigation through the summary ecosystem
3. **Content Transparency**: Clear visibility into data sources for each summary
4. **Quality Assurance**: Users can verify summary accuracy by checking source files
5. **Knowledge Graph Creation**: Interconnected system enabling discovery and exploration
6. **Career Development**: Rich historical data for performance reviews and reflection
7. **Content Creation**: Authentic stories for blogs, talks, and documentation

---

## Future Enhancements

- **Bidirectional Linking**: Links from source files back to summaries that reference them
- **Visual Navigation**: Potential web interface for graphical navigation
- **Link Validation**: Automated checking for broken or outdated links
- **Custom Link Formats**: Support for different link formats and destinations
- **Summary Comparison**: Trending analysis across time periods
- **Advanced Content Filtering**: Categorization and tagging systems
- **Real-time Updates**: Dynamic summary updates as entries are added
- **Integration with External Systems**: Knowledge management and project tracking tools 