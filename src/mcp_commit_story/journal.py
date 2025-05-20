import re
from typing import List, Optional, Dict, Union

class JournalParseError(Exception):
    pass

class JournalEntry:
    """
    Represents a single engineering journal entry, with Markdown serialization.
    Only non-empty sections are included in output.
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
        lines = [f"### {self.timestamp} — Commit {self.commit_hash}", ""]

        if self.summary:
            lines.append("## Summary")
            lines.append(self.summary)
            lines.append("")

        if self.accomplishments:
            lines.append("## Accomplishments")
            for item in self.accomplishments:
                lines.append(f"- {item}")
            lines.append("")

        if self.frustrations:
            lines.append("## Frustrations or Roadblocks")
            for item in self.frustrations:
                lines.append(f"- {item}")
            lines.append("")

        if self.terminal_commands:
            lines.append("## Terminal Commands (AI Session)")
            lines.append("Commands executed by AI during this work session:")
            lines.append("```bash")
            for cmd in self.terminal_commands:
                lines.append(cmd)
            lines.append("```")
            lines.append("")

        if self.discussion_notes:
            lines.append("## Discussion Notes (from chat)")
            for note in self.discussion_notes:
                if isinstance(note, dict) and 'speaker' in note and 'text' in note:
                    text_lines = note['text'].splitlines()
                    if text_lines:
                        lines.append(f"> **{note['speaker']}:** {text_lines[0]}")
                        for l in text_lines[1:]:
                            lines.append(f"> {l}")
                    else:
                        lines.append(f"> **{note['speaker']}:**")
                else:
                    text_lines = str(note).splitlines()
                    for l in text_lines:
                        lines.append(f"> {l}")
            lines.append("")

        if self.tone_mood and self.tone_mood.get("mood") and self.tone_mood.get("indicators"):
            lines.append("## Tone/Mood")
            lines.append(f"> {self.tone_mood['mood']}")
            lines.append(f"> {self.tone_mood['indicators']}")
            lines.append("")

        if self.behind_the_commit:
            lines.append("## Behind the Commit")
            for k, v in self.behind_the_commit.items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")

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
            # Reflections
            reflections = []
            m2 = re.search(r'## Reflections\n((?:- .+\n)+)', md)
            if m2:
                reflections = [line[2:].strip() for line in m2.group(1).splitlines() if line.startswith('- ')]
            return JournalEntry(
                timestamp=timestamp,
                commit_hash=commit_hash,
                accomplishments=accomplishments,
                frustrations=frustrations,
                summary=summary,
                reflections=reflections,
            )
        # Try to parse reflection entry
        m = re.search(r'###\s+(\d{1,2}:\d{2} [AP]M) — Reflection', md)
        if m:
            timestamp = m.group(1)
            # The rest is the reflection text
            text_match = re.search(r'— Reflection\n+(.+)', md, re.DOTALL)
            text = text_match.group(1).strip() if text_match else ''
            return JournalEntry(
                timestamp=timestamp,
                is_reflection=True,
                text=text,
            )
        raise JournalParseError('Unrecognized journal entry format')
