"""User preferences storage for FOSDEM assistant."""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

PREFERENCES_PATH = Path.home() / ".fosdem_preferences.json"


class UserPreferences(BaseModel):
    """User preferences and saved data."""
    interests: list[str] = Field(default_factory=list)
    bookmarked_talks: list[str] = Field(default_factory=list)  # Talk IDs

    def add_interest(self, interest: str) -> bool:
        """Add an interest topic. Returns True if added, False if already exists."""
        interest_lower = interest.lower()
        if interest_lower not in [i.lower() for i in self.interests]:
            self.interests.append(interest)
            return True
        return False

    def remove_interest(self, interest: str) -> bool:
        """Remove an interest topic. Returns True if removed, False if not found."""
        interest_lower = interest.lower()
        for i, existing in enumerate(self.interests):
            if existing.lower() == interest_lower:
                self.interests.pop(i)
                return True
        return False

    def add_bookmark(self, talk_id: str) -> bool:
        """Bookmark a talk. Returns True if added, False if already bookmarked."""
        if talk_id not in self.bookmarked_talks:
            self.bookmarked_talks.append(talk_id)
            return True
        return False

    def remove_bookmark(self, talk_id: str) -> bool:
        """Remove a bookmark. Returns True if removed, False if not found."""
        if talk_id in self.bookmarked_talks:
            self.bookmarked_talks.remove(talk_id)
            return True
        return False

    def is_bookmarked(self, talk_id: str) -> bool:
        """Check if a talk is bookmarked."""
        return talk_id in self.bookmarked_talks


class PreferencesManager:
    """Manager for loading and saving user preferences."""

    def __init__(self, path: Path = PREFERENCES_PATH):
        self.path = path
        self._preferences: Optional[UserPreferences] = None

    def load(self) -> UserPreferences:
        """Load preferences from disk."""
        if self._preferences is not None:
            return self._preferences

        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._preferences = UserPreferences(**data)
            except (json.JSONDecodeError, ValueError):
                self._preferences = UserPreferences()
        else:
            self._preferences = UserPreferences()

        return self._preferences

    def save(self) -> None:
        """Save preferences to disk."""
        if self._preferences is None:
            return
        self.path.write_text(self._preferences.model_dump_json(indent=2))

    @property
    def preferences(self) -> UserPreferences:
        """Get the current preferences, loading if necessary."""
        return self.load()

    def add_interest(self, interest: str) -> bool:
        """Add an interest and save."""
        result = self.preferences.add_interest(interest)
        if result:
            self.save()
        return result

    def remove_interest(self, interest: str) -> bool:
        """Remove an interest and save."""
        result = self.preferences.remove_interest(interest)
        if result:
            self.save()
        return result

    def add_bookmark(self, talk_id: str) -> bool:
        """Bookmark a talk and save."""
        result = self.preferences.add_bookmark(talk_id)
        if result:
            self.save()
        return result

    def remove_bookmark(self, talk_id: str) -> bool:
        """Remove a bookmark and save."""
        result = self.preferences.remove_bookmark(talk_id)
        if result:
            self.save()
        return result

    def get_interests(self) -> list[str]:
        """Get all interests."""
        return self.preferences.interests

    def get_bookmarks(self) -> list[str]:
        """Get all bookmarked talk IDs."""
        return self.preferences.bookmarked_talks
