"""
Enhanced exception system for cursor database operations.

Provides comprehensive error handling with custom exceptions, context-rich error messages,
and troubleshooting hints for the cursor database module.
"""

import platform
import time
from typing import Dict, Any, Optional


class CursorDatabaseError(Exception):
    """
    Base exception class for all cursor database-related errors.
    
    Provides context collection and troubleshooting hints for debugging and user guidance.
    """
    
    def __init__(self, message: str, **context_kwargs):
        """
        Initialize cursor database error with message and context.
        
        Args:
            message: Human-readable error description
            **context_kwargs: Additional context information for debugging
        """
        super().__init__(message)
        self.message = message
        self.context = self._build_context(**context_kwargs)
        self.troubleshooting_hint = get_troubleshooting_hint(self.__class__.__name__.lower(), self.context)
    
    def _build_context(self, **kwargs) -> Dict[str, Any]:
        """Build comprehensive context information for the error."""
        context = {
            'timestamp': time.time(),
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
        }
        
        # Add all provided context
        context.update(kwargs)
        
        # Sanitize sensitive information
        return self._sanitize_context(context)
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive information from context."""
        sensitive_keys = {'password', 'api_key', 'token', 'secret', 'auth'}
        sanitized = {}
        
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str) and any(sensitive in value.lower() for sensitive in ['password=', 'token=', 'key=']):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value
        
        return sanitized


class CursorDatabaseNotFoundError(CursorDatabaseError):
    """
    Exception raised when cursor database files cannot be found.
    
    This typically occurs when:
    - Cursor hasn't been run recently in the workspace
    - Database files are in unexpected locations
    - Auto-discovery fails to locate valid databases
    """
    
    def __init__(self, message: str, path: Optional[str] = None, **context_kwargs):
        context_kwargs['path'] = path
        super().__init__(message, **context_kwargs)


class CursorDatabaseAccessError(CursorDatabaseError):
    """
    Exception raised when database access is denied due to permissions or locks.
    
    This typically occurs when:
    - File permissions prevent reading the database
    - Database is locked by another process
    - Insufficient system permissions
    """
    
    def __init__(self, message: str, path: Optional[str] = None, permission_type: Optional[str] = None, **context_kwargs):
        context_kwargs.update({'path': path, 'permission_type': permission_type})
        super().__init__(message, **context_kwargs)


class CursorDatabaseSchemaError(CursorDatabaseError):
    """
    Exception raised when database schema doesn't match expectations.
    
    This typically occurs when:
    - Database is from different Cursor version
    - Required tables or columns are missing
    - Schema has been corrupted or modified
    """
    
    def __init__(self, message: str, table_name: Optional[str] = None, expected_schema: Optional[str] = None, **context_kwargs):
        context_kwargs.update({'table_name': table_name, 'expected_schema': expected_schema})
        super().__init__(message, **context_kwargs)


class CursorDatabaseQueryError(CursorDatabaseError):
    """
    Exception raised for query-related errors including syntax and parameter issues.
    
    This typically occurs when:
    - SQL contains syntax errors
    - Wrong number of parameters provided
    - Parameter types don't match expectations
    - Query execution fails for other reasons
    """
    
    def __init__(self, message: str, sql: Optional[str] = None, parameters: Optional[tuple] = None, **context_kwargs):
        context_kwargs.update({'sql': sql, 'parameters': parameters})
        super().__init__(message, **context_kwargs)


def format_error_message(message: str, context: Optional[Dict[str, Any]] = None, 
                        troubleshooting_hint: Optional[str] = None) -> str:
    """
    Format error message with context and troubleshooting information.
    
    Args:
        message: Base error message
        context: Additional context information
        troubleshooting_hint: Optional troubleshooting guidance
    
    Returns:
        Formatted error message with context and hints
    """
    formatted_parts = [message]
    
    if context:
        # Add relevant context information
        if 'path' in context and context['path']:
            formatted_parts.append(f"Path: {context['path']}")
        
        if 'sql' in context and context['sql']:
            # Truncate long SQL for readability
            sql = context['sql']
            if len(sql) > 100:
                sql = sql[:97] + "..."
            formatted_parts.append(f"SQL: {sql}")
        
        if 'operation' in context and context['operation']:
            formatted_parts.append(f"Operation: {context['operation']}")
    
    if troubleshooting_hint:
        formatted_parts.append(f"Troubleshooting: {troubleshooting_hint}")
    
    return " | ".join(formatted_parts)


def get_troubleshooting_hint(error_type: str, context: Dict[str, Any]) -> str:
    """
    Generate context-appropriate troubleshooting hint for different error types.
    
    Args:
        error_type: Type of error (e.g., 'cursordatabasenotfounderror')
        context: Error context information
    
    Returns:
        Helpful troubleshooting hint for the user
    """
    error_type = error_type.lower()
    
    if 'notfound' in error_type:
        hints = [
            "Ensure Cursor has been run recently in this workspace",
            "Check that the workspace contains Cursor chat history",
            "Verify the database path is correct"
        ]
        if context.get('path'):
            hints.append(f"Searched path: {context['path']}")
        return ". ".join(hints) + "."
    
    elif 'access' in error_type:
        permission_type = context.get('permission_type', 'access')
        hints = [
            f"Check file permissions for {permission_type} access",
            "Ensure the database file is not locked by another process",
            "Verify you have sufficient system permissions"
        ]
        if context.get('path'):
            hints.append(f"File path: {context['path']}")
        return ". ".join(hints) + "."
    
    elif 'schema' in error_type:
        hints = [
            "Database schema may be from a different Cursor version",
            "Check if Cursor has been updated recently",
            "Try using a more recent workspace database"
        ]
        if context.get('table_name'):
            hints.append(f"Missing table: {context['table_name']}")
        return ". ".join(hints) + "."
    
    elif 'query' in error_type:
        hints = [
            "Check the SQL query for syntax errors or typos",
            "Verify parameter count matches placeholders",
            "Ensure the query is valid SQLite syntax"
        ]
        param_count = context.get('parameter_count')
        expected_count = context.get('expected_count')
        if param_count is not None and expected_count is not None:
            hints.append(f"Provided {param_count} parameters, expected {expected_count}")
        elif context.get('sql') and '?' in context.get('sql', ''):
            placeholder_count = context['sql'].count('?')
            param_count = len(context.get('parameters', []))
            if placeholder_count != param_count:
                hints.append(f"Query has {placeholder_count} placeholders but {param_count} parameters provided")
        return ". ".join(hints) + "."
    
    # Default hint for unknown error types
    return "Ensure Cursor has been run recently in this workspace and check file permissions." 