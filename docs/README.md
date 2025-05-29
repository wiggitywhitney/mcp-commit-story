# MCP Commit Story Documentation

This directory contains the complete technical documentation for the MCP Commit Story project.

## Documentation Overview

### 📋 Start Here
- **[Architecture](architecture.md)** - High-level system design, architectural decisions, and component relationships

### 🔧 Technical References
- **[MCP API Specification](mcp-api-specification.md)** - Complete reference for MCP operations, data formats, and client integration
- **[Journal Behavior](journal-behavior.md)** - How journal entries are generated, structured, and configured
- **[Implementation Guide](implementation-guide.md)** - Detailed development guidance, patterns, and technical implementation

### 🎯 Development Guides
- **[Testing Standards](testing_standards.md)** - Testing approaches, standards, and quality requirements
- **[On-Demand Directory Pattern](on-demand-directory-pattern.md)** - File system organization and directory creation patterns
- **[AI Function Pattern](ai_function_pattern.md)** - Patterns for AI-powered functionality
- **[Journal Init](journal_init.md)** - Journal initialization process and configuration
- **[Server Setup](server_setup.md)** - MCP server setup and deployment

## Quick Navigation

### For New Developers
1. Read [Architecture](architecture.md) for system overview
2. Review [Implementation Guide](implementation-guide.md) for development setup
3. Check [Testing Standards](testing_standards.md) for quality requirements

### For API Integration
1. Start with [MCP API Specification](mcp-api-specification.md)
2. Reference [Journal Behavior](journal-behavior.md) for content structure
3. Review [Architecture](architecture.md) for integration patterns

### For Journal Configuration
1. See [Journal Behavior](journal-behavior.md) for configuration options
2. Check [Journal Init](journal_init.md) for setup process
3. Reference [On-Demand Directory Pattern](on-demand-directory-pattern.md) for file organization

## Document Status

All documentation reflects the current MCP-first architecture as of Task 25, where operational commands moved from CLI to MCP server operations.

### Recent Updates
- ✅ Created comprehensive API specification
- ✅ Organized journal behavior documentation
- ✅ Consolidated implementation guidance
- ✅ Added table of contents to engineering spec
- ✅ Updated cross-references between documents

## Contributing

When updating code, please also update the relevant documentation:
- **Architecture changes** → Update [Architecture](architecture.md)
- **API changes** → Update [MCP API Specification](mcp-api-specification.md)
- **Journal behavior changes** → Update [Journal Behavior](journal-behavior.md)
- **Implementation patterns** → Update [Implementation Guide](implementation-guide.md) 