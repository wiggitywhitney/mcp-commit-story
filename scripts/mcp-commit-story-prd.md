# Product Requirements Document (PRD)
## MCP Commit Story - Engineering Journal Tool

---

## **Product Overview**

**MCP Commit Story** is an automated engineering journal tool that captures the story behind code commits. It transforms development work into narrative entries that can be used for retrospectives, career documentation, and content creation.

### **Core Value Proposition**
- **Capture context**: Record not just what was built, but how it felt and why it mattered
- **Enable storytelling**: Transform development work into content for blogs, talks, and retrospectives  
- **Support growth**: Help developers reflect on and document their professional journey
- **Zero friction**: Work silently in the background, triggered by normal git workflow

---

## **Target Users**

### **Primary User: Individual Developer**
- Works with git repositories
- Values reflection and professional growth
- Creates content (blogs, talks, documentation)
- Participates in team retrospectives and performance reviews

### **Secondary Users**
- **Team Leads**: Use journal insights for retrospectives and team development
- **Engineering Managers**: Support career development conversations with concrete examples
- **Developer Advocates**: Mine authentic stories for technical content

---

## **Core User Stories**

### **As a Developer, I want to:**
1. **Automatically capture my development story** so I don't lose the context behind my work
2. **Remember why I made technical decisions** weeks or months later
3. **Have concrete examples for performance reviews** without manually tracking accomplishments
4. **Find authentic stories for blog posts and talks** based on real development experiences
5. **Reflect on my growth over time** through patterns in my work and challenges

### **As a Team Lead, I want to:**
1. **Access rich context for retrospectives** beyond just what shipped
2. **Understand team challenges and blockers** through authentic development experiences
3. **Support career development conversations** with concrete examples of growth and impact

---

## **Product Requirements**

### **Core Functionality**

#### **✅ IMPLEMENTED: Automated Journal Generation**
- **✅ Trigger**: Generate journal entry automatically on each git commit via MCP `journal/new-entry` handler
- **✅ Content**: Capture commit details, code changes, and available context through comprehensive TypedDict workflow system
- **✅ Format**: Human-readable markdown files organized by date with structured sections
- **✅ Storage**: Local files in the developer's repository with on-demand directory creation
- **✅ Integration**: Full MCP protocol integration with comprehensive test coverage and telemetry
- **✅ Error Handling**: Graceful handling of missing context, file permissions, and journal-only commit detection
- **✅ Type Safety**: Complete TypedDict definitions for all workflow operations ensuring API contract compliance

#### **Context Collection** 
- **Git data**: Commit messages, file changes, timestamps
- **Chat history**: Conversations with AI assistants during development (when available)
- **Terminal activity**: Commands executed during development session (when available)
- **Decision context**: Technical choices and reasoning (when evident from available data)

#### **✅ IMPLEMENTED: Multi-Timeframe Summaries**
- **✅ Daily summaries**: Comprehensive AI-generated daily summaries via MCP `journal/generate-daily-summary` tool with 8-section structure (Summary, Reflections, Progress Made, Key Accomplishments, Technical Synopsis, Challenges and Learning, Discussion Highlights, Tone/Mood, Daily Metrics)
- **✅ Manual reflection preservation**: User-written reflections are automatically extracted and prioritized in summaries, preserving authentic developer insights verbatim
- **✅ Smart trigger system**: File-creation-based triggers automatically determine when summaries should be generated based on journal activity
- **✅ Robust error handling**: Graceful handling of missing entries, invalid dates, and file system issues with appropriate status responses
- **✅ Source file linking**: Hierarchical navigation system where each summary type (daily, weekly, monthly, quarterly, yearly) automatically links to its constituent source files, enabling users to trace information provenance from high-level summaries down to individual journal entries
- **Weekly summaries**: Patterns, progress themes, key achievements (planned)
- **Monthly summaries**: Major milestones, growth areas, significant learnings (planned)
- **Yearly summaries**: Career development, skill evolution, major projects (planned)

#### **Content Quality Standards**
- **No hallucination**: All content must be grounded in actual data (commits, chat, commands)
- **Authentic tone**: Capture the developer's actual mood and language from available context
- **Decision transparency**: Include reasoning when available, acknowledge uncertainty when not
- **Respectful privacy**: Only process data that developers explicitly make available

### **User Experience Requirements**

#### **Setup Experience**
- **Simple initialization**: One command to set up in a repository
- **Minimal configuration**: Works with sensible defaults out of the box
- **Clear instructions**: Obvious next steps after setup

#### **Daily Usage Experience**  
- **Invisible operation**: No disruption to normal development workflow
- **Reliable triggering**: Consistently generates entries on commits
- **Fast execution**: No noticeable delay to commit process
- **Graceful degradation**: Works even when some data sources unavailable

#### **Content Discovery Experience**
- **Logical organization**: Easy to find entries by date or time period
- **Readable format**: Clean markdown that works in any editor
- **Portable content**: Files can be shared, exported, or processed by other tools

