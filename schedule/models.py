"""Data models for FOSDEM schedule."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Speaker(BaseModel):
    """A speaker at FOSDEM."""
    id: str
    name: str


class Link(BaseModel):
    """A link associated with a talk."""
    href: str
    title: Optional[str] = None


class Talk(BaseModel):
    """A talk/event at FOSDEM."""
    id: str
    title: str
    subtitle: Optional[str] = None
    abstract: Optional[str] = None
    description: Optional[str] = None
    track: str
    room: str
    day: str
    date: str
    start_time: str
    end_time: str
    duration: str
    speakers: list[Speaker] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)

    def matches_keyword(self, keyword: str) -> bool:
        """Check if this talk matches a keyword."""
        keyword = keyword.lower()
        searchable = [
            self.title,
            self.subtitle or "",
            self.abstract or "",
            self.description or "",
            self.track,
        ]
        searchable.extend(s.name for s in self.speakers)
        return any(keyword in text.lower() for text in searchable)


class Track(BaseModel):
    """A track at FOSDEM."""
    name: str
    room: str
    talks: list[Talk] = Field(default_factory=list)


class Day(BaseModel):
    """A day of FOSDEM."""
    index: int
    date: str
    name: str  # e.g., "Saturday" or "Sunday"


class Schedule(BaseModel):
    """The complete FOSDEM schedule."""
    conference: str = "FOSDEM 2026"
    days: list[Day] = Field(default_factory=list)
    talks: list[Talk] = Field(default_factory=list)
    tracks: dict[str, Track] = Field(default_factory=dict)

    def search(self, keyword: str) -> list[Talk]:
        """Search talks by keyword."""
        return [talk for talk in self.talks if talk.matches_keyword(keyword)]

    def get_talks_by_track(self, track_name: str) -> list[Talk]:
        """Get all talks in a specific track."""
        track_lower = track_name.lower()
        return [talk for talk in self.talks if track_lower in talk.track.lower()]

    def get_talks_by_day(self, day: str) -> list[Talk]:
        """Get all talks on a specific day (Saturday/Sunday or day number)."""
        day_lower = day.lower()
        return [
            talk for talk in self.talks
            if day_lower in talk.day.lower() or day_lower in talk.date.lower()
        ]

    def get_talks_by_speaker(self, speaker_name: str) -> list[Talk]:
        """Get all talks by a specific speaker."""
        speaker_lower = speaker_name.lower()
        return [
            talk for talk in self.talks
            if any(speaker_lower in s.name.lower() for s in talk.speakers)
        ]

    def get_talk_by_id(self, talk_id: str) -> Optional[Talk]:
        """Get a specific talk by its ID."""
        for talk in self.talks:
            if talk.id == talk_id:
                return talk
        return None

    def list_tracks(self) -> list[str]:
        """Get a list of all track names."""
        return sorted(set(talk.track for talk in self.talks))
