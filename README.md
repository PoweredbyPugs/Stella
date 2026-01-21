# Stella

An AI chat plugin for [Obsidian](https://obsidian.md) with multi-provider LLM support, MCP integration, and deep vault integration.

## Features

- **Multi-Provider Support** - Anthropic, OpenAI, Google, Ollama, LM Studio, or any OpenAI-compatible API
- **MCP Integration** - Connect to Model Context Protocol servers for extended tool capabilities
- **Vault Integration** - Add notes as context, click `[[wiki links]]` in chat to navigate
- **System Prompts** - Load prompts from markdown files to customize AI behavior
- **Mental Models** - Load thinking frameworks to guide AI reasoning
- **Conversation Management** - Multiple threads, history, persistence

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
| `/history` | View conversation history |
| `/help` | Show all commands |

### Adding Context

- Type `@` to search and add notes as context
- Use `[[Note Name]]` in messages - click to add as context, Ctrl+click to open

## Configuration

1. Open Settings → Stella
2. Select your LLM provider
3. Enter your API key
4. (Optional) Set paths for system prompts and mental models folders

### Supported Providers

| Provider | Models | Local |
|----------|--------|-------|
| Anthropic | Claude 3.5, Claude 3 | No |
| OpenAI | GPT-4, GPT-3.5 | No |
| Google | Gemini Pro, Gemini Flash | No |
| Ollama | Llama, Mistral, etc. | Yes |
| LM Studio | Any GGUF model | Yes |
| Custom | OpenAI-compatible | Varies |

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
