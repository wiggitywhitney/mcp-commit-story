"""
Message data extraction module for cursor database operations.

Provides functions to extract and parse user prompts and AI responses from Cursor's
ItemTable key-value structure with robust JSON parsing and error handling.
"""

import json
import logging
from typing import List, Dict, Any

from .query_executor import execute_cursor_query

logger = logging.getLogger(__name__)


def extract_prompts_data(db_path: str) -> List[Dict[str, Any]]:
    """
    Extract user prompts data from the cursor database.
    
    Queries the 'aiService.prompts' key from ItemTable and returns parsed JSON data
    containing user messages with their command types.
    
    Args:
        db_path: Path to the cursor database file
        
    Returns:
        List of prompt dictionaries with 'text' and 'commandType' fields.
        Returns empty list if no data found or all data is malformed.
        
    Raises:
        CursorDatabaseAccessError: If database cannot be accessed
        CursorDatabaseQueryError: If SQL query fails
        
    Design Choice: Skip and log approach for malformed JSON
    - Continue processing other messages when JSON parsing fails
    - Log warnings for skipped messages so users know data was omitted
    - Don't fail the entire operation due to one bad message
    """
    try:
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
                        f"Expected list format for aiService.prompts, got {type(parsed_data).__name__}. "
                        f"Skipping entry in database: {db_path}"
                    )
                    continue
                
                # Add all prompts from this entry
                all_prompts.extend(parsed_data)
                
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(
                    f"Failed to parse JSON for aiService.prompts in database {db_path}: {e}. "
                    f"Skipping malformed entry."
                )
                continue
        
        return all_prompts
        
    except Exception as e:
        # Re-raise database exceptions without modification
        # This allows proper error propagation from execute_cursor_query
        raise


def extract_generations_data(db_path: str) -> List[Dict[str, Any]]:
    """
    Extract AI generations data from the cursor database.
    
    Queries the 'aiService.generations' key from ItemTable and returns parsed JSON data
    containing AI responses with timestamps, UUIDs, and text content.
    
    Args:
        db_path: Path to the cursor database file
        
    Returns:
        List of generation dictionaries with 'unixMs', 'generationUUID', 'type', 
        and 'textDescription' fields. Returns empty list if no data found or all data is malformed.
        
    Raises:
        CursorDatabaseAccessError: If database cannot be accessed
        CursorDatabaseQueryError: If SQL query fails
        
    Design Choices:
    - Skip and log approach for malformed JSON (resilience pattern)
    - Memory strategy: Load everything into memory (100 messages isn't a concern)
    - No batching needed (100 messages is trivial for SQLite)
    """
    try:
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
                        f"Expected list format for aiService.generations, got {type(parsed_data).__name__}. "
                        f"Skipping entry in database: {db_path}"
                    )
                    continue
                
                # Add all generations from this entry  
                all_generations.extend(parsed_data)
                
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(
                    f"Failed to parse JSON for aiService.generations in database {db_path}: {e}. "
                    f"Skipping malformed entry."
                )
                continue
        
        return all_generations
        
    except Exception as e:
        # Re-raise database exceptions without modification
        # This allows proper error propagation from execute_cursor_query
        raise 