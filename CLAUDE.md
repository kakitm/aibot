# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Linting and Type Checking
```bash
# Run linter with auto-fix
ruff check --fix src/

# Format code
ruff format src/

# Type checking
mypy src/
```

### Running the Bot
```bash
# Start the Discord bot (requires environment variables)
python -m src.aibot

# Or using Python module execution
python src/aibot/__main__.py
```

### Environment Variables Required
The bot requires these environment variables:
- `DISCORD_BOT_TOKEN`: Discord bot token for authentication
- `BOT_NAME`: Discord bot's display name
- `BOT_ID`: Discord bot's user ID (integer)
- `ADMIN_USER_IDS`: Comma-separated list of admin user IDs
- `DB_NAME`: SQLite database file name (default: "aibot.db")
- `TIMEZONE`: Timezone for database operations (default: "Asia/Tokyo")

## Architecture Overview

This is an AI-powered Discord bot that integrates multiple LLM providers (Anthropic, Google Gemini, OpenAI) with voice channel management and usage tracking.

### Core Architecture Patterns

**Singleton Bot Client**: The `BotClient` class uses a singleton pattern accessed via `BotClient.get_instance()`. All Discord commands are registered on this single instance.

**DAO Layer with Base Class**: All database operations inherit from `DAOBase` which provides:
- Database connection management (SQLite via aiosqlite)
- Table name validation (alphanumeric + underscores only)
- Timezone configuration (Asia/Tokyo default)
- Environment-based database naming

**Multi-Provider LLM Support**: The API layer abstracts three LLM providers with unified parameter classes (`ClaudeParams`, `GeminiParams`, `GPTParams`) and a type union `LLMParams`.

### Key Components

**Connection Management**: The `ConnectionDAO` implements a dual-table design:
- `connection_status` table: Single record tracking current voice channel connection
- `connection_history` table: Complete audit log of all connection events (CONNECT/DISCONNECT/ERROR)
- Transactional safety ensures data consistency during connection state changes

**Usage Tracking System**: The `UsageDAO` manages API call limits with:
- Per-user daily limits with fallback to default limits
- Daily usage counters with automatic reset
- User ID "0" represents the default limit for all users

**Service Layer Architecture**: Key services implement singleton patterns:
- `ProviderManager`: Manages current AI provider selection (anthropic/google/openai)
- `RestrictionService`: Controls instruction modification restrictions
- `InstructionService`: Handles custom instruction storage and retrieval

**Chat Message Processing**: The `ChatMessage` and `ChatHistory` classes handle Discord message conversion to LLM-compatible format, with special handling for:
- Thread messages created by the bot
- Role mapping (BOT_NAME → "assistant", others → "user")
- Message validation and content extraction

### Discord Command Structure

Commands are organized in `/src/aibot/discord/commands/` with each file containing related functionality:
- `chat.py`: LLM chat integration with message history processing
- `connection.py`: Voice channel join/leave with database tracking
- `fixme.py`: Code debugging via LLM with modal input
- `instruction.py`: Custom instruction management system
- `limit.py`: Usage limit management (admin-only)
- `provider.py`: AI provider selection and management

**Permission System**: Admin commands use the `@is_admin_user()` decorator which validates against the `ADMIN_USER_IDS` environment variable.

**Restriction System**: Custom instruction commands use the `@is_restricted()` decorator to prevent instruction creation/modification when restriction mode is active via `RestrictionService`.

**Voice Channel Integration**: Voice operations use VoiceProtocol type annotations but rely on discord.py's polymorphic behavior where `ctx.voice_client` returns VoiceClient instances at runtime.

### Database Design Philosophy

**State vs History Separation**: Connection tracking separates current state (single record) from historical events (append-only log) to optimize both real-time queries and analytics.

**Defensive Validation**: All table names are validated against SQL injection via regex pattern matching before query construction.

**Timezone Consistency**: All datetime operations use the configured timezone (default Asia/Tokyo) for consistent data storage.

### Code Quality Standards

- Line length: 99 characters (PEP8 + team agreement)
- Type hints: Strict mypy configuration with untyped code disallowed
- String quotes: Double quotes preferred over single quotes
- Modern Python: Uses union syntax (`str | None` over `Optional[str]`)
- Docstring format: NumPy style with Parameters/Returns sections

## Common Pitfalls

### TRY300 - Use `else` block instead of `return` in `try`

**Code that should execute only when no exception occurs should be written in `else` block, not inside `try`.**

Using `return` inside a `try` block can lead to unexpected behavior or reduced readability when the result gets overwritten/ignored by `except` or `finally` blocks, or when exceptions are inadvertently suppressed.

Bad example (returning inside try block):
```python
try:
    value = compute()
    return value
except ValueError:
    return default
finally:
    cleanup()  # If an exception occurs here, the above return is ignored
```

Good example (using else to explicitly indicate "execute only when no exception"):
```python
try:
    value = compute()
except ValueError:
    return default
else:
    return value
finally:
    cleanup()
```

## Git

The commit message template is located in `.github/.gitmessage`. Please create commit messages following the template.
