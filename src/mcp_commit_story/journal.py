import re
from typing import List, Optional, Dict, Union

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
