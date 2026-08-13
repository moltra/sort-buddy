# Sort Buddy

This is a very simple python program that leverages OpenAI or Ollama to classify and organize emails based on their content. The system connects to an IMAP email server, retrieves unread emails, and uses AI to decide the most suitable folder to store them in.

[![asciicast](https://asciinema.org/a/85fD67bwW0XsejSPXIo92QTaT.svg)](https://asciinema.org/a/85fD67bwW0XsejSPXIo92QTaT)

## Features

- **Multiple AI Provider Support**: Uses OpenAI (ChatGPT), Ollama, or any OpenAI-compatible API to determine the folder where each email should be placed
- **Multi-Provider Email Support**: Supports generic IMAP, Gmail (with app passwords), and Yahoo Mail (with app passwords)
- Fetches unread emails from the specified IMAP server folders
- Supports a dry-run mode to simulate processing without actual folder movement
- Can optionally display prompts used to query AI for debugging
- Configurable folder prefixes for automated sorting

## Performance

In my testing, ChatGPT-4o has given me extremly good results at a cost of about $0.005 per email (one half of one cent). This is much higher than the cost of using a purpose built model, but the ease and flexibility of doing it this way is amazing.

I have also tested with various local models via [Ollama](https://ollama.com/), but acheiving a result that competes with ChatGPT-4o is difficult. Ollama provides a cost-effective alternative for those with sufficient hardware.

## Prerequisites

- Python 3.8+
- [Poetry](https://python-poetry.org/) for dependency management
- IMAP email credentials (or Gmail/Yahoo app passwords)
- For Ollama: [Ollama](https://ollama.com/) installed and running locally
- For OpenAI: OpenAI API key

## Quick Start

1. Clone the repository

```bash
git clone git@github.com:scott-r-lindsey/ai-email.git
cd sort-buddy
```

2. Install dependencies using Poetry:

```bash
poetry install
```

3. Configure environment variables

```bash
cp .env.dist .env
```

Edit `.env` and configure your AI provider and email provider (see Configuration section below).

4. Create AI folders in your email client

Open your email client and create some special folders with names that start with "AI-", or another prefix as you have selected in the `.env` configuration. Examples: "AI-Spam", "AI-Important", "AI-Mailing-List". These categories can be whatever you like.

5. Run the project

```bash
./run.sh --dry-run
```

Or run directly with Poetry:

```bash
poetry run python main.py --dry-run --show-prompt
```

## Configuration

Sort Buddy uses environment variables for configuration. Copy `.env.dist` to `.env` and customize based on your chosen providers.

### AI Provider Configuration

Choose your AI provider by setting `LLM_PROVIDER` to either `openai` or `ollama`.

#### OpenAI Configuration

```bash
LLM_PROVIDER="openai"
LLM_BASE_URL="https://api.openai.com/v1/"
LLM_API_KEY="[your-openai-api-key]"
LLM_MODEL="gpt-4-turbo"
LLM_TIMEOUT=60.0
```

**Legacy Variables (Backward Compatible):**
For existing configurations, you can still use:
- `OPENAI_API_KEY` → automatically mapped to `LLM_API_KEY`
- `OPENAI_API_URL` → automatically mapped to `LLM_BASE_URL`
- `OPENAI_MODEL` → automatically mapped to `LLM_MODEL`

#### Ollama Configuration

```bash
LLM_PROVIDER="ollama"
LLM_BASE_URL="http://localhost:11434/v1/"
LLM_API_KEY="ollama"  # Placeholder for local instances
LLM_MODEL="llama3.1:latest"
LLM_TIMEOUT=60.0
```

**Note:** Ensure Ollama is running locally with `ollama serve`. The API key is a placeholder required by the OpenAI-compatible API.

### Email Provider Configuration

Choose your email provider by setting `EMAIL_PROVIDER` to `generic`, `gmail`, or `yahoo`.

#### Generic IMAP Configuration

```bash
EMAIL_PROVIDER="generic"
IMAP_HOST="[imap.somehost.com]"
IMAP_PORT=993
IMAP_USE_SSL=true
EMAIL_USERNAME="[your email]"
EMAIL_PASSWORD="[your password]"
FOLDER_PREFIX="AI-"
```

#### Gmail Configuration

Gmail requires an app-specific password for IMAP access. [Generate one here](https://support.google.com/accounts/answer/185833).

```bash
EMAIL_PROVIDER="gmail"
GMAIL_USERNAME="[your@gmail.com]"
GMAIL_APP_PASSWORD="[your app password]"
GMAIL_LABEL_PREFIX="AI-"  # Optional, defaults to FOLDER_PREFIX
FOLDER_PREFIX="AI-"
```

**Note:** Gmail uses `imap.gmail.com` on port 993 with SSL automatically.

#### Yahoo Mail Configuration

Yahoo Mail requires an app-specific password for IMAP access. [Generate one here](https://help.yahoo.com/kb/SLN15241.html).

```bash
EMAIL_PROVIDER="yahoo"
YAHOO_USERNAME="[your@yahoo.com]"
YAHOO_APP_PASSWORD="[your app password]"
YAHOO_FOLDER_PREFIX="AI-"  # Optional, defaults to FOLDER_PREFIX
FOLDER_PREFIX="AI-"
```

**Note:** Yahoo Mail uses `imap.mail.yahoo.com` on port 993 with SSL automatically.

### Common Configuration

```bash
FOLDER_PREFIX="AI-"  # Prefix for AI-sorted folders
```

### Provider Selection Logic

- If `LLM_PROVIDER` is not set, defaults to `openai`
- If `EMAIL_PROVIDER` is not set, defaults to `generic`
- Legacy `OPENAI_*` variables are automatically mapped to `LLM_*` when using OpenAI provider
- Generic IMAP variables (`IMAP_HOST`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`) are used when `EMAIL_PROVIDER=generic`

## Running the Project

### Using the run.sh script

```bash
./run.sh --dry-run
```

### Running directly with Poetry

```bash
poetry run python main.py --dry-run --show-prompt
```

### Command-line Options

- `--dry-run`: Print prompts and messages without moving any emails
- `--show-prompt`: Display the AI prompt, minus the email body
- `--limit`: Max number of messages to process
- `--save-to-json`: Save messages and the resulting sort to a file, for benchmarking different LLMs
- `--use-json`: Instead of connecting to an IMAP server, use a previously saved file as input
- `--print-rate-limits`: Output the [rate limit](https://platform.openai.com/docs/guides/rate-limits) headers provided by OpenAI (not applicable for Ollama)

## Testing

Sort Buddy uses pytest for testing. Run tests with:

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_config.py

# Run with verbose output
poetry run pytest -v
```

Tests are organized into:
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests (optional, requires local services)

**Note:** Integration tests require a local Ollama instance and/or IMAP server. These are skipped in CI by default.

## Contribution

Feel free to submit issues or pull requests to improve the functionality.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
