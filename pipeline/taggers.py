"""Taggers: things that look at an image and suggest tags for it.

They all share one method, suggest(), so tag.py doesn't care which one
it's using. Fake for testing now, Claude next, local Qwen later.
"""
from abc import ABC, abstractmethod   # ABC = "this class is a template, not a real thing"
from pathlib import Path


class Tagger(ABC):
    """The template every tagger has to follow."""

    name = "base"   # each tagger gets a short name, saved next to its tags in tags.json

    @abstractmethod   # "every subclass MUST write its own suggest()", or Python won't even create it
    def suggest(self, image: Path, vocabulary: list[str]) -> list[str]:
        """Look at one image and return tags, picked from the vocabulary."""
        ...   # no real code here on purpose: the subclasses fill this in


class FakeTagger(Tagger):
    """Pretend tagger for testing: free, instant, and always says the same thing."""

    name = "fake"

    def suggest(self, image: Path, vocabulary: list[str]) -> list[str]:
        # Ignores the image completely. The list is messy on purpose
        # (capital letter, extra spaces, a tag that doesn't exist, a repeat)
        # because real AI output gets messy too, and tag.py's clean() has to handle it.
        return ["Portrait", "  painterly ", "spaceship", "portrait"]