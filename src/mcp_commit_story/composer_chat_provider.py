"""
ComposerChatProvider - Main interface for retrieving chat history from Cursor's Composer databases.

This class provides the core functionality for querying Cursor's Composer databases
to retrieve chat messages within specific time windows, with comprehensive error
handling, telemetry, and performance monitoring.
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional

from opentelemetry import trace

from mcp_commit_story.cursor_db.query_executor import execute_cursor_query
from mcp_commit_story.telemetry import trace_mcp_operation, get_mcp_metrics

# Performance threshold for ComposerChatProvider operations (500ms as approved)
COMPOSER_CHAT_PROVIDER_THRESHOLD_MS = 500

# Initialize logger
logger = logging.getLogger(__name__)


class ComposerChatProvider:
    """
    Main interface class for retrieving chat history from Cursor's Composer databases.
    
    This class connects to both workspace and global Composer databases to retrieve
    chat messages within specific time windows. It provides comprehensive error
    handling, telemetry integration, and performance monitoring.
    
    Design Features (per approved design):
    - Per-request connections with no connection pooling
    - No caching - query fresh data every time  
    - Reuses existing execute_cursor_query infrastructure
    - Bubbles up database errors from execute_cursor_query
    - Comprehensive telemetry with @trace_mcp_operation decorator
    - Performance threshold monitoring (500ms)
    - Debug logging for empty results
    """

    def __init__(self, workspace_db_path: str, global_db_path: str):
        """
        Initialize ComposerChatProvider with database paths.
        
        Per approved design, this constructor does NOT validate database existence
        or establish connections. Database validation happens at query time following
        the connection.py patterns.
        
        Args:
            workspace_db_path: Path to workspace database (workspaceStorage/{hash}/state.vscdb)
            global_db_path: Path to global database (globalStorage/state.vscdb)
        """
        self.workspace_db_path = workspace_db_path
        self.global_db_path = global_db_path

    @trace_mcp_operation("composer_chat_retrieval")
    def getChatHistoryForCommit(self, start_timestamp_ms: int, end_timestamp_ms: int) -> List[Dict[str, Any]]:
        """
        Retrieve chat history for a commit within a specific time window.
        
        Args:
            start_timestamp_ms: Start of time window (milliseconds since epoch)
            end_timestamp_ms: End of time window (milliseconds since epoch)
            
        Returns:
            List of formatted message dictionaries sorted chronologically
            
        Raises:
            CursorDatabaseNotFoundError: When database files don't exist
            CursorDatabaseAccessError: When databases cannot be accessed
            CursorDatabaseQueryError: When queries fail
            CursorDatabaseSchemaError: When database schema is unexpected
        """
        start_time = time.time()
        
        try:
            # Get session metadata from workspace database
            session_metadata = self._get_session_metadata()
            
            if not session_metadata:
                logger.debug("No composer sessions found in workspace database")
                self._record_metrics("no_sessions", start_time, 0)
                return []
            
            all_messages = []
            
            # Process each session
            for session in session_metadata:
                composer_id = session.get('composerId')
                session_name = session.get('name', 'Unknown Session')
                session_created_at = session.get('createdAt', 0)  # Get timestamp from session metadata
                
                if not composer_id:
                    continue
                
                # Check if this session falls within the time window
                if not (start_timestamp_ms <= session_created_at <= end_timestamp_ms):
                    continue  # Skip session if outside time window
                
                # Get message headers from global database
                message_headers = self._get_message_headers(composer_id)
                
                if not message_headers:
                    continue
                
                # Get messages for this session, passing session timestamp
                session_messages = self._get_session_messages(
                    composer_id,
                    session_name,
                    message_headers,
                    session_created_at  # Pass session timestamp
                )
                
                all_messages.extend(session_messages)
            
            # Sort all messages chronologically by session timestamp
            all_messages.sort(key=lambda msg: msg['timestamp'])
            
            if not all_messages:
                logger.debug(f"No messages found in time window {start_timestamp_ms} to {end_timestamp_ms}")
            
            self._record_metrics("success", start_time, len(all_messages))
            
            return all_messages
            
        except Exception as e:
            # Let database errors bubble up as per approved design
            # Record metrics for failed operations
            self._record_metrics("error", start_time, 0)
            raise

    def _get_session_metadata(self) -> List[Dict[str, Any]]:
        """
        Retrieve session metadata from workspace database.
        
        Returns:
            List of session metadata dictionaries from allComposers array
            
        Raises:
            CursorDatabaseAccessError: When workspace database cannot be accessed
            CursorDatabaseQueryError: When query fails
            json.JSONDecodeError: When JSON data is malformed
        """
        # Query workspace database for composer metadata
        result = execute_cursor_query(
            self.workspace_db_path,
            "SELECT value FROM ItemTable WHERE [key] = 'composer.composerData'"
        )
        
        if not result:
            return []
        
        # Parse JSON metadata
        metadata_json = result[0][0]
        metadata = json.loads(metadata_json)
        
        # Return sessions from allComposers array
        return metadata.get('allComposers', [])

    def _get_message_headers(self, composer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve message headers for a specific session from global database.
        
        Args:
            composer_id: Unique identifier for the composer session
            
        Returns:
            Message headers dictionary or None if not found
            
        Raises:
            CursorDatabaseAccessError: When global database cannot be accessed
            CursorDatabaseQueryError: When query fails
            json.JSONDecodeError: When JSON data is malformed
        """
        # Query global database for message headers
        result = execute_cursor_query(
            self.global_db_path,
            "SELECT value FROM cursorDiskKV WHERE [key] = ?",
            (f"composerData:{composer_id}",)
        )
        
        if not result:
            return None
        
        # Parse JSON headers
        headers_json = result[0][0]
        return json.loads(headers_json)

    def _get_session_messages(
        self,
        composer_id: str,
        session_name: str,
        message_headers: Dict[str, Any],
        session_created_at: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve and filter individual messages for a session.
        
        Args:
            composer_id: Session identifier
            session_name: Human-readable session name
            message_headers: Message headers containing conversation structure
            session_created_at: Session creation timestamp
            
        Returns:
            List of formatted message dictionaries within time window
        """
        messages = []
        
        # Get conversation headers (message list)
        conversation_headers = message_headers.get('fullConversationHeadersOnly', [])
        
        for header in conversation_headers:
            bubble_id = header.get('bubbleId')
            message_type = header.get('type')
            
            if not bubble_id or message_type is None:
                continue
            
            # Get individual message content
            message_data = self._get_individual_message(composer_id, bubble_id)
            
            if not message_data:
                continue
            
            # Format message according to enhanced structure
            # Use session timestamp for all messages (individual messages don't have timestamps)
            formatted_message = {
                'role': self._map_message_type_to_role(message_type),
                'content': message_data.get('text', ''),
                'timestamp': session_created_at,  # Use session timestamp, not individual message timestamp
                'sessionName': session_name,
                'composerId': composer_id,
                'bubbleId': bubble_id
            }
            
            messages.append(formatted_message)
        
        return messages

    def _get_individual_message(self, composer_id: str, bubble_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve individual message content from global database.
        
        Args:
            composer_id: Session identifier
            bubble_id: Unique message identifier
            
        Returns:
            Message data dictionary or None if not found
            
        Raises:
            CursorDatabaseAccessError: When global database cannot be accessed
            CursorDatabaseQueryError: When query fails
            json.JSONDecodeError: When JSON data is malformed
        """
        # Query global database for individual message
        result = execute_cursor_query(
            self.global_db_path,
            "SELECT value FROM cursorDiskKV WHERE [key] = ?",
            (f"bubbleId:{composer_id}:{bubble_id}",)
        )
        
        if not result:
            return None
        
        # Parse JSON message data
        message_json = result[0][0]
        return json.loads(message_json)

    def _map_message_type_to_role(self, message_type: int) -> str:
        """
        Map Cursor message type to standard role format.
        
        Args:
            message_type: Cursor message type (1 = user, 2 = assistant)
            
        Returns:
            Standardized role string ('user' or 'assistant')
        """
        if message_type == 1:
            return 'user'
        elif message_type == 2:
            return 'assistant'
        else:
            # Default to user for unknown types
            return 'user'

    def _record_metrics(self, strategy: str, start_time: float, message_count: int) -> None:
        """
        Record performance metrics and check threshold.
        
        Args:
            strategy: Operation outcome (success, no_sessions, error)
            start_time: Operation start time (from time.time())
            message_count: Number of messages retrieved
        """
        duration_ms = (time.time() - start_time) * 1000
        
        # Get metrics instance
        metrics = get_mcp_metrics()
        
        if metrics:
            try:
                # Counter metric for operation outcomes
                metrics.record_counter(
                    "mcp_composer_chat_total",
                    value=1,
                    attributes={
                        "strategy": strategy,
                        "success": str(strategy == "success").lower()
                    }
                )
                
                # Histogram metric for operation duration
                metrics.record_histogram(
                    "mcp_composer_chat_duration_ms",
                    value=duration_ms,
                    attributes={"strategy": strategy}
                )
                
                # Message count histogram
                metrics.record_histogram(
                    "mcp_composer_chat_message_count",
                    value=message_count,
                    attributes={"strategy": strategy}
                )
                
            except Exception:
                # Ignore metrics errors to avoid disrupting main functionality
                pass
        
        # Performance threshold monitoring (500ms as approved)
        if duration_ms > COMPOSER_CHAT_PROVIDER_THRESHOLD_MS:
            logger.warning(
                f"ComposerChatProvider operation exceeded {COMPOSER_CHAT_PROVIDER_THRESHOLD_MS}ms threshold: "
                f"{duration_ms:.1f}ms (strategy: {strategy})"
            )
        
        # Set span attributes for telemetry
        self._set_span_attributes(strategy, duration_ms, message_count)

    def _set_span_attributes(self, strategy: str, duration_ms: float, message_count: int) -> None:
        """
        Set telemetry span attributes for ComposerChatProvider operations.
        
        Args:
            strategy: Operation outcome
            duration_ms: Operation duration in milliseconds
            message_count: Number of messages retrieved
        """
        try:
            span = trace.get_current_span()
            if span:
                span.set_attribute("composer_chat.strategy", strategy)
                span.set_attribute("composer_chat.duration_ms", duration_ms)
                span.set_attribute("composer_chat.message_count", message_count)
                span.set_attribute("composer_chat.workspace_db_path", self.workspace_db_path)
                span.set_attribute("composer_chat.global_db_path", self.global_db_path)
                
                # Performance threshold attribute
                span.set_attribute(
                    "composer_chat.threshold_exceeded", 
                    duration_ms > COMPOSER_CHAT_PROVIDER_THRESHOLD_MS
                )
                
        except Exception:
            # Ignore telemetry errors to avoid disrupting main functionality
            pass 