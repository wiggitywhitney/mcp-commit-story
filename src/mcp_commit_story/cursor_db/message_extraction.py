"""
Message data extraction module for cursor database operations.

Provides functions to extract and parse chat messages from Cursor's database
with robust JSON parsing and error handling.

Telemetry instrumentation tracks:
- Query + JSON parsing performance against 100ms thresholds
- Data counts and quality metrics for extracted messages
- JSON parse error tracking for data quality monitoring
- Truncation detection for message limits
"""

import json
import logging
import time
from typing import List, Dict, Any

from opentelemetry import trace

from .query_executor import execute_cursor_query
from ..telemetry import trace_mcp_operation, PERFORMANCE_THRESHOLDS

logger = logging.getLogger(__name__)


@trace_mcp_operation("cursor_db.extract_prompts")
def extract_prompts_data(db_path: str) -> List[Dict[str, Any]]:
    """
    Extract user message data from the cursor database.
    
    Queries the chat database and returns parsed JSON data
    containing user messages with their metadata.
    
    Telemetry Metrics Tracked:
        - database_path: Which database file was queried
        - query_duration_ms: Total time for query + JSON parsing
        - prompt_count: Number of messages successfully extracted
        - json_parse_errors: Count of malformed JSON entries skipped
        - threshold_exceeded: Boolean if duration > 100ms threshold
    
    Threshold Rationale:
        100ms accounts for SQLite query + JSON parsing of typical message entries.
        Higher than basic query due to JSON deserialization overhead.
    
    Args:
        db_path: Path to the cursor database file
        
    Returns:
        List of message dictionaries with 'text' and 'commandType' fields.
        Returns empty list if no data found or all data is malformed.
        
    Raises:
        CursorDatabaseAccessError: If database cannot be accessed
        CursorDatabaseQueryError: If SQL query fails
        
    Design Choice: Skip and log approach for malformed JSON
    - Continue processing other messages when JSON parsing fails
    - Log warnings for skipped messages so users know data was omitted
    - Don't fail the entire operation due to one bad message
    """
    start_time = time.time()
    span = trace.get_current_span()
    json_parse_errors = 0
    
    try:
        # Set initial telemetry attributes
        span.set_attribute("database_path", db_path)
        
        # Query the database for prompts data
        raw_data = execute_cursor_query(
            db_path,
            "SELECT [key], value FROM ItemTable WHERE [key] = ?",
            ("aiService.prompts",)
        )
        
        all_prompts = []
        
        # Process each row (there should typically be only one)
        for key, value in raw_data:
            try:
                # Decode the BLOB value and parse JSON
                if isinstance(value, bytes):
                    json_str = value.decode('utf-8')
                else:
                    json_str = str(value)
                    
                parsed_data = json.loads(json_str)
                
                # Validate that it's a list format
                if not isinstance(parsed_data, list):
                    logger.warning(
                        f"Expected list format for chat messages, got {type(parsed_data).__name__}. "
                        f"Skipping entry in database: {db_path}"
                    )
                    continue
                
                # Add all prompts from this entry
                all_prompts.extend(parsed_data)
                
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                json_parse_errors += 1
                logger.warning(
                    f"Failed to parse JSON for chat messages in database {db_path}: {e}. "
                    f"Skipping malformed entry."
                )
                continue
        
        # Calculate duration and set final telemetry attributes
        duration_ms = (time.time() - start_time) * 1000
        span.set_attribute("query_duration_ms", duration_ms)
        span.set_attribute("prompt_count", len(all_prompts))
        span.set_attribute("json_parse_errors", json_parse_errors)
        
        # Check performance threshold
        threshold = PERFORMANCE_THRESHOLDS["extract_prompts_data"]
        span.set_attribute("threshold_exceeded", duration_ms > threshold)
        if duration_ms > threshold:
            span.set_attribute("threshold_ms", threshold)
        
        return all_prompts
        
    except Exception as e:
        # Re-raise database exceptions without modification
        # This allows proper error propagation from execute_cursor_query
        raise


@trace_mcp_operation("cursor_db.extract_generations")
def extract_generations_data(db_path: str) -> List[Dict[str, Any]]:
    """
    Extract AI response data from the cursor database.
    
    Queries the chat database and returns parsed JSON data
    containing AI responses with timestamps, UUIDs, and text content.
    
    Telemetry Metrics Tracked:
        - database_path: Which database file was queried
        - query_duration_ms: Total time for query + JSON parsing
        - generation_count: Number of responses successfully extracted
        - json_parse_errors: Count of malformed JSON entries skipped
        - truncation_detected: Boolean if generation_count == 100 (database limit)
        - threshold_exceeded: Boolean if duration > 100ms threshold
    
    Threshold Rationale:
        100ms accounts for SQLite query + JSON parsing of typical response entries.
        Responses contain more text data than prompts, requiring similar threshold.
    
    Args:
        db_path: Path to the cursor database file
        
    Returns:
        List of response dictionaries with 'unixMs', 'generationUUID', 'type', 
        and 'textDescription' fields. Returns empty list if no data found or all data is malformed.
        
    Raises:
        CursorDatabaseAccessError: If database cannot be accessed
        CursorDatabaseQueryError: If SQL query fails
        
    Design Choices:
    - Skip and log approach for malformed JSON (resilience pattern)
    - Memory strategy: Load everything into memory (typical message count isn't a concern)
    - No batching needed (typical message count is trivial for SQLite)
    """
    start_time = time.time()
    span = trace.get_current_span()
    json_parse_errors = 0
    
    try:
        # Set initial telemetry attributes
        span.set_attribute("database_path", db_path)
        
        # Query the database for generations data
        raw_data = execute_cursor_query(
            db_path,
            "SELECT [key], value FROM ItemTable WHERE [key] = ?",
            ("aiService.generations",)
        )
        
        all_generations = []
        
        # Process each row (there should typically be only one)
        for key, value in raw_data:
            try:
                # Decode the BLOB value and parse JSON
                if isinstance(value, bytes):
                    json_str = value.decode('utf-8')
                else:
                    json_str = str(value)
                    
                parsed_data = json.loads(json_str)
                
                # Validate that it's a list format
                if not isinstance(parsed_data, list):
                    logger.warning(
                        f"Expected list format for chat responses, got {type(parsed_data).__name__}. "
                        f"Skipping entry in database: {db_path}"
                    )
                    continue
                
                # Add all generations from this entry  
                all_generations.extend(parsed_data)
                
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                json_parse_errors += 1
                logger.warning(
                    f"Failed to parse JSON for chat responses in database {db_path}: {e}. "
                    f"Skipping malformed entry."
                )
                continue
        
        # Calculate duration and set final telemetry attributes
        duration_ms = (time.time() - start_time) * 1000
        span.set_attribute("query_duration_ms", duration_ms)
        span.set_attribute("generation_count", len(all_generations))
        span.set_attribute("json_parse_errors", json_parse_errors)
        
        # Check for truncation (100 generations indicates potential database capacity limit)
        span.set_attribute("truncation_detected", len(all_generations) == 100)
        
        # Check performance threshold
        threshold = PERFORMANCE_THRESHOLDS["extract_generations_data"]
        span.set_attribute("threshold_exceeded", duration_ms > threshold)
        if duration_ms > threshold:
            span.set_attribute("threshold_ms", threshold)
        
        return all_generations
        
    except Exception as e:
        # Re-raise database exceptions without modification
        # This allows proper error propagation from execute_cursor_query
        raise 