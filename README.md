# FOSDEM Assistant

A CLI-based AI assistant for exploring FOSDEM 2026 talks and getting personalized recommendations based on your interests.

Built in 15 minutes while stuck in a boring talk at FOSDEM. The irony.

## Features

- **Search talks** by keyword, speaker, or track
- **Personalized recommendations** based on your interests
- **Bookmark talks** to build your personal schedule
- **Natural language interface** - just tell it what you're interested in
- **Runs entirely offline** using MLX on Apple Silicon (or use Ollama/Claude API)

## Installation

```bash
git clone https://github.com/dsiganos/fosdem-assistant.git
cd fosdem-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
source .venv/bin/activate
python main.py
```

Then just chat naturally:

```
You: I'm interested in Rust and WebAssembly
Assistant: I've added Rust and WebAssembly to your interests!
          I found 12 talks matching these topics...

You: Show me the top 3 recommendations
Assistant: Here are my top recommendations:
          1. "Rust in the Linux Kernel" - Main Track, Sat 10:00
          2. "WebAssembly Beyond the Browser" - WASM Room, Sat 14:00
          ...
```

### Commands

- `/interests` - Show your saved interests
- `/bookmarks` - Show your bookmarked talks
- `/refresh` - Refresh the schedule from FOSDEM
- `/clear` - Clear conversation history
- `/quit` - Exit

## Architecture

```
fosdem/
├── main.py              # CLI entry point with Rich terminal UI
├── config.py            # Configuration (LLM provider, models)
├── schedule/
│   ├── models.py        # Pydantic models (Talk, Track, Speaker)
│   └── parser.py        # Pentabarf XML parser with caching
├── agent/
│   ├── assistant.py     # LLM client (MLX, Ollama, Anthropic)
│   └── tools.py         # 11 tool definitions for the agent
└── storage/
    └── preferences.py   # User interests & bookmarks (JSON)
```

### Tools

The agent has access to 11 tools:

| Tool | Description |
|------|-------------|
| `search_talks` | Search by keyword, topic, or speaker |
| `get_talk_details` | Get full details of a specific talk |
| `list_tracks` | Show all available tracks |
| `get_schedule_for_day` | Get talks for Saturday/Sunday |
| `add_interest` | Add a topic to your interests |
| `remove_interest` | Remove an interest |
| `get_interests` | View your saved interests |
| `get_recommendations` | Get personalized suggestions |
| `bookmark_talk` | Save a talk to your schedule |
| `remove_bookmark` | Remove a bookmark |
| `get_bookmarks` | View bookmarked talks |

## LLM Providers

### MLX (Default - Apple Silicon)

Runs entirely locally, no API keys needed:

```bash
python main.py
```

Default model: `mlx-community/Llama-3.2-3B-Instruct-4bit`

Use a different model:
```bash
export MLX_MODEL="mlx-community/Mistral-7B-Instruct-v0.3-4bit"
python main.py
```

### Ollama

```bash
ollama serve &
ollama pull llama3.1:8b
export LLM_PROVIDER=ollama
python main.py
```

### Anthropic Claude API

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
python main.py
```

## Dependencies

- `anthropic` - Claude API client
- `openai` - Ollama compatibility
- `mlx-lm` - Local inference on Apple Silicon
- `requests` - Fetching schedule XML
- `rich` - Terminal UI
- `pydantic` - Data models

## License

MIT
