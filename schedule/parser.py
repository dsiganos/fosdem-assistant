"""Pentabarf XML parser for FOSDEM schedule."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from .models import Day, Link, Schedule, Speaker, Talk, Track

SCHEDULE_URL = "https://fosdem.org/2026/schedule/xml"
CACHE_PATH = Path(__file__).parent.parent / "data" / "schedule.xml"


def fetch_schedule(url: str = SCHEDULE_URL, cache_path: Path = CACHE_PATH) -> str:
    """Fetch the schedule XML, using cache if available."""
    if cache_path.exists():
        return cache_path.read_text()

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text)

    return response.text


def refresh_schedule(url: str = SCHEDULE_URL, cache_path: Path = CACHE_PATH) -> str:
    """Force refresh the schedule from the server."""
    if cache_path.exists():
        cache_path.unlink()
    return fetch_schedule(url, cache_path)


def get_text(element: Optional[ET.Element], tag: str, default: str = "") -> str:
    """Safely get text from a child element."""
    if element is None:
        return default
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def parse_schedule(xml_content: str) -> Schedule:
    """Parse Pentabarf XML into Schedule model."""
    root = ET.fromstring(xml_content)
    schedule = Schedule()

    # Parse conference info
    conference = root.find("conference")
    if conference is not None:
        title = get_text(conference, "title")
        if title:
            schedule.conference = title

    # Parse days and events
    for day_elem in root.findall(".//day"):
        day_index = day_elem.get("index", "0")
        day_date = day_elem.get("date", "")

        # Determine day name from index
        day_name = "Saturday" if day_index == "1" else "Sunday" if day_index == "2" else f"Day {day_index}"

        day = Day(index=int(day_index), date=day_date, name=day_name)
        schedule.days.append(day)

        # Parse rooms and events within each day
        for room_elem in day_elem.findall("room"):
            room_name = room_elem.get("name", "Unknown Room")

            for event_elem in room_elem.findall("event"):
                talk = parse_event(event_elem, room_name, day_name, day_date)
                schedule.talks.append(talk)

                # Add to track
                if talk.track not in schedule.tracks:
                    schedule.tracks[talk.track] = Track(name=talk.track, room=room_name)
                schedule.tracks[talk.track].talks.append(talk)

    return schedule


def parse_event(event_elem: ET.Element, room: str, day: str, date: str) -> Talk:
    """Parse a single event element into a Talk."""
    event_id = event_elem.get("id", "")

    # Parse speakers
    speakers = []
    persons_elem = event_elem.find("persons")
    if persons_elem is not None:
        for person in persons_elem.findall("person"):
            person_id = person.get("id", "")
            person_name = person.text.strip() if person.text else ""
            if person_name:
                speakers.append(Speaker(id=person_id, name=person_name))

    # Parse links
    links = []
    links_elem = event_elem.find("links")
    if links_elem is not None:
        for link in links_elem.findall("link"):
            href = link.get("href", "")
            title = link.text.strip() if link.text else None
            if href:
                links.append(Link(href=href, title=title))

    return Talk(
        id=event_id,
        title=get_text(event_elem, "title"),
        subtitle=get_text(event_elem, "subtitle") or None,
        abstract=get_text(event_elem, "abstract") or None,
        description=get_text(event_elem, "description") or None,
        track=get_text(event_elem, "track", "Unknown Track"),
        room=room,
        day=day,
        date=date,
        start_time=get_text(event_elem, "start"),
        end_time=get_text(event_elem, "start"),  # Will be calculated from duration
        duration=get_text(event_elem, "duration"),
        speakers=speakers,
        links=links,
    )


def load_schedule(force_refresh: bool = False) -> Schedule:
    """Load and parse the FOSDEM schedule."""
    if force_refresh:
        xml_content = refresh_schedule()
    else:
        xml_content = fetch_schedule()
    return parse_schedule(xml_content)
