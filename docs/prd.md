# MCP Commit Story - Product Requirements Document

## Project Overview

MCP Commit Story is a Model Context Protocol (MCP) server that automatically generates comprehensive journal entries from git commits and AI chat history. It bridges the gap between technical development activities and meaningful personal reflection by creating rich, contextual journal entries that capture both the technical work and the thought processes behind it.

## Core Value Proposition

**Transform development commits into meaningful personal narratives** by combining git metadata with AI chat conversations to create journal entries that capture not just what was built, but why, how, and what was learned in the process.

## Target Users

- **Primary**: Software developers who use AI assistants (like Claude, ChatGPT, etc.) and want to maintain development journals
- **Secondary**: Engineering teams wanting to capture institutional knowledge and decision-making processes
- **Tertiary**: Researchers studying AI-assisted development workflows

## Key Features

### 1. Automated Journal Generation
- **Git Integration**: Automatically extracts commit metadata, file changes, and diff statistics
- **AI Chat Integration**: Reads conversation history from popular AI platforms (starting with Cursor)
- **Intelligent Synthesis**: Combines technical and conversational data into coherent journal entries
- **Multiple Output Formats**: Supports markdown, plain text, and structured data formats

### 2. MCP Server Architecture
- **Protocol Compliance**: Full MCP (Model Context Protocol) server implementation
- **Tool Integration**: Exposes journal generation as callable tools for AI assistants
- **Cross-Platform**: Works on Windows, macOS, Linux, and WSL environments
- **Performance Optimized**: Efficient data processing with minimal resource usage

### 3. Chat Platform Integration
- **Cursor Support**: Direct integration with Cursor's SQLite chat databases
- **Auto-Discovery**: Automatically finds and connects to recent workspace databases
- **Multi-Workspace**: Supports multiple concurrent workspace chat histories
- **Privacy-First**: All processing happens locally, no data transmitted externally

### 4. Comprehensive Error Handling and User Experience

#### Error Prevention
- **Proactive Validation**: Validates database access and schema compatibility before processing
- **Graceful Degradation**: Falls back to git-only journal generation when chat data unavailable
- **Smart Discovery**: Uses 48-hour recency filter to focus on active workspaces
- **Cross-Platform Detection**: Automatically adapts to different operating system environments

#### User-Friendly Error Messages
- **Context-Rich Feedback**: Error messages include specific paths, system information, and troubleshooting guidance
- **Actionable Instructions**: Each error provides clear steps for resolution
- **Progressive Disclosure**: Basic error message with optional detailed context for advanced users
- **Sensitive Data Protection**: Automatically redacts passwords, API keys, and other sensitive information

#### Error Recovery Mechanisms
- **Automatic Fallbacks**: When primary database unavailable, searches for alternative recent databases
- **Partial Success Handling**: Generates journal entries with available data when some sources fail
- **Retry Logic**: Built-in retry mechanisms for transient connection issues
- **Manual Override Options**: Environment variables and explicit paths for custom configurations

#### Error Categories and Handling
1. **Database Discovery Errors**
   - **Not Found**: Clear guidance on Cursor usage requirements and workspace activity
   - **Access Denied**: Permission troubleshooting with platform-specific instructions
   - **Schema Mismatch**: Version compatibility guidance and alternative database suggestions

2. **Connection Errors**
   - **File Locking**: Instructions for closing Cursor and checking process conflicts
   - **Corruption Detection**: Database integrity validation and recovery suggestions
   - **Network Issues**: Local-only operation confirmation and path verification

3. **Query Execution Errors**
   - **Syntax Validation**: SQL error detection with parameter count verification
   - **Schema Evolution**: Graceful handling of database schema changes across Cursor versions
   - **Performance Issues**: Query optimization and timeout handling for large datasets

#### Logging and Diagnostics
- **Structured Logging**: Consistent log format with error types, context, and troubleshooting hints
- **Debug Mode**: Detailed discovery process logging for advanced troubleshooting
- **Error Aggregation**: Summary reporting for multiple database operations
- **Performance Metrics**: Connection timing and query performance tracking

### 5. Intelligent Content Processing
- **Conversation Analysis**: Extracts key decisions, challenges, and insights from AI chat logs
- **Technical Synthesis**: Combines code changes with conversational context
- **Emotional Intelligence**: Identifies frustration, excitement, and breakthrough moments
- **Learning Extraction**: Highlights new concepts, techniques, and problem-solving approaches

