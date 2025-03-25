"""Module providing a structure"""

from typing import List
from dataclasses import dataclass
from dataclasses import field


@dataclass
class Search:
    """Class representing a search"""

    url: str = ""
    content: str = ""


@dataclass
class Research:
    """Class representing a research"""
    search_history: List[Search] = field(default_factory=list)
    latest_summary: str = ""
    reflection_iteration: int = 0


@dataclass
class Paragraph:
    """Class representing a paragraph"""

    title: str = ""
    content: str = ""
    research: Research = field(default_factory=Research)


@dataclass
class State:
    """Class representing a state"""

    report_title: str = ""
    paragraphs: List[Paragraph] = field(default_factory=list)
