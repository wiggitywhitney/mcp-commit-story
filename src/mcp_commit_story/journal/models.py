"""
Journal models for data structures and parsing.

Contains the core data models for journal entries and parsing logic.
"""
import re
from typing import List, Optional, Dict, Union, Any
from ..telemetry import trace_mcp_operation, get_mcp_metrics
from ..journal_generate import JournalEntry


class JournalParseError(Exception):
    pass



class JournalParser:
    @staticmethod
    @trace_mcp_operation("journal.parse_entry", attributes={"operation_type": "file_read", "file_type": "markdown"})
    def parse(md):
        """
        Parse markdown content into a JournalEntry object.
        
        Args:
            md: Markdown content to parse
            
        Returns:
            JournalEntry: Parsed journal entry
            
        Raises:
            JournalParseError: If the markdown cannot be parsed
        """
        import time
        from opentelemetry import trace
        
        start_time = time.time()
        
        # Add semantic conventions for telemetry
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("journal.content_length", len(md) if md else 0)
            current_span.set_attribute("journal.operation_type", "parse")
        
        try:
            if not md or not md.strip():
                if current_span:
                    current_span.set_attribute("error.category", "empty_content")
                raise JournalParseError('Empty entry')
            
            # Parse H4 (####) headers for all sections
            def extract_section(header):
                pattern = rf"#### {header}\n(.+?)(?=\n#### |\Z)"
                m = re.search(pattern, md, re.DOTALL)
                return m.group(1).strip() if m else ''
            
            timestamp_commit = re.search(r"###\s+(.*?) — Commit ([a-zA-Z0-9]+)", md)
            if timestamp_commit:
                timestamp = timestamp_commit.group(1)
                commit_hash = timestamp_commit.group(2)
                
                # Add parsed commit info to span
                if current_span:
                    current_span.set_attribute("journal.entry_id", commit_hash)
                    current_span.set_attribute("journal.timestamp", timestamp)
                
                summary = extract_section("Summary")
                technical_synopsis = extract_section("Technical Synopsis")
                
                # Accomplishments
                accomplishments = []
                acc_section = extract_section("Accomplishments")
                if acc_section:
                    accomplishments = [line[2:].strip() for line in acc_section.splitlines() if line.startswith('- ')]
                
                # Frustrations
                frustrations = []
                frus_section = extract_section("Frustrations or Roadblocks")
                if frus_section:
                    frustrations = [line[2:].strip() for line in frus_section.splitlines() if line.startswith('- ')]
                
                # Tone/Mood
                tone_mood = None
                tm_section = extract_section("Tone/Mood")
                if tm_section:
                    tm_lines = [l.strip('> ').strip() for l in tm_section.splitlines() if l.strip().startswith('>')]
                    mood = tm_lines[0] if len(tm_lines) >= 1 else ''
                    indicators = tm_lines[1] if len(tm_lines) >= 2 else ''
                    if mood or indicators:
                        tone_mood = {"mood": mood, "indicators": indicators}
                    else:
                        tone_mood = None
                
                # Discussion Notes
                discussion_notes = []
                dn_section = extract_section("Discussion Notes (from chat)")
                if dn_section:
                    for l in dn_section.splitlines():
                        l = l.strip()
                        if l.startswith('> **'):
                            # Speaker-attributed
                            m = re.match(r'> \*\*(.+?):\*\* (.+)', l)
                            if m:
                                discussion_notes.append({"speaker": m.group(1), "text": m.group(2)})
                        elif l.startswith('> '):
                            discussion_notes.append(l[2:])
                
                # Commit Metadata
                commit_metadata = {}
                cm_section = extract_section("Commit Metadata")
                if cm_section:
                    for l in cm_section.splitlines():
                        l = l.strip()
                        if l.startswith('- **') and ':** ' in l:
                            k, v = l[4:].split(':** ', 1)
                            commit_metadata[k.strip()] = v.strip()
                
                # Count parsed sections for metrics
                section_count = sum([
                    1 if summary else 0,
                    1 if technical_synopsis else 0,
                    1 if accomplishments else 0,
                    1 if frustrations else 0,
                    1 if tone_mood else 0,
                    1 if discussion_notes else 0,
                    1 if commit_metadata else 0
                ])
                
                if current_span:
                    current_span.set_attribute("journal.sections_parsed", section_count)
                
                # Record successful parsing metrics
                duration = time.time() - start_time
                metrics = get_mcp_metrics()
                if metrics:
                    metrics.record_operation_duration(
                        "journal.parse_duration_seconds",
                        duration,
                        operation_type="parse",
                        file_type="markdown"
                    )
                    metrics.record_tool_call(
                        "journal.parse_operations_total",
                        success=True,
                        operation_type="parse"
                    )
                
                return JournalEntry(
                    timestamp=timestamp,
                    commit_hash=commit_hash,
                    summary=summary,
                    technical_synopsis=technical_synopsis,
                    accomplishments=accomplishments,
                    frustrations=frustrations,
                    tone_mood=tone_mood,
                    discussion_notes=discussion_notes,
                    commit_metadata=commit_metadata,
                )
            
            # Failed to parse - invalid format
            if current_span:
                current_span.set_attribute("error.category", "invalid_format")
            
            duration = time.time() - start_time
            metrics = get_mcp_metrics()
            if metrics:
                metrics.record_tool_call(
                    "journal.parse_operations_total",
                    success=False,
                    operation_type="parse"
                )
            
            raise JournalParseError('Unrecognized journal entry format')
            
        except JournalParseError:
            # Re-raise parse errors as-is
            raise
        except Exception as e:
            # Record unexpected error metrics
            duration = time.time() - start_time
            metrics = get_mcp_metrics()
            if metrics:
                metrics.record_tool_call(
                    "journal.parse_operations_total",
                    success=False,
                    operation_type="parse"
                )
            
            if current_span:
                current_span.set_attribute("error.category", "parse_exception")
            
            raise JournalParseError(f'Parse error: {e}') 