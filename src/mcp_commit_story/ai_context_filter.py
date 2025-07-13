"""
AI-powered context filtering for MCP Journal.

This module uses AI to intelligently filter chat conversations when generating journal entries
for git commits. It identifies conversation boundaries to separate work on the current commit
from previous development work, ensuring journal entries contain only relevant context.

Key Features:
- Analyzes chat conversations to find where current commit work begins
- Removes irrelevant conversation history before the boundary
- Provides confidence scoring and reasoning for boundary detection
- Handles edge cases like empty conversations or missing context
- Integrates with git history and previous journal entries

The filtering helps create focused, accurate journal entries by removing conversations
about unrelated work or previous commits.
"""
import os
import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, TypedDict
from git import Commit

from .git_utils import get_previous_commit_info
from .telemetry import trace_mcp_operation
from .context_types import ChatMessage
from .ai_invocation import invoke_ai
from .config import load_config

logger = logging.getLogger(__name__)


class BoundaryResponse(TypedDict):
    """Type-safe structure for AI boundary detection response.
    
    Represents the AI's decision about where to place the conversation
    boundary for filtering messages related to a specific commit.
    
    Attributes:
        bubbleId: The ID of the message that marks the boundary point.
                 All messages from this point onward are kept.
        confidence: Integer from 1-10 indicating AI's confidence in the decision.
                   Higher values mean more certain boundary detection.
        reasoning: Human-readable explanation of why this boundary was chosen.
                  Helps with debugging and understanding AI decisions.
    """
    bubbleId: str
    confidence: int
    reasoning: str


