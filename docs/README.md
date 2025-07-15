# MCP Commit Story Documentation

This directory contains the complete technical documentation for the MCP Commit Story project.

## Documentation Overview

### 📋 Start Here
- **[Architecture](architecture.md)** - High-level system design, architectural decisions, and component relationships

### 🔧 Technical References
- **[MCP API Specification](mcp-api-specification.md)** - Complete reference for MCP operations, data formats, and client integration
- **[Setup CLI Reference](setup-cli.md)** - Human-friendly setup commands and architecture philosophy
- **[Journal Core](journal-core.md)** - Core journal functionality, classes, and AI generation system
- **[Context Collection](context-collection.md)** - Context gathering system and type definitions for AI generation
- **[Reflection Core](reflection-core.md)** - Manual reflection addition system with validation and telemetry
- **[Telemetry](telemetry.md)** - Comprehensive telemetry, monitoring, and observability system
- **[Structured Logging](structured-logging.md)** - JSON logging with trace correlation and sensitive data protection
- **[Multi-Exporter](multi-exporter.md)** - OpenTelemetry exporter configuration with environment precedence
- **[Journal Behavior](journal-behavior.md)** - How journal entries are generated, structured, and configured
- **[Implementation Guide](implementation-guide.md)** - Detailed development guidance, patterns, and technical implementation

### 🎯 Development Guides
- **[Testing Standards](testing_standards.md)** - Testing approaches, standards, and quality requirements
- **[On-Demand Directory Pattern](on-demand-directory-pattern.md)** - File system organization and directory creation patterns
- **[AI Function Pattern](ai_function_pattern.md)** - Patterns for AI-powered functionality
- **[Journal Behavior](journal-behavior.md)** - Journal initialization process and configuration
- **[Server Setup](server_setup.md)** - MCP server setup and deployment

## Quick Navigation

### For New Developers
1. Read [Architecture](architecture.md) for system overview
2. Review [Implementation Guide](implementation-guide.md) for development setup
3. Check [Testing Standards](testing_standards.md) for quality requirements

### For API Integration
1. Start with [MCP API Specification](mcp-api-specification.md)
2. Reference [Setup CLI Reference](setup-cli.md) for setup vs operational command boundaries
3. Review [Journal Behavior](journal-behavior.md) for content structure
4. Check [Architecture](architecture.md) for integration patterns

### For Journal Configuration
1. See [Journal Behavior](journal-behavior.md) for configuration options
2. Check [Journal Behavior](journal-behavior.md) for setup process
3. Reference [On-Demand Directory Pattern](on-demand-directory-pattern.md) for file organization

### For Core System Understanding
1. Review [Journal Core](journal-core.md) for entry generation system
2. Check [Context Collection](context-collection.md) for data gathering
3. See [Reflection Core](reflection-core.md) for manual reflection features

### For Monitoring and Observability
1. Start with [Telemetry](telemetry.md) for comprehensive monitoring
2. Review [Structured Logging](structured-logging.md) for logging capabilities
3. Check [Multi-Exporter](multi-exporter.md) for exporter configuration

## Document Status

All documentation reflects the current MCP-first architecture where operational commands are handled by the MCP server rather than CLI.

### Recent Updates
- ✅ Created comprehensive API specification
- ✅ Documented all core system modules (journal, context, reflection, telemetry, logging, multi-exporter)
- ✅ Organized journal behavior documentation
- ✅ Consolidated implementation guidance
- ✅ Added table of contents to engineering spec
- ✅ Updated cross-references between documents

## Contributing

When updating code, please also update the relevant documentation:
- **Architecture changes** → Update [Architecture](architecture.md)
- **API changes** → Update [MCP API Specification](mcp-api-specification.md)
- **CLI changes** → Update [Setup CLI Reference](setup-cli.md)
- **Journal behavior changes** → Update [Journal Behavior](journal-behavior.md) and [Journal Core](journal-core.md)
- **Context collection changes** → Update [Context Collection](context-collection.md)
- **Reflection system changes** → Update [Reflection Core](reflection-core.md)
- **Telemetry changes** → Update [Telemetry](telemetry.md), [Structured Logging](structured-logging.md), or [Multi-Exporter](multi-exporter.md)
- **Implementation patterns** → Update [Implementation Guide](implementation-guide.md) 