### **Technical Integration Requirements**

#### **Git Integration**
- **Hook-based triggering**: Automatic execution via git post-commit hook
- **Repository awareness**: Understand git context and changes
- **Multi-repo support**: Each repository maintains its own journal
- **✅ Enhanced hook architecture**: Python worker pattern with daily summary auto-triggering and MCP integration

#### **✅ IMPLEMENTED: Automatic Daily Summary Generation**
- **✅ Smart triggering**: File-creation-based detection automatically generates daily summaries when journal activity indicates date change
- **✅ Git hook integration**: Enhanced post-commit hook using Python worker architecture detects summary opportunities
- **✅ MCP integration**: Hook worker communicates with MCP server for summary generation
- **✅ Graceful degradation**: Hook operations never block git commits, with comprehensive error handling and logging
- **✅ End-to-end workflow**: Complete automation from commit → date detection → summary generation → file creation
- **✅ Period boundary detection**: Automatic weekly/monthly/quarterly summary triggering on date transitions
- **✅ Troubleshooting support**: Comprehensive logging and debug tools for hook operation diagnosis

#### **✅ IMPLEMENTED: AI Assistant Integration**
- **✅ MCP protocol**: Expose functionality via Model Context Protocol with complete `journal/new-entry` implementation
- **✅ Chat context awareness**: Access to AI assistant conversation history when available through structured TypedDict interfaces
- **✅ Command tracking**: Capture AI-executed commands when available through terminal context collection
- **✅ Type-safe workflows**: Comprehensive TypedDict system ensures reliable data flow between all components
- **✅ Error handling**: Robust error responses and validation for all MCP operations
- **✅ Performance**: Optimized implementation with telemetry monitoring and minimal overhead

#### **✅ IMPLEMENTED: MCP Server Entry Point**
- **✅ Primary launch method**: Official `python -m mcp_commit_story` entry point with comprehensive telemetry and monitoring
- **✅ Robust error handling**: Proper Unix exit codes (0=success, 1=error, 2=config error, 130=SIGINT) 
- **✅ Signal handling**: Graceful shutdown (SIGINT, SIGTERM) and config reload (SIGHUP) capabilities
- **✅ Configuration validation**: Clear error messages for invalid or missing configuration settings
- **✅ Structured logging**: Complete server lifecycle logging with trace correlation and telemetry integration
- **✅ Production readiness**: FastMCP integration with stdio transport for maximum AI client compatibility

#### **✅ IMPLEMENTED: Signal Directory Management and File Creation**
- **✅ File-based signaling mechanism**: Asynchronous communication between git hooks and AI clients via `.mcp-commit-story/signals/` directory
- **✅ Signal file format**: JSON-structured signal files with timestamp-based naming for chronological ordering and uniqueness
- **✅ Standard metadata scope**: Commit context including hash, author, date, message, files changed, and statistics in pretty JSON format
- **✅ Thread safety**: Concurrent git hook execution support with threading locks and collision detection
- **✅ Graceful degradation**: Error handling ensures git operations are never blocked by signal creation failures
- **✅ Signal validation**: JSON format validation with required fields and comprehensive error reporting
- **✅ Comprehensive API**: Core functions for directory creation, signal file management, and format validation
- **✅ Production telemetry**: Full OpenTelemetry integration with metrics and tracing for signal operations

#### **✅ IMPLEMENTED: Generic MCP Tool Signal Creation**
- **✅ Universal tool support**: Single `create_tool_signal()` implementation works for any MCP tool (journal_new_entry, generate_daily_summary, generate_weekly_summary, etc.)
- **✅ Complete placeholder replacement**: Fully replaced the `call_mcp_tool()` placeholder with production-ready generic signal creation
- **✅ Enhanced function interface**: Explicit parameters for tool name, parameters, commit metadata, and repository path providing clear signal creation intent
- **✅ Comprehensive telemetry**: Performance metrics, success/failure rates, and error type classification for all tool signal creation
- **✅ Commit metadata extraction**: Automatic extraction of git commit context using existing utilities with graceful fallback
- **✅ Error handling architecture**: Separate validation and graceful degradation layers ensuring git operations never fail while maintaining data integrity
- **✅ Hook workflow integration**: Complete integration with git post-commit hook supporting daily/weekly/monthly summary generation alongside journal entries
- **✅ Test-driven implementation**: 17 comprehensive tests covering all signal creation scenarios, error conditions, and telemetry integration with 100% pass rate

#### **Development Environment Compatibility**
- **Cross-platform**: Work on macOS, Linux, Windows
- **Editor agnostic**: No dependency on specific development tools
- **Version control friendly**: Journal files work well with git

