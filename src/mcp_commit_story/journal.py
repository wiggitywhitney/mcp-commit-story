import re
from typing import List, Optional, Dict, Union
from pathlib import Path
import os

"""
Journal entry generation for engineering work.

Content Quality Guidelines:
- Focus on signal (unique insights, decisions, challenges) over noise (routine procedures)
- Highlight what makes each entry unique rather than repeating standard practices
- Capture the narrative "story" behind the code changes
- Include emotional context when relevant, but only with clear supporting evidence
- Omit standard workflow details unless they're directly relevant to understanding the work
"""

class JournalParseError(Exception):
    pass

class JournalEntry:
    """
    Represents a single engineering journal entry, with Markdown serialization.
    Only non-empty sections are included in output.

    Content should prioritize unique insights and developments over routine
    workflow steps. The goal is to create entries that provide value when
    reviewed in the future, focusing on "why" and "how" rather than just "what".
    """

    def __init__(
        self,
        timestamp: str,
        commit_hash: str,
        summary: Optional[str] = None,
        accomplishments: Optional[List[str]] = None,
        frustrations: Optional[List[str]] = None,
        terminal_commands: Optional[List[str]] = None,
        discussion_notes: Optional[List[Union[str, Dict[str, str]]]] = None,
        tone_mood: Optional[Dict[str, str]] = None,  # {'mood': str, 'indicators': str}
        behind_the_commit: Optional[Dict[str, str]] = None,
    ):
        self.timestamp = timestamp
        self.commit_hash = commit_hash
        self.summary = summary
        self.accomplishments = accomplishments or []
        self.frustrations = frustrations or []
        self.terminal_commands = terminal_commands or []
        self.discussion_notes = discussion_notes or []
        self.tone_mood = tone_mood
        self.behind_the_commit = behind_the_commit or {}

    def to_markdown(self) -> str:
        """
        Serialize the journal entry to Markdown with improved formatting:
        - H3 for entry header
        - H4 for section headers
        - Blank line after section headers
        - Blank line between bullet points
        - Blank line on speaker change in discussion notes
        - Terminal commands as a single bash code block
        - Blockquotes visually distinct
        - (Horizontal rule between entries is handled externally)
        """
        lines = [f"### {self.timestamp} — Commit {self.commit_hash}", ""]

        def section(header, content_lines):
            if not content_lines:
                return []
            out = [f"#### {header}", ""]
            out.extend(content_lines)
            out.append("")
            return out

        if self.summary:
            lines += section("Summary", [self.summary])

        if self.accomplishments:
            acc_lines = []
            for i, item in enumerate(self.accomplishments):
                acc_lines.append(f"- {item}")
                if i < len(self.accomplishments) - 1:
                    acc_lines.append("")  # blank line between bullets
            lines += section("Accomplishments", acc_lines)

        if self.frustrations:
            frus_lines = []
            for i, item in enumerate(self.frustrations):
                frus_lines.append(f"- {item}")
                if i < len(self.frustrations) - 1:
                    frus_lines.append("")
            lines += section("Frustrations or Roadblocks", frus_lines)

        if self.terminal_commands:
            tc_lines = ["Commands executed by AI during this work session:", "```bash"]
            tc_lines.extend(self.terminal_commands)
            tc_lines.append("```")
            lines += section("Terminal Commands (AI Session)", tc_lines)

        if self.discussion_notes:
            dn_lines = []
            prev_speaker = None
            for note in self.discussion_notes:
                if isinstance(note, dict) and 'speaker' in note and 'text' in note:
                    speaker = note['speaker']
                    text_lines = note['text'].splitlines()
                    if prev_speaker is not None and speaker != prev_speaker:
                        dn_lines.append("")  # blank line on speaker change
                    if text_lines:
                        dn_lines.append(f"> **{speaker}:** {text_lines[0]}")
                        for l in text_lines[1:]:
                            dn_lines.append(f"> {l}")
                    else:
                        dn_lines.append(f"> **{speaker}:**")
                    prev_speaker = speaker
                else:
                    text_lines = str(note).splitlines()
                    for l in text_lines:
                        dn_lines.append(f"> {l}")
            lines += section("Discussion Notes (from chat)", dn_lines)

        if self.tone_mood and self.tone_mood.get("mood") and self.tone_mood.get("indicators"):
            tm_lines = [f"> {self.tone_mood['mood']}", f"> {self.tone_mood['indicators']}"]
            lines += section("Tone/Mood", tm_lines)

        if self.behind_the_commit:
            btc_lines = [f"- **{k}:** {v}" for k, v in self.behind_the_commit.items()]
            lines += section("Behind the Commit", btc_lines)

        # Remove trailing blank lines
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines).strip()