@trace_mcp_operation("ai_context_filter.get_previous_journal_entry")
def get_previous_journal_entry(commit: Commit) -> Optional[str]:
    """Get the most recent journal entry for context.
    
    Looks for the most recent journal entry from the previous day's journal
    to provide context for AI boundary detection.
    
    Args:
        commit: Git commit object to get previous journal entry for
        
    Returns:
        Contents of the most recent journal entry, or None if not found
    """
    try:
        # Load config to get journal path
        config = load_config()
        
        # Get journal path configuration
        if hasattr(config, 'journal_path'):
            journal_base_path = config.journal_path
        else:
            journal_base_path = config.get("journal", {}).get("path", "journal")
        
        # Get the date of the current commit
        commit_date = datetime.fromtimestamp(commit.committed_date)
        
        # Try to find a journal file from the previous day(s)
        for days_back in range(1, 8):  # Check up to 7 days back
            previous_date = commit_date - timedelta(days=days_back)
            journal_filename = f"{previous_date.strftime('%Y-%m-%d')}-journal.md"
            journal_path = os.path.join(journal_base_path, "daily", journal_filename)
            
            if os.path.exists(journal_path):
                with open(journal_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract the most recent entry from the journal
                # Pattern to match journal entry headers
                header_pattern = re.compile(
                    r'^(#{2,3})\s*(.+?)\s*[-—]\s*Commit\s+([\w-]+)',
                    re.MULTILINE | re.IGNORECASE
                )
                
                matches = list(header_pattern.finditer(content))
                
                if matches:
                    # Get the last entry in the file
                    last_match = matches[-1]
                    start_pos = last_match.start()
                    end_pos = len(content)
                    
                    entry_content = content[start_pos:end_pos].strip()
                    logger.debug(f"Found previous journal entry from {previous_date.strftime('%Y-%m-%d')}")
                    return entry_content
        
        logger.debug("No previous journal entries found")
        return None
            
    except Exception as e:
        logger.warning(f"Error getting previous journal entry: {e}")
        return None


@trace_mcp_operation("ai_context_filter.filter_chat")
def filter_chat_for_commit(
    messages: List[ChatMessage], 
    commit: Commit, 
    git_context: Optional[Dict[str, Any]] = None
) -> List[ChatMessage]:
    """Use AI to filter chat messages to only those relevant to the commit.
    
    Analyzes the conversation to identify the boundary where work for the
    current commit begins, using AI to understand context and transitions.
    
    Args:
        messages: List of chat messages to analyze for boundary detection
        commit: Git commit object to analyze for context
        git_context: Optional pre-collected git context. If None, a minimal context will be created.
        
    Returns:
        Filtered list of messages from the detected boundary onwards
    """
    if not messages:
        logger.warning("No messages provided for filtering")
        return []

    # Validate that all messages have bubbleId field
    for i, msg in enumerate(messages):
        if 'bubbleId' not in msg:
            logger.error(f"Message {i+1} is missing bubbleId field. This indicates a data pipeline issue.")
            raise ValueError(f"AI filtering requires bubbleId field in all messages. Message {i+1} is missing this field. Check data extraction pipeline.")

    try:
        # Use provided git context or create minimal context
        if git_context is None:
            # Minimal git context for backward compatibility
            git_context = {
                'metadata': {
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'date': commit.committed_datetime.isoformat()
                },
                'changed_files': [],
                'diff_summary': 'Git context not provided'
            }
        
        # Get previous commit information for context
        previous_commit = get_previous_commit_info(commit)
        
        # Get previous journal entry for additional context
        previous_journal = get_previous_journal_entry(commit)
        
        # Limit to last 250 messages to reduce AI context overload
        limited_messages = messages[-250:] if len(messages) > 250 else messages
        
        # Simplify message structure for AI - only essential fields
        simplified_messages = []
        for msg in limited_messages:
            simplified_messages.append({
                "bubbleId": msg.get("bubbleId", ""),
                "speaker": msg.get("speaker", "Unknown"),
                "timestamp": msg.get("timestamp", ""),
                "preview": msg.get("text", "")[:100] + ("..." if len(msg.get("text", "")) > 100 else "")
            })
        
        # Format the comprehensive AI prompt with all context
        prompt = f"""You are helping build a high-quality development journal system that tracks 
coding work across commits. Your job is to analyze a conversation and identify 
the exact point where work for the CURRENT commit begins.

## Your Task
Find the single message (bubbleId) that marks the boundary where the current 
commit's work starts. Everything from that message onward should be kept in 
the filtered conversation.

## Key Principles
1. **Boundary Approach**: Return exactly ONE bubbleId that marks where current work begins
2. **Everything After**: All messages from the boundary onward are kept  
3. **Context Clues**: Look for explicit statements about starting new work
4. **File References**: Pay attention to mentions of files that were changed
5. **Task Transitions**: Notice when conversation shifts between different features/bugs

## Context Analysis Strategy
- **Git Context**: Examine files changed, commit message, and commit metadata
- **Previous Commit**: Understand what was accomplished in the prior commit  
- **Previous Journal**: Review what was documented about earlier work
- **Conversation Flow**: Track the logical progression of the discussion

## Decision Guidelines

### HIGH CONFIDENCE (8-10): Clear, explicit boundaries
- Direct statements: "Now let's work on X", "Starting the Y feature", "Moving to Z"
- File context matches: Discussion shifts to files that were actually changed
- Task completion signals: "That's done, now for...", "Finished X, next is Y"

### MEDIUM CONFIDENCE (5-7): Reasonable but ambiguous boundaries  
- Topic shifts that align with commit content but aren't explicitly stated
- File mentions that partially match changed files
- Conversational transitions that suggest new work

### LOW CONFIDENCE (1-4): Guessing or unclear
- No clear transition points in the conversation
- Multiple possible boundaries with equal evidence
- Conversation doesn't clearly relate to the commit changes

## Verification Checklist
Before finalizing your decision, verify:
1. ✅ The bubbleId you chose actually exists in the provided message list
2. ✅ The boundary makes logical sense given the commit's file changes
3. ✅ Messages after the boundary discuss work that relates to this commit
4. ✅ Messages before the boundary discuss different work (if any)
5. ✅ Your confidence level honestly reflects the clarity of the boundary

## Edge Cases
- **No clear boundary**: If you can't find a meaningful boundary, return the first message with low confidence
- **Entire conversation relevant**: Return first message with note about full relevance
- **Single-message conversation**: Return that message with appropriate confidence

## Response Format
Always respond with valid JSON in exactly this structure:
{{
  "bubbleId": "the-boundary-bubble-id",
  "confidence": 8,
  "reasoning": "explanation of why this is the boundary"
}}

Messages to analyze (limited to last 250 for clarity):
{json.dumps(simplified_messages, indent=2)}

Current commit information:
- **Commit Message**: {git_context.get('metadata', {}).get('message', 'N/A')}
- **Changed Files**: {', '.join(git_context.get('changed_files', []))}
- **Diff Summary**: {git_context.get('diff_summary', 'N/A')}

Full current commit context:
{json.dumps(git_context, indent=2)}

Previous commit:
{json.dumps(previous_commit, indent=2)}

Previous journal entry:
{json.dumps(previous_journal, indent=2)}

Return your response as JSON with this structure:
{{
  "bubbleId": "the-boundary-bubble-id",
  "confidence": 8,
  "reasoning": "explanation of why this is the boundary"
}}"""

        # Debug logging for AI prompt (only in debug mode)
        if os.getenv('DEBUG_AI_FILTERING'):
            logger.debug(f"AI Context Filter Prompt:\n{prompt}")

        # Call AI for boundary detection
        logger.info(f"Calling AI to analyze {len(messages)} messages for commit {commit.hexsha[:8]}")
        ai_response = invoke_ai(prompt, {})
        
        # Parse the AI response
        boundary_result = _parse_ai_response(ai_response)
        
        # Validate the bubbleId exists in the messages
        valid_bubble_ids = {msg['bubbleId'] for msg in messages}
        if boundary_result['bubbleId'] not in valid_bubble_ids:
            # Smart fallback: default to last 250 messages instead of all messages
            if len(messages) > 250:
                fallback_index = len(messages) - 250
                fallback_bubble_id = messages[fallback_index]['bubbleId']
                fallback_reasoning = "AI returned invalid bubbleId, defaulted to last 250 messages"
            else:
                fallback_index = 0
                fallback_bubble_id = messages[0]['bubbleId']
                fallback_reasoning = "AI returned invalid bubbleId, defaulted to first message (fewer than 250 total)"
            
            logger.warning(f"AI returned invalid bubbleId '{boundary_result['bubbleId']}', using fallback at index {fallback_index}")
            boundary_result['bubbleId'] = fallback_bubble_id
            boundary_result['confidence'] = 1
            boundary_result['reasoning'] = fallback_reasoning

        # Log confidence and reasoning
        confidence = boundary_result['confidence']
        reasoning = boundary_result['reasoning']
        
        if confidence < 7:
            logger.warning(f"Low confidence AI boundary (confidence={confidence}): {reasoning}")
        else:
            logger.info(f"AI boundary detection (confidence={confidence}): {reasoning}")

        # Filter messages from the boundary onwards
        boundary_index = next(
            i for i, msg in enumerate(messages) 
            if msg['bubbleId'] == boundary_result['bubbleId']
        )
        
        filtered_messages = messages[boundary_index:]
        
        # Streamline chat data - remove unnecessary metadata
        streamlined_messages = []
        for msg in filtered_messages:
            streamlined_messages.append({
                "speaker": msg.get("speaker", "Unknown"),
                "text": msg.get("text", "")
            })
        
        logger.info(f"Filtered {len(messages)} → {len(streamlined_messages)} messages using AI boundary (streamlined)")
        return streamlined_messages

    except Exception as e:
        logger.error(f"Error in AI context filtering: {e}")
        
        # Smart fallback: return last 250 messages instead of all messages
        if len(messages) > 250:
            fallback_messages = messages[-250:]
        else:
            fallback_messages = messages
            
        # Streamline fallback messages too - remove unnecessary metadata
        streamlined_fallback = []
        for msg in fallback_messages:
            streamlined_fallback.append({
                "speaker": msg.get("speaker", "Unknown"), 
                "text": msg.get("text", "")
            })
        
        logger.info(f"AI filtering failed, using smart fallback: returning {len(streamlined_fallback)} streamlined messages")
        return streamlined_fallback


def _parse_ai_response(ai_response: str) -> BoundaryResponse:
    """Parse AI response into a BoundaryResponse structure.
    
    Args:
        ai_response: Raw JSON response from AI containing boundary detection
        
    Returns:
        Parsed BoundaryResponse with bubbleId, confidence, and reasoning
        
    Raises:
        ValueError: If the response cannot be parsed into valid BoundaryResponse
    """
    if not ai_response or not ai_response.strip():
        raise ValueError("Empty AI response")

    try:
        # Parse JSON response
        response_data = json.loads(ai_response.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in AI response: {e}")
    
    # Validate required fields
    if not isinstance(response_data, dict):
        raise ValueError("AI response must be a JSON object")
    
    if 'bubbleId' not in response_data:
        raise ValueError("AI response missing required 'bubbleId' field")
    
    if 'confidence' not in response_data:
        raise ValueError("AI response missing required 'confidence' field")
    
    if 'reasoning' not in response_data:
        raise ValueError("AI response missing required 'reasoning' field")
    
    # Validate and clean bubbleId
    bubble_id = response_data['bubbleId']
    if not isinstance(bubble_id, str):
        raise ValueError("bubbleId must be a non-empty string")
    bubble_id = bubble_id.strip()
    if not bubble_id:
        raise ValueError("bubbleId must be a non-empty string")
    
    # Validate confidence is an integer between 1-10
    confidence = response_data['confidence']
    if not isinstance(confidence, int) or confidence < 1 or confidence > 10:
        raise ValueError("confidence must be an integer between 1 and 10")
    
    # Validate and clean reasoning
    reasoning = response_data['reasoning']
    if not isinstance(reasoning, str):
        raise ValueError("reasoning must be a non-empty string")
    reasoning = reasoning.strip()
    if not reasoning:
        raise ValueError("reasoning must be a non-empty string")
    
    # Create the BoundaryResponse
    return BoundaryResponse(
        bubbleId=bubble_id,
        confidence=confidence,
        reasoning=reasoning
    ) 