#### **Observability and Monitoring**
- **✅ IMPLEMENTED: Comprehensive telemetry integration**: Complete OpenTelemetry-based observability system integrated throughout the MCP server lifecycle and journal operations
- **✅ IMPLEMENTED: End-to-end tracing**: Distributed traces capture the complete journey from MCP tool call initiation through journal generation, AI processing, and file writing operations
- **✅ IMPLEMENTED: Real-time metrics collection**: Automatic collection of tool call counts, durations, success/failure rates, file operation metrics, AI generation timing, and system performance metrics
- **✅ IMPLEMENTED: Structured logging with trace correlation**: JSON-formatted logs automatically enhanced with OpenTelemetry trace and span IDs for seamless debugging
- **✅ IMPLEMENTED: Multi-environment telemetry support**: Production-ready configuration with console output for development and OTLP export for production observability backends
- **✅ IMPLEMENTED: Graceful degradation**: System continues operating normally even when telemetry infrastructure fails, ensuring reliability
- **✅ IMPLEMENTED: Performance monitoring**: Sub-5ms overhead per operation with comprehensive timing and resource utilization tracking
- **✅ IMPLEMENTED: MCP-specific observability**: Dedicated metrics for tool call patterns, client attribution (Cursor, Claude Desktop), and operation success rates
- **✅ IMPLEMENTED: Security-conscious logging**: Automatic redaction of sensitive data (passwords, API keys, tokens, git info, URLs, personal data) from all log output with configurable debug mode for development
- **✅ IMPLEMENTED: Health monitoring**: Built-in health checks for telemetry system status and integration verification
- **✅ IMPLEMENTED: Hot configuration reload**: Update telemetry settings without restarting the MCP server
- **✅ IMPLEMENTED: Production deployment ready**: Configurable exporters supporting Jaeger, DataDog, New Relic, Prometheus, and custom observability backends
- **✅ IMPLEMENTED: Journal operations instrumentation**: Complete observability for all journal management operations including file operations, AI generation, directory creation, context loading, and entry parsing
- **✅ IMPLEMENTED: Context collection telemetry**: Comprehensive instrumentation for Git operations (diff, log, status) and context gathering (chat history, terminal commands) with performance optimization, memory tracking, and smart file sampling for large repositories
- **✅ IMPLEMENTED: Async/sync operation support**: Telemetry decorator automatically handles both synchronous and asynchronous functions for comprehensive coverage
- **✅ IMPLEMENTED: Advanced sensitive data filtering**: Multi-layer protection with production and debug modes, handling git information, authentication data, connection strings, and personal information
- **✅ IMPLEMENTED: Integration test telemetry validation**: Comprehensive test framework validates telemetry functionality across MCP tool execution chains, AI generation pipelines, and production scenarios with automated circuit breaker and performance impact testing

---

## **Success Metrics**

### **Adoption Metrics**
- **Daily active usage**: Consistent journal generation on commits
- **Content creation**: Developers using journal entries for external content
- **Retention**: Continued use after initial setup

### **Value Metrics**
- **Retrospective quality**: More meaningful team and individual retrospectives
- **Career development**: Concrete examples used in performance discussions  
- **Content creation**: Blog posts, talks, or documentation created from journal content

### **Experience Metrics**
- **Setup success rate**: Percentage of developers who successfully initialize and use the tool
- **Workflow disruption**: Minimal impact on development speed and flow
- **Content satisfaction**: Developers find the generated content accurate and useful

---

## **Non-Requirements (Out of Scope)**

### **Not Building**
- **Web interface**: Command-line and AI integration only
- **Cloud storage**: Local files only
- **Team collaboration features**: Individual developer focus
- **Project management integration**: Journal captures development, not planning
- **Real-time synchronization**: Async, commit-triggered operation only
- **AI model hosting**: Uses external AI services via API

### **Future Considerations**
- **Team aggregation features**: Combine individual journals for team insights
- **Integration plugins**: Connections to project management tools
- **Advanced analytics**: Pattern recognition across time and projects
- **Export formats**: PDF, HTML, or other formats for sharing

---

## **Technical Constraints**

### **Platform Requirements**
- **Python 3.9+**: Minimum runtime requirement
- **Git repository**: Must be used within a git-managed project
- **Local file system**: Requires write access to repository directory

### **Integration Constraints**
- **MCP protocol compliance**: Must work with MCP-compatible AI assistants
- **No external dependencies**: Core functionality works without internet
- **Minimal resource usage**: Should not impact development performance

### **Privacy and Security**
- **Local data only**: No automatic external transmission of journal content
- **Developer control**: Clear boundaries on what data is collected and how
- **Opt-out capability**: Easy to disable or remove

---

## **Release Strategy**

### **MVP (Minimum Viable Product)**
- Basic journal entry generation on commits
- Simple setup and configuration
- Local markdown file output
- MCP server integration for AI assistants

### **Post-MVP Enhancements**
- Enhanced context collection (terminal, chat history)
- Summary generation (daily, weekly, monthly)
- Content quality improvements
- Cross-platform compatibility testing

---

*This PRD focuses on product requirements and user value. For technical implementation details, see the [Technical Documentation](../docs/) and [Engineering Specification](../engineering-mcp-journal-spec-final.md).* 