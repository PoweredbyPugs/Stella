# Stella

An AI chat plugin for [Obsidian](https://obsidian.md) with multi-provider LLM support, MCP integration, and deep vault integration.

## Features

- **Multi-Provider Support** - Anthropic, OpenAI, Google, Ollama, LM Studio, OpenClaw, or any OpenAI-compatible API
- **MCP Integration** - Connect to Model Context Protocol servers for extended tool capabilities
- **Vault Integration** - Add notes as context, click `[[wiki links]]` in chat to navigate
- **System Prompts** - Load persona and behavior prompts from markdown files
- **Mental Models** - Load reasoning frameworks that the LLM actively applies as an analytical lens, distinct from the system prompt
- **Conversation Management** - Multiple threads, history, smart auto-save

## Installation

### From Source

1. Clone this repo into your vault's plugins folder:
   ```bash
   cd /path/to/vault/.obsidian/plugins
   git clone https://github.com/PoweredbyPugs/Stella.git
   cd Stella
   ```

2. Install dependencies and build:
   ```bash
   npm install
   npm run build
   ```

3. Enable the plugin in Obsidian: Settings → Community Plugins → Stella

### Manual Installation

1. Download the latest release
2. Extract to `.obsidian/plugins/Stella/`
3. Enable in Obsidian settings

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `/sys` | Load a system prompt |
| `/sysclear` | Clear system prompt |
| `/model` | Load a mental model |
| `/modelclear` | Clear mental model |
| `/mcp` | Connect to MCP server |
| `/mcpclear` | Disconnect MCP |
| `/new` | New conversation |
| `/del` | Delete current conversation |
| `/name` | Rename current conversation |
| `/history` | View conversation history |
| `/clear` | Clear all context and start fresh |
| `/settings` | Open plugin settings |
| `/hide` | Toggle header visibility |
| `/help` | Show all commands |

### Adding Context

- Type `@` to search and add notes as context
- Use `[[Note Name]]` in messages — click to add as context, Ctrl+click to open

### System Prompts vs Mental Models

Stella treats these as distinct concepts:

- **System Prompt** (`/sys`) — Defines identity, persona, tone, and behavioral constraints. The LLM adopts this as its character.
- **Mental Model** (`/model`) — A reasoning framework the LLM actively applies to evaluate and filter its responses. Injected with an explicit instruction to think through the framework, not just reference it.

Both can be loaded simultaneously. The system prompt shapes *who* the LLM is; the mental model shapes *how* it thinks.

## Configuration

1. Open Settings → Stella
2. Select your LLM provider
3. Enter your API key
4. (Optional) Set paths for system prompts and mental models folders

### Supported Providers

| Provider | Local | Notes |
|----------|-------|-------|
| Anthropic | No | Claude models |
| OpenAI | No | GPT models |
| Google | No | Gemini models, native MCP support |
| Ollama | Yes | Any Ollama-hosted model |
| LM Studio | Yes | Any GGUF model |
| OpenClaw | Yes | WebSocket gateway for local agent models |
| Custom | Varies | Any OpenAI-compatible endpoint |

## Development

```bash
# Development mode (watch)
npm run dev

# Production build
npm run build
```

### Project Structure

```
Stella/
├── main.ts              # Main plugin entry
├── src/
│   ├── types/           # TypeScript interfaces
│   ├── services/        # Cache, logger, MCP client
│   ├── providers/       # LLM provider implementations
│   └── views/           # Modal components
├── styles.css           # Plugin styles
└── manifest.json        # Obsidian plugin manifest
```

## License

MIT

## Author

PoweredbyPugs