class JournalParser:
    @staticmethod
    def parse(md):
        if not md or not md.strip():
            raise JournalParseError('Empty entry')
        # Try to parse daily note entry
        m = re.search(r'###\s+(\d{1,2}:\d{2} [AP]M) — Commit ([a-zA-Z0-9]+)', md)
        if m:
            timestamp = m.group(1)
            commit_hash = m.group(2)
            # Summary
            summary = ''
            m2 = re.search(r'## Summary\n(.+?)(\n##|$)', md, re.DOTALL)
            if m2:
                summary = m2.group(1).strip()
            # Accomplishments
            accomplishments = []
            m2 = re.search(r'## Accomplishments\n((?:- .+\n)+)', md)
            if m2:
                accomplishments = [line[2:].strip() for line in m2.group(1).splitlines() if line.startswith('- ')]
            # Frustrations
            frustrations = []
            m2 = re.search(r'## Frustrations or Roadblocks\n((?:- .+\n)+)', md)
            if m2:
                frustrations = [line[2:].strip() for line in m2.group(1).splitlines() if line.startswith('- ')]
            return JournalEntry(
                timestamp=timestamp,
                commit_hash=commit_hash,
                accomplishments=accomplishments,
                frustrations=frustrations,
                summary=summary,
            )
        # Reflection entries are not supported in the canonical JournalEntry structure
        raise JournalParseError('Unrecognized journal entry format')

def get_journal_file_path(date, entry_type):
    """
    Return the correct journal file path based on date and entry type.
    entry_type: 'daily', 'daily_summary', 'weekly_summary', 'monthly_summary', 'yearly_summary'
    """
    if entry_type == "daily":
        return Path("journal/daily") / f"{date}-journal.md"
    elif entry_type == "daily_summary":
        return Path("journal/summaries/daily") / f"{date}-daily.md"
    elif entry_type == "weekly_summary":
        return Path("journal/summaries/weekly") / f"{date}-weekly.md"
    elif entry_type == "monthly_summary":
        return Path("journal/summaries/monthly") / f"{date}-monthly.md"
    elif entry_type == "yearly_summary":
        return Path("journal/summaries/yearly") / f"{date}-yearly.md"
    else:
        raise ValueError(f"Unknown entry_type: {entry_type}")

def create_journal_directories(base_dir):
    """
    Create all required journal subdirectories under base_dir.
    """
    (Path(base_dir) / "daily").mkdir(parents=True, exist_ok=True)
    (Path(base_dir) / "summaries" / "daily").mkdir(parents=True, exist_ok=True)
    (Path(base_dir) / "summaries" / "weekly").mkdir(parents=True, exist_ok=True)
    (Path(base_dir) / "summaries" / "monthly").mkdir(parents=True, exist_ok=True)
    (Path(base_dir) / "summaries" / "yearly").mkdir(parents=True, exist_ok=True)

