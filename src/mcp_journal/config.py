from typing import Dict, List, Optional, Any

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

class Config:
    """
    Configuration class for MCP Journal system.
    Holds all config options with sensible defaults and type validation.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        defaults = self.get_default_config()
        config = config or {}
        self._journal_path = config.get('journal_path', defaults['journal_path'])
        self._auto_generate = config.get('auto_generate', defaults['auto_generate'])
        included_sections = config.get('included_sections', defaults['included_sections'])
        if not isinstance(included_sections, list):
            included_sections = defaults['included_sections']
        self._included_sections = included_sections
        section_order = config.get('section_order', defaults['section_order'])
        if not isinstance(section_order, dict):
            section_order = defaults['section_order']
        self._section_order = section_order
        self._date_format = config.get('date_format', defaults['date_format'])
        self._file_extension = config.get('file_extension', defaults['file_extension'])

    @property
    def journal_path(self) -> str:
        return self._journal_path
    @journal_path.setter
    def journal_path(self, value: str):
        if not isinstance(value, str):
            raise ConfigError('journal_path must be a string')
        self._journal_path = value

    @property
    def auto_generate(self) -> bool:
        return self._auto_generate
    @auto_generate.setter
    def auto_generate(self, value: bool):
        if not isinstance(value, bool):
            raise ConfigError('auto_generate must be a boolean')
        self._auto_generate = value

    @property
    def included_sections(self) -> List[str]:
        return self._included_sections
    @included_sections.setter
    def included_sections(self, value: List[str]):
        if not isinstance(value, list):
            raise ConfigError('included_sections must be a list of strings')
        self._included_sections = value

    @property
    def section_order(self) -> Dict[str, int]:
        return self._section_order
    @section_order.setter
    def section_order(self, value: Dict[str, int]):
        if not isinstance(value, dict):
            raise ConfigError('section_order must be a dict')
        self._section_order = value

    @property
    def date_format(self) -> str:
        return self._date_format
    @date_format.setter
    def date_format(self, value: str):
        if not isinstance(value, str):
            raise ConfigError('date_format must be a string')
        self._date_format = value

    @property
    def file_extension(self) -> str:
        return self._file_extension
    @file_extension.setter
    def file_extension(self, value: str):
        if not isinstance(value, str):
            raise ConfigError('file_extension must be a string')
        self._file_extension = value

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            'journal_path': '~/journal',
            'auto_generate': True,
            'included_sections': ["Summary", "Tasks", "Notes", "Ideas"],
            'section_order': {"Summary": 1, "Tasks": 2, "Notes": 3, "Ideas": 4},
            'date_format': "%Y-%m-%d",
            'file_extension': ".md",
        }

    def as_dict(self) -> Dict[str, Any]:
        return {
            'journal_path': self.journal_path,
            'auto_generate': self.auto_generate,
            'included_sections': self.included_sections,
            'section_order': self.section_order,
            'date_format': self.date_format,
            'file_extension': self.file_extension,
        }

    def is_valid(self) -> bool:
        try:
            assert isinstance(self.journal_path, str)
            assert isinstance(self.auto_generate, bool)
            assert isinstance(self.included_sections, list)
            assert isinstance(self.section_order, dict)
            assert isinstance(self.date_format, str)
            assert isinstance(self.file_extension, str)
            return True
        except AssertionError:
            return False

    def reset_to_defaults(self):
        defaults = self.get_default_config()
        self.journal_path = defaults['journal_path']
        self.auto_generate = defaults['auto_generate']
        self.included_sections = defaults['included_sections']
        self.section_order = defaults['section_order']
        self.date_format = defaults['date_format']
        self.file_extension = defaults['file_extension']
