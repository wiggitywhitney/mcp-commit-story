# Product Requirements Document (PRD)
## MCP Commit Story - Engineering Journal Tool

---

## **Product Overview**

**MCP Commit Story** is an automated engineering journal tool that captures the story behind code commits through background generation. It transforms development work into narrative entries that can be used for retrospectives, career documentation, and content creation.

### **Core Value Proposition**
- **Capture context**: Record not just what was built, but how it felt and why it mattered
- **Enable storytelling**: Transform development work into content for blogs, talks, and retrospectives  
- **Support growth**: Help developers reflect on and document their professional journey
- **Zero friction**: Background generation captures and processes context automatically after each commit
- **User control**: Manual tools for adding reflections and capturing AI context when needed

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
1. **Have my development story captured automatically** so I don't lose the context behind my work
2. **Remember why I made technical decisions** weeks or months later
3. **Have concrete examples for performance reviews** without manually tracking accomplishments
4. **Find authentic stories for blog posts and talks** based on real development experiences
5. **Reflect on my growth over time** through patterns in my work and challenges
6. **Add context when I need to** without disrupting my workflow

### **As a Team Lead, I want to:**
1. **Access rich context for retrospectives** beyond just what shipped
2. **Understand team challenges and blockers** through authentic development experiences
3. **Support career development conversations** with concrete examples of growth and impact

---

## **Product Requirements**

### **Core Functionality**

#### **Background Journal Generation**
- **Trigger**: Automatic generation after each git commit via post-commit hook
- **Context Collection**: 
  - Git metadata, diffs, and file changes (always available)
  - Cursor chat history with intelligent filtering based on git changes
  - Recent journal entries for continuity (today + 2 most recent daily files)
  - Project overview/README for context
- **Processing**: Fresh AI agent invoked with comprehensive context for each entry
- **Output**: Human-readable markdown files with machine-readable tags
- **Storage**: Local files in the developer's repository organized by date
- **Performance**: Background processing never blocks git operations

#### **Intelligent Chat History Processing**
- **Git-driven filtering**: Extract keywords and concepts from git diffs
- **Relevance scoring**: Match chat content against code changes to find related discussions
- **Boundary detection**: Identify relevant chat sessions and conversation segments
- **Context optimization**: Include only chat portions that relate to the actual work done

#### **User-Controlled Context Addition**
- **Manual reflections**: Direct thought capture via journal/add-reflection tool
- **AI context capture**: Capture current AI assistant knowledge via journal/capture-context tool
  - **Problem**: AI knowledge lost between sessions - valuable insights from AI conversations disappear when the session ends
  - **Solution**: Persistent knowledge capture in journal files that enriches future commit journal generation
  - **Benefits**: Continuous learning, richer documentation, team knowledge sharing, prevents rediscovering solutions
- **Flexible timing**: Add context before, during, or after development work  
- **Integration**: Context automatically included in future journal entries

**Usage Example for AI Context Capture:**
```
Developer discovers React performance optimization with AI assistant
→ Uses journal/capture-context to save insight
→ Knowledge stored in daily journal with timestamp
→ Next React commit automatically references previous insight
→ Creates continuous learning cycle in journal documentation
```

#### **Automatic Summary Generation**
- **Daily summaries**: Generated automatically when date boundaries are detected
- **Multi-timeframe summaries**: Weekly, monthly, quarterly, yearly (planned)
- **Same pattern**: Background generation using recent journal entries as input
- **Manual override**: MCP tools available for manual summary generation when needed

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
- **Automatic processing**: Journal entries appear without user intervention
- **Fast execution**: Background processing completes quickly after commits
- **Graceful degradation**: Works even when some context sources unavailable
- **Optional interaction**: Manual context tools available when needed

#### **Content Discovery Experience**
- **Logical organization**: Easy to find entries by date or time period
- **Readable format**: Clean markdown that works in any editor
- **Portable content**: Files can be shared, exported, or processed by other tools

### **Technical Integration Requirements**

#### **Git Integration**
- **Hook-based triggering**: Automatic execution via git post-commit hook
- **Direct execution**: Standalone generator runs independently of MCP server
- **Repository awareness**: Understand git context and changes
- **Multi-repo support**: Each repository maintains its own journal
- **Never blocks**: Git operations complete normally even if journal generation fails

#### **AI Assistant Integration**
- **MCP protocol**: Interactive tools exposed via Model Context Protocol
- **Chat context awareness**: Access to AI assistant conversation history when available
- **Fresh AI instances**: Each journal entry generated by new AI agent with full context
- **Context capture**: Tools to manually capture AI assistant's current knowledge
- **Optional dependency**: Core functionality works without MCP server running

#### **Cursor Integration**
- **SQLite database access**: Extract chat history from Cursor's local database with robust connection management
- **Cross-platform support**: Work on macOS, Linux, Windows with different Cursor installations
- **Workspace detection**: Automatically find relevant chat history for current repository
- **Privacy respect**: Only access chat data that relates to current development work
- **Performance characteristics**: 
  - No connection caching - lightweight connections for each operation
  - 48-hour recency filter to focus on recent workspace activity
  - Aggressive auto-discovery of `state.vscdb` files across workspace directories
  - Context manager support for automatic resource cleanup
  - Parameterized queries with SQL injection protection
- **Error handling**: Comprehensive error recovery for connection failures, corrupted databases, and permission issues
- **Resource management**: Automatic connection cleanup with no persistent database connections

#### **Development Environment Compatibility**
- **Cross-platform**: Work on macOS, Linux, Windows
- **Editor agnostic**: No dependency on specific development tools beyond git
- **Version control friendly**: Journal files work well with git
- **Minimal dependencies**: Core functionality requires only Python and git

#### **Background Processing Architecture**
- **Standalone operation**: Core journal generation works without external dependencies
- **Fresh context**: Each entry generated with comprehensive, current context
- **Error isolation**: Processing failures don't affect git operations
- **Resource efficiency**: Optimized for quick background execution
- **Telemetry**: Performance monitoring and error tracking

---

## **Success Metrics**

### **Adoption Metrics**
- **Daily active usage**: Consistent journal generation on commits
- **Content creation**: Developers using journal entries for external content
- **Retention**: Continued use after initial setup
- **Context addition**: Usage of manual reflection and context capture tools

### **Value Metrics**
- **Retrospective quality**: More meaningful team and individual retrospectives
- **Career development**: Concrete examples used in performance discussions  
- **Content creation**: Blog posts, talks, or documentation created from journal content
- **Decision recall**: Developers successfully finding past decision context

### **Experience Metrics**
- **Setup success rate**: Percentage of developers who successfully initialize and use the tool
- **Workflow disruption**: Minimal impact on development speed and flow (target: <1 second overhead)
- **Content satisfaction**: Developers find the generated content accurate and useful
- **Context relevance**: Chat history filtering produces relevant, useful content

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