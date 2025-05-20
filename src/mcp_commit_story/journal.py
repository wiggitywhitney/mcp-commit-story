import re

class JournalParseError(Exception):
    pass

class JournalEntry:
    def __init__(self, **kwargs):
        self.timestamp = kwargs.get('timestamp')
        self.commit_hash = kwargs.get('commit_hash')
        self.accomplishments = kwargs.get('accomplishments', [])
        self.frustrations = kwargs.get('frustrations', [])
        self.summary = kwargs.get('summary', '')
        self.reflections = kwargs.get('reflections', [])
        self.is_reflection = kwargs.get('is_reflection', False)
        self.text = kwargs.get('text', '')

    @staticmethod
    def generate_summary(md):
        # Extract the summary text after the '## Summary' header
        if md.strip().startswith('## Summary'):
            lines = md.strip().splitlines()
            # Remove the header
            summary_lines = [line for line in lines if not line.strip().startswith('## Summary')]
            return '\n'.join(summary_lines).strip()
        return md.strip()

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