### 6. Flexible Configuration
- **Environment Variables**: Simple configuration via CURSOR_WORKSPACE_PATH and other env vars
- **Custom Paths**: Support for non-standard Cursor installations and workspace locations
- **Output Customization**: Configurable journal entry formats and content sections
- **Integration Options**: Multiple ways to invoke journal generation (CLI, MCP tools, API)

## Technical Architecture

### Database Integration
- **SQLite Expertise**: Deep integration with Cursor's state.vscdb database format
- **Schema Adaptation**: Handles different Cursor versions and database schema evolution
- **Performance Optimization**: Efficient query patterns with minimal database locking
- **Data Safety**: Read-only access with comprehensive error handling

### Cross-Platform Compatibility
- **Platform Detection**: Automatic OS detection with WSL support
- **Path Resolution**: Smart path discovery across different installation patterns
- **Permission Handling**: Graceful handling of file system permission variations
- **Environment Integration**: Seamless integration with different shell environments

### MCP Implementation
- **Standard Compliance**: Full adherence to MCP protocol specifications
- **Tool Exposure**: Journal generation exposed as callable MCP tools
- **Error Propagation**: Proper error handling through MCP response format
- **Resource Management**: Efficient connection and memory management

## Success Metrics

### Technical Performance
- **Discovery Success Rate**: >95% successful database discovery on supported platforms
- **Error Recovery Rate**: >90% of errors provide actionable resolution guidance
- **Processing Speed**: <5 seconds for typical journal entry generation
- **Resource Usage**: <100MB memory footprint during normal operation

### User Experience
- **Setup Time**: <5 minutes from installation to first journal entry
- **Error Resolution**: <2 minutes average time to resolve common configuration issues
- **User Satisfaction**: Clear error messages reduce support requests by >80%
- **Platform Coverage**: 100% compatibility across Windows, macOS, Linux, and WSL

### Content Quality
- **Completeness**: Journal entries include both technical and conversational context
- **Accuracy**: >95% accurate extraction of key decisions and insights
- **Readability**: Generated content requires minimal manual editing
- **Privacy**: 100% local processing with no external data transmission

## Implementation Phases

### Phase 1: Core Infrastructure ✅
- [x] MCP server framework and protocol compliance
- [x] Cross-platform database discovery and connection
- [x] Comprehensive error handling with user-friendly messages
- [x] Basic git integration and commit metadata extraction

### Phase 2: Chat Integration 🔄
- [ ] Cursor chat database schema analysis and query implementation
- [ ] Conversation parsing and context extraction
- [ ] Multi-workspace database support and management
- [ ] Advanced error recovery and fallback mechanisms

### Phase 3: Content Generation 📋
- [ ] AI-powered content synthesis and journal entry creation
- [ ] Emotional intelligence and learning extraction algorithms
- [ ] Customizable output formats and content sections
- [ ] Performance optimization and caching strategies

### Phase 4: Advanced Features 📋
- [ ] Additional chat platform integrations (VS Code, other editors)
- [ ] Team collaboration features and shared journal generation
- [ ] Advanced analytics and development pattern recognition
- [ ] API extensions and third-party integration support

## Risk Mitigation

### Technical Risks
- **Database Schema Changes**: Comprehensive error handling and version detection
- **Platform Compatibility**: Extensive testing across all supported environments
- **Performance Issues**: Efficient algorithms and resource management
- **Data Privacy**: Local-only processing with sensitive data protection

### User Experience Risks
- **Complex Setup**: Automated discovery and clear error messages minimize configuration
- **Error Confusion**: Context-rich error messages with actionable troubleshooting steps
- **Platform Variations**: Comprehensive testing and platform-specific guidance
- **Support Burden**: Self-service error resolution through detailed error handling

## Quality Assurance

### Testing Strategy
- **Unit Testing**: >90% code coverage with comprehensive error scenario testing
- **Integration Testing**: Real-world database testing across multiple Cursor versions
- **Platform Testing**: Automated testing on Windows, macOS, Linux, and WSL
- **Error Handling Testing**: Comprehensive error scenario validation and recovery testing

### Documentation Standards
- **User Guides**: Platform-specific setup and troubleshooting documentation
- **Error Reference**: Comprehensive error message catalog with resolution steps
- **API Documentation**: Complete MCP tool and function reference
- **Troubleshooting Guides**: Step-by-step resolution for common issues

This PRD establishes MCP Commit Story as a robust, user-friendly tool that transforms development activities into meaningful personal narratives while maintaining the highest standards of reliability, privacy, and user experience. 