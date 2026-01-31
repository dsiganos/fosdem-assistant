"""Tool definitions for the FOSDEM Assistant agent."""

from typing import Any

from schedule.models import Schedule, Talk
from storage.preferences import PreferencesManager

# Tool definitions for Claude
TOOLS = [
    {
        "name": "search_talks",
        "description": "Search for talks by keyword, topic, or speaker name. Returns matching talks from the FOSDEM schedule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (keyword, topic, or speaker name)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_talk_details",
        "description": "Get full details of a specific talk by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "talk_id": {
                    "type": "string",
                    "description": "The ID of the talk to get details for"
                }
            },
            "required": ["talk_id"]
        }
    },
    {
        "name": "list_tracks",
        "description": "List all available tracks/devrooms at FOSDEM.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_schedule_for_day",
        "description": "Get all talks scheduled for a specific day.",
        "input_schema": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "string",
                    "description": "The day to get schedule for (e.g., 'Saturday', 'Sunday', or a date)"
                },
                "track": {
                    "type": "string",
                    "description": "Optional: Filter by track name"
                }
            },
            "required": ["day"]
        }
    },
    {
        "name": "add_interest",
        "description": "Add a topic or keyword to the user's interests for personalized recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "interest": {
                    "type": "string",
                    "description": "The topic or keyword to add to interests"
                }
            },
            "required": ["interest"]
        }
    },
    {
        "name": "remove_interest",
        "description": "Remove a topic or keyword from the user's interests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "interest": {
                    "type": "string",
                    "description": "The topic or keyword to remove"
                }
            },
            "required": ["interest"]
        }
    },
    {
        "name": "get_interests",
        "description": "Get the list of user's current interests.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_recommendations",
        "description": "Get talk recommendations based on the user's stored interests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recommendations (default: 5)",
                    "default": 5
                }
            }
        }
    },
    {
        "name": "bookmark_talk",
        "description": "Save a talk to the user's personal schedule/bookmarks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "talk_id": {
                    "type": "string",
                    "description": "The ID of the talk to bookmark"
                }
            },
            "required": ["talk_id"]
        }
    },
    {
        "name": "remove_bookmark",
        "description": "Remove a talk from the user's bookmarks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "talk_id": {
                    "type": "string",
                    "description": "The ID of the talk to remove from bookmarks"
                }
            },
            "required": ["talk_id"]
        }
    },
    {
        "name": "get_bookmarks",
        "description": "Get all talks the user has bookmarked.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


def format_talk(talk: Talk, include_abstract: bool = False) -> dict[str, Any]:
    """Format a talk for display."""
    result = {
        "id": talk.id,
        "title": talk.title,
        "track": talk.track,
        "room": talk.room,
        "day": talk.day,
        "time": f"{talk.start_time} ({talk.duration})",
        "speakers": [s.name for s in talk.speakers]
    }
    if include_abstract and talk.abstract:
        result["abstract"] = talk.abstract
    if talk.subtitle:
        result["subtitle"] = talk.subtitle
    return result


class ToolExecutor:
    """Executes tools for the FOSDEM assistant."""

    def __init__(self, schedule: Schedule, preferences: PreferencesManager):
        self.schedule = schedule
        self.preferences = preferences

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool and return the result as a string."""
        method = getattr(self, f"_tool_{tool_name}", None)
        if method is None:
            return f"Unknown tool: {tool_name}"
        try:
            result = method(**tool_input)
            return result
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _tool_search_talks(self, query: str, limit: int = 10) -> str:
        """Search for talks by keyword."""
        talks = self.schedule.search(query)[:limit]
        if not talks:
            return f"No talks found matching '{query}'."

        results = [format_talk(t) for t in talks]
        return f"Found {len(talks)} talk(s) matching '{query}':\n" + \
               "\n".join(f"- {t['title']} (ID: {t['id']}) - {t['track']}, {t['day']} {t['time']}"
                        for t in results)

    def _tool_get_talk_details(self, talk_id: str) -> str:
        """Get details of a specific talk."""
        talk = self.schedule.get_talk_by_id(talk_id)
        if not talk:
            return f"Talk with ID '{talk_id}' not found."

        details = format_talk(talk, include_abstract=True)
        is_bookmarked = self.preferences.preferences.is_bookmarked(talk_id)

        lines = [
            f"**{details['title']}**",
            f"Track: {details['track']}",
            f"Room: {details['room']}",
            f"When: {details['day']} at {details['time']}",
        ]
        if details.get('subtitle'):
            lines.insert(1, f"*{details['subtitle']}*")
        if details['speakers']:
            lines.append(f"Speakers: {', '.join(details['speakers'])}")
        if details.get('abstract'):
            lines.append(f"\nAbstract: {details['abstract']}")
        if talk.links:
            lines.append(f"\nLinks: {', '.join(l.href for l in talk.links)}")
        lines.append(f"\nBookmarked: {'Yes' if is_bookmarked else 'No'}")

        return "\n".join(lines)

    def _tool_list_tracks(self) -> str:
        """List all tracks."""
        tracks = self.schedule.list_tracks()
        if not tracks:
            return "No tracks found in the schedule."
        return f"FOSDEM 2026 Tracks ({len(tracks)} total):\n" + "\n".join(f"- {t}" for t in tracks)

    def _tool_get_schedule_for_day(self, day: str, track: str = None) -> str:
        """Get schedule for a specific day."""
        talks = self.schedule.get_talks_by_day(day)
        if track:
            talks = [t for t in talks if track.lower() in t.track.lower()]

        if not talks:
            msg = f"No talks found for {day}"
            if track:
                msg += f" in track '{track}'"
            return msg + "."

        # Sort by start time
        talks.sort(key=lambda t: t.start_time)

        results = [format_talk(t) for t in talks[:20]]  # Limit to 20
        header = f"Schedule for {day}"
        if track:
            header += f" ({track})"
        header += f" - {len(talks)} talks"
        if len(talks) > 20:
            header += " (showing first 20)"

        return header + ":\n" + "\n".join(
            f"- {t['time']}: {t['title']} ({t['track']}, ID: {t['id']})"
            for t in results
        )

    def _tool_add_interest(self, interest: str) -> str:
        """Add an interest."""
        if self.preferences.add_interest(interest):
            return f"Added '{interest}' to your interests."
        return f"'{interest}' is already in your interests."

    def _tool_remove_interest(self, interest: str) -> str:
        """Remove an interest."""
        if self.preferences.remove_interest(interest):
            return f"Removed '{interest}' from your interests."
        return f"'{interest}' was not in your interests."

    def _tool_get_interests(self) -> str:
        """Get user's interests."""
        interests = self.preferences.get_interests()
        if not interests:
            return "You haven't added any interests yet. Tell me what topics you're interested in!"
        return f"Your interests: {', '.join(interests)}"

    def _tool_get_recommendations(self, limit: int = 5) -> str:
        """Get recommendations based on interests."""
        interests = self.preferences.get_interests()
        if not interests:
            return "You haven't added any interests yet. Tell me what topics you're interested in, and I'll recommend talks!"

        # Score talks based on how many interests they match
        talk_scores: dict[str, tuple[Talk, int]] = {}
        for interest in interests:
            for talk in self.schedule.search(interest):
                if talk.id in talk_scores:
                    talk_scores[talk.id] = (talk, talk_scores[talk.id][1] + 1)
                else:
                    talk_scores[talk.id] = (talk, 1)

        if not talk_scores:
            return f"No talks found matching your interests: {', '.join(interests)}"

        # Sort by score (descending)
        sorted_talks = sorted(talk_scores.values(), key=lambda x: x[1], reverse=True)[:limit]

        lines = [f"Top {len(sorted_talks)} recommendations based on your interests ({', '.join(interests)}):"]
        for i, (talk, score) in enumerate(sorted_talks, 1):
            bookmark = " [BOOKMARKED]" if self.preferences.preferences.is_bookmarked(talk.id) else ""
            lines.append(
                f"{i}. {talk.title}{bookmark}\n"
                f"   Track: {talk.track} | {talk.day} {talk.start_time}\n"
                f"   ID: {talk.id} | Matches {score} interest(s)"
            )

        return "\n".join(lines)

    def _tool_bookmark_talk(self, talk_id: str) -> str:
        """Bookmark a talk."""
        talk = self.schedule.get_talk_by_id(talk_id)
        if not talk:
            return f"Talk with ID '{talk_id}' not found."

        if self.preferences.add_bookmark(talk_id):
            return f"Bookmarked: {talk.title} ({talk.day} {talk.start_time})"
        return f"'{talk.title}' is already bookmarked."

    def _tool_remove_bookmark(self, talk_id: str) -> str:
        """Remove a bookmark."""
        talk = self.schedule.get_talk_by_id(talk_id)
        if self.preferences.remove_bookmark(talk_id):
            title = talk.title if talk else talk_id
            return f"Removed '{title}' from bookmarks."
        return f"Talk '{talk_id}' was not bookmarked."

    def _tool_get_bookmarks(self) -> str:
        """Get all bookmarked talks."""
        bookmark_ids = self.preferences.get_bookmarks()
        if not bookmark_ids:
            return "You haven't bookmarked any talks yet."

        lines = [f"Your bookmarked talks ({len(bookmark_ids)}):"]
        for talk_id in bookmark_ids:
            talk = self.schedule.get_talk_by_id(talk_id)
            if talk:
                lines.append(f"- {talk.title}\n  {talk.track} | {talk.day} {talk.start_time} | ID: {talk.id}")
            else:
                lines.append(f"- [Talk not found: {talk_id}]")

        return "\n".join(lines)
