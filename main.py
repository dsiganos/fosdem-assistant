#!/usr/bin/env python3
"""FOSDEM Assistant - CLI chat interface."""

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from agent.assistant import FosdemAssistant
from schedule.parser import load_schedule
from storage.preferences import PreferencesManager


def print_welcome(console: Console, talk_count: int, track_count: int) -> None:
    """Print welcome message."""
    welcome = f"""# FOSDEM 2026 Assistant

Welcome! I'm your AI assistant for exploring FOSDEM 2026.

**Schedule loaded:** {talk_count} talks across {track_count} tracks

**What I can help with:**
- Search for talks by topic, speaker, or keyword
- Get personalized recommendations based on your interests
- Build your personal schedule with bookmarks
- Explore different tracks and devrooms

**Commands:**
- `/interests` - Show your saved interests
- `/bookmarks` - Show your bookmarked talks
- `/refresh` - Refresh the schedule from FOSDEM
- `/clear` - Clear conversation history
- `/quit` - Exit the assistant

**Just start chatting!** Tell me what topics interest you, and I'll help you find great talks.
"""
    console.print(Panel(Markdown(welcome), title="FOSDEM Assistant", border_style="blue"))


def handle_command(
    command: str,
    assistant: FosdemAssistant,
    preferences: PreferencesManager,
    console: Console
) -> bool:
    """Handle special commands. Returns True if should continue, False to quit."""
    cmd = command.lower().strip()

    if cmd == "/quit" or cmd == "/exit" or cmd == "/q":
        console.print("[yellow]Goodbye! Enjoy FOSDEM 2026![/yellow]")
        return False

    elif cmd == "/interests":
        interests = preferences.get_interests()
        if interests:
            console.print(Panel(
                "\n".join(f"- {i}" for i in interests),
                title="Your Interests",
                border_style="green"
            ))
        else:
            console.print("[dim]No interests saved yet. Tell me what topics you like![/dim]")

    elif cmd == "/bookmarks":
        bookmarks = preferences.get_bookmarks()
        if bookmarks:
            lines = []
            for talk_id in bookmarks:
                talk = assistant.schedule.get_talk_by_id(talk_id)
                if talk:
                    lines.append(f"- **{talk.title}**\n  {talk.track} | {talk.day} {talk.start_time}")
                else:
                    lines.append(f"- [Unknown talk: {talk_id}]")
            console.print(Panel(
                Markdown("\n".join(lines)),
                title="Your Bookmarked Talks",
                border_style="green"
            ))
        else:
            console.print("[dim]No bookmarks yet. Ask me about talks to bookmark![/dim]")

    elif cmd == "/refresh":
        console.print("[yellow]Refreshing schedule...[/yellow]")
        try:
            from schedule.parser import load_schedule
            assistant.schedule = load_schedule(force_refresh=True)
            assistant.tool_executor.schedule = assistant.schedule
            console.print(f"[green]Schedule refreshed! {len(assistant.schedule.talks)} talks loaded.[/green]")
        except Exception as e:
            console.print(f"[red]Error refreshing schedule: {e}[/red]")

    elif cmd == "/clear":
        assistant.reset_conversation()
        console.print("[dim]Conversation cleared.[/dim]")

    elif cmd == "/help":
        console.print(Panel(Markdown("""
**Commands:**
- `/interests` - Show your saved interests
- `/bookmarks` - Show your bookmarked talks
- `/refresh` - Refresh the schedule from FOSDEM
- `/clear` - Clear conversation history
- `/quit` - Exit the assistant
"""), title="Help", border_style="blue"))

    else:
        console.print(f"[red]Unknown command: {command}[/red]")

    return True


def main() -> None:
    """Main entry point."""
    console = Console()

    # Check for API key
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set.[/red]")
        console.print("Please set your Anthropic API key:")
        console.print("  export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    # Load schedule
    console.print("[dim]Loading FOSDEM 2026 schedule...[/dim]")
    try:
        schedule = load_schedule()
        console.print(f"[green]Loaded {len(schedule.talks)} talks![/green]")
    except Exception as e:
        console.print(f"[red]Error loading schedule: {e}[/red]")
        console.print("[yellow]Starting with empty schedule. Use /refresh to try again.[/yellow]")
        from schedule.models import Schedule
        schedule = Schedule()

    # Initialize components
    preferences = PreferencesManager()
    assistant = FosdemAssistant(schedule, preferences)

    # Print welcome
    print_welcome(console, len(schedule.talks), len(schedule.list_tracks()))

    # Main chat loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                if not handle_command(user_input, assistant, preferences, console):
                    break
                continue

            # Send to assistant and stream response
            console.print("\n[bold green]Assistant[/bold green]")

            response_text = ""
            for chunk in assistant.chat(user_input):
                response_text += chunk
                console.print(chunk, end="")

            console.print()  # Newline after response

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit.[/yellow]")
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