def append_to_journal_file(entry, file_path):
    """
    Append a journal entry to the file at file_path. If the file does not exist, create it.
    If the file exists and is not empty, prepend a horizontal rule (---) before the new entry.
    Automatically create parent directories as needed.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if file_path.exists() and file_path.stat().st_size > 0:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write("\n---\n" + entry)
        else:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(entry)
    except Exception as e:
        raise

def collect_chat_history(since_commit=None, max_messages_back=150):
    """
    Collect relevant chat history for journal entry.

    AI Prompt:
    Please analyze our ENTIRE chat history within the specified boundary and extract ALL relevant discussion points for the journal entry.
    - Search backward through the current conversation for the last time you invoked the mcp-commit-story new-entry command (or a similar journal generation function).
    - If no such reference is found, review all available conversation history within your context window.
    IMPORTANT: Review ALL chat messages and terminal commands within this boundary, not just the most recent ones.
    Be thorough and comprehensive in your review—do not skip or summarize large portions of the conversation.
    Focus on:
      1. Technical decisions and reasoning
      2. Problem-solving approaches and solutions
      3. Challenges encountered and how they were addressed
      4. Expressions of frustration, satisfaction, or other emotions
      5. Key questions and answers that shaped the work
    Do NOT include:
      - Passwords, API keys, authentication tokens
      - Personal identifiable information (PII)
      - Other sensitive data
      - Routine procedural discussions that don't provide insight
      - Ambiguous notes that don't add clear value
    If in doubt about whether to include a note, err on the side of exclusion unless it clearly adds value to the engineering narrative.
    Format each discussion note as a dictionary with 'speaker' and 'text' fields when the speaker is identifiable, or just 'text' for unattributed notes.
    These entries may be used to generate developer-facing summaries or historical narratives. Please ensure clarity and accuracy.
    The goal is to capture the complete narrative and decision-making process, reviewing ALL available information within the boundary.
    
    ANTI-HALLUCINATION RULES:
    - Do NOT invent, infer, or summarize information that is not explicitly present in the actual conversation history.
    - Only include discussion points that are directly supported by the chat transcript.
    - If a detail is not present, do NOT speculate or fill in gaps.

    Checklist:
    - [ ] Search backward through the current conversation for the last invocation of the mcp-commit-story new-entry command (or similar journal generation function)
    - [ ] If no such reference is found, review all available conversation history within your context window
    - [ ] Review ALL chat messages and terminal commands within this boundary, not just the most recent ones
    - [ ] Be thorough and comprehensive—do not skip or summarize large portions of the conversation
    - [ ] Focus on extracting:
        - Technical decisions and reasoning
        - Problem-solving approaches and solutions
        - Challenges encountered and how they were addressed
        - Expressions of frustration, satisfaction, or other emotions
        - Key questions and answers that shaped the work
    - [ ] Exclude:
        - Passwords, API keys, authentication tokens
        - Personal identifiable information (PII)
        - Other sensitive data
        - Routine procedural discussions that don't provide insight
        - Ambiguous notes that don't add clear value
    - [ ] If in doubt about whether to include a note, err on the side of exclusion unless it clearly adds value to the engineering narrative
    - [ ] Format each discussion note as a dictionary with 'speaker' and 'text' fields when the speaker is identifiable, or just 'text' for unattributed notes
    - [ ] Ensure clarity and accuracy, as these entries may be used for developer-facing summaries or historical narratives
    - [ ] ANTI-HALLUCINATION: Do NOT invent, infer, or summarize information that is not explicitly present in the actual conversation history
    - [ ] ANTI-HALLUCINATION: Only include discussion points directly supported by the chat transcript
    - [ ] ANTI-HALLUCINATION: If a detail is not present, do NOT speculate or fill in gaps

    ---
    ADDITIONAL INSTRUCTIONS (MESSAGE-BASED BOUNDARY):
    - This function scans backward through the conversation for the last commit reference (e.g., last journal entry or new-entry command).
    - If no such reference is found, scan up to `max_messages_back` messages.
    - No time-based boundaries are used.
    - Do not use timestamps or time-based calculations for chat history collection.
    - All time boundaries in this function are deprecated in favor of message count.
    """
    return []

def collect_ai_terminal_commands(since_commit=None, max_messages_back=150):
    """
    Collect terminal commands executed by AI during the current work session.

    AI Prompt:
    Please analyze our ENTIRE terminal command history within the specified boundary and extract ALL relevant commands executed by the AI for the journal entry.
    - Search backward through the current conversation for the last time you invoked the mcp-commit-story new-entry command (or a similar journal generation function).
    - If no such reference is found, review all available terminal command history within your context window.
    IMPORTANT: Review ALL terminal commands within this boundary, not just the most recent ones.
    Be thorough and comprehensive in your review—do not skip or summarize large portions of the command history.
    Focus on including:
      - Commands that demonstrate problem-solving steps
      - Commands that show the technical approach
      - Failed commands that highlight challenges or errors
      - Repetitive commands that might indicate frustrations or iteration
    Exclude:
      - Routine git commands (add, status, commit) unless they are significant to the narrative
      - Commands run specifically as part of journal entry creation
      - Commands containing passwords, API keys, tokens, or other sensitive information
      - Commands that reveal personal identifiable information (PII)
    If in doubt about whether to include a command, err on the side of exclusion unless it clearly adds value to the engineering narrative.
    Format the output as a chronological list of terminal commands, suitable for inclusion in a developer-facing journal entry.
    These entries may be used to generate developer-facing summaries or historical narratives. Please ensure clarity and accuracy.
    The goal is to document the complete technical steps taken during the work session, reviewing ALL available information within the boundary.

    ANTI-HALLUCINATION RULES:
    - Do NOT invent, infer, or summarize commands that are not explicitly present in the actual terminal history.
    - Only include commands that are directly supported by the terminal transcript.
    - If a command is not present, do NOT speculate or fill in gaps.

    Checklist:
    - [ ] Search backward through the current conversation for the last invocation of the mcp-commit-story new-entry command (or similar journal generation function)
    - [ ] If no such reference is found, review all available terminal command history within your context window
    - [ ] Review ALL terminal commands within this boundary, not just the most recent ones
    - [ ] Be thorough and comprehensive—do not skip or summarize large portions of the command history
    - [ ] Focus on including:
        - Commands that demonstrate problem-solving steps
        - Commands that show the technical approach
        - Failed commands that highlight challenges or errors
        - Repetitive commands that might indicate frustrations or iteration
    - [ ] Exclude:
        - Routine git commands (add, status, commit) unless significant to the narrative
        - Commands run specifically as part of journal entry creation
        - Commands containing passwords, API keys, tokens, or other sensitive information
        - Commands that reveal personal identifiable information (PII)
    - [ ] If in doubt about whether to include a command, err on the side of exclusion unless it clearly adds value to the engineering narrative
    - [ ] Format the output as a chronological list of terminal commands, suitable for a developer-facing journal entry
    - [ ] Ensure clarity and accuracy, as these entries may be used for developer-facing summaries or historical narratives
    - [ ] ANTI-HALLUCINATION: Do NOT invent, infer, or summarize commands that are not explicitly present in the actual terminal history
    - [ ] ANTI-HALLUCINATION: Only include commands directly supported by the terminal transcript
    - [ ] ANTI-HALLUCINATION: If a command is not present, do NOT speculate or fill in gaps

    ---
    ADDITIONAL INSTRUCTIONS (MESSAGE-BASED BOUNDARY):
    - This function scans backward through the conversation for the last commit reference (e.g., last journal entry or new-entry command).
    - If no such reference is found, scan up to `max_messages_back` messages.
    - No time-based boundaries are used.
    - Do not use timestamps or time-based calculations for terminal command collection.
    - All time boundaries in this function are deprecated in favor of message count.
    """
    return []
