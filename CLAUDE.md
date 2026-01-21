# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stella is an Obsidian plugin providing an AI chat interface with multi-provider LLM support, note context integration, and future MCP (Model Context Protocol) integration. The project has completed Phase 1 with all core functionality working smoothly.

## Build Commands

```bash
# Development mode (watch mode with sourcemaps)
npm run dev

# Production build (TypeScript check + bundle)
npm run build

# Version bump (updates manifest.json and versions.json)
npm run version
```

## Current Status: ✅ PHASE 1 COMPLETE - All Core Features Working

### ✅ Recently Completed (September 2025)
1. **Fixed Critical Bugs**: Markdown rendering and chat truncation issues resolved
2. **Enhanced Conversation Management**: Date-based titles, persistent storage, delete functionality
3. **System Prompt Integration**: `/sys` command to load .md system prompts, `/sysclear` to remove
4. **Note Context Feature**: "@" symbol to add vault notes as context, with visual indicators
5. **UI Polish**: Improved date calculations, neutral colors, clean interface
6. **MCP Integration Debugging**: Fixed undefined array errors, enhanced error handling, working tool execution
7. **Enhanced Tooltips**: Fixed MCP tooltip positioning and layout issues
8. **Improved Context Indicators**: Replaced chip-based note display with clean inline page icon, added hover tooltips showing filenames for system prompts and mental models
9. **Help Command**: Added `/help` command with dynamic, extensible command list that auto-updates when new commands are added, displays as formatted code block with monospace styling
10. **Windows MCP Server Fix**: Fixed Windows compatibility for npm/npx MCP servers with proper shell execution and .cmd handling

## Architecture Overview

The plugin follows Obsidian's plugin architecture with robust functionality:

### Core Classes

- **`StellaPlugin`** (main.ts:32): Main plugin class handling lifecycle, view registration, and settings management
- **`StellaChatView`** (main.ts:~100): Chat interface view extending Obsidian's `ItemView` for the right sidebar
- **`StellaSettingTab`** (main.ts:~1400+): Settings interface extending `PluginSettingTab` for provider/API configuration

### Key Architecture Patterns

- **Multi-Provider LLM Support**: Unified interface for Anthropic, OpenAI, Google, Ollama, LM Studio, and custom APIs
- **Dynamic Model Fetching**: Real-time model lists fetched from actual APIs via `fetchModelsForProvider()`
- **Conversation Management**: Persistent conversations with date-based titles and full history
- **Context Integration**: System prompts and note context seamlessly integrated into API calls
- **View-Based Chat**: Obsidian workspace integration using `WorkspaceLeaf` and custom view type `CHAT_VIEW_TYPE`

### API Integration Architecture

Each provider implements the same interface pattern with context support:
- Model fetching: Provider-specific endpoints (`/v1/models`, `/v1beta/models`, `/api/tags`)
- Message sending: Unified `callLLM()` method with context integration via `buildSystemMessage()`
- Context handling: System prompts, mental models, and note context automatically included in all API calls
- Error handling: Provider-specific error parsing and fallbacks

### UI Components Structure

- **Header Bar**: Editable conversation name + model info + action buttons (new, history, settings)
- **Chat Area**: Message list with working markdown rendering using Obsidian's `MarkdownRenderer`
- **Context Indicator**: Clean bar above input showing loaded note context as removable chips
- **Input Area**: Clean textarea + copy button + send button with keyboard shortcuts

## Current Features

### ✅ Core Chat Functionality
- Multi-provider LLM support (Anthropic, OpenAI, Google, Ollama, LM Studio, Custom)
- Real-time model fetching and selection
- Persistent conversation history with proper chat flow
- Markdown rendering for AI responses
- Copy last response functionality

### ✅ Advanced Features
- **System Prompts**: `/sys` command opens file browser for .md system prompts in configurable directory
- **Mental Models**: `/model` command opens file browser for .md mental model files (thinking frameworks) in configurable directory
- **Wiki Link Resolution**: `[[Note Name]]` automatically becomes clickable links in all chat messages
- **Note Context**: "@" symbol opens quick switcher to add vault notes as context
- **Conversation Management**: Date-based titles, persistent storage, conversation switching
- **Clean UI**: Professional styling with Obsidian theme compatibility

### ✅ User Experience
- **Keyboard Shortcuts**: Enter to send, "@" for notes, "/sys" for system prompts, "/model" for mental models
- **Interactive Wiki Links**: Click `[[Note]]` to add to context, Ctrl+Click to open in main window
- **Visual Indicators**: Note context (page icon), system prompt (square-terminal icon), mental model (eclipse icon), MCP (bow-arrow icon) - all with hover tooltips
- **Clean Interface**: No placeholder text, neutral colors, proper spacing
- **Delete Functionality**: Remove conversations and context notes easily

## Available Commands

All commands are accessible via the chat input. Type `/help` to see this list in the chat displayed as a formatted code block with aligned, monospace text.

### Context Management
- **`/help`** - Show all available commands (displays as formatted code block with monospace styling)
- **`/sys`** - Load system prompt from file (defines AI identity/role)
- **`/sysclear`** - Clear current system prompt
- **`/model`** - Load mental model from file (thinking frameworks)
- **`/modelclear`** - Clear current mental model
- **`/mcp`** - Connect to MCP server (Model Context Protocol)
- **`/mcpclear`** - Clear MCP connections
- **`/clear`** - Clear all context and start new conversation

### Conversation Management
- **`/new`** - Start new conversation
- **`/del`** - Delete current conversation
- **`/history`** - Show conversation history
- **`/name`** - Rename current conversation

### Interface
- **`/settings`** - Open plugin settings
- **`/hide`** - Toggle header visibility

### Special Input
- **`@`** - Add note context (opens quick switcher)
- **`[[Note]]`** - Interactive wiki links (click to add context, Ctrl+click to open)

## File Structure & Responsibilities

```
main.ts                 # Single-file plugin (~2800+ lines) containing all logic
├── StellaPlugin     # Main plugin class (lines 32-96)
├── StellaChatView   # Chat UI and message handling (lines ~100-1200)
├── StellaSettingTab # Settings interface (lines ~1400+)
└── Interfaces & Utils  # Settings, message types, API helpers, context management

styles.css              # Complete UI styling with context indicators, modal styles, and wiki link styling
manifest.json           # Plugin metadata and version info
esbuild.config.mjs      # Build configuration with watch/production modes
PROJECT_STATUS.md        # Detailed project status and roadmap
```

## Key Implementation Details

### Message Flow (✅ Working)
1. User input → `sendMessage()` → `callLLM()` → Provider API
2. Context integration via `buildSystemMessage()` combining system prompts, mental models, and notes
3. Wiki link processing via `processAllWikiLinks()` for interactive note navigation
3. Response handling with full conversation history maintained
4. Markdown rendering via Obsidian's `MarkdownRenderer.renderMarkdown(content, container, '', this)`

### Context Integration (✅ Enhanced Features)
- **System Prompts**: Loaded from configurable directory via `/sys` command, defines AI identity/role
- **Mental Models**: Loaded from configurable directory via `/model` command, provides thinking frameworks
- **Note Context**: Added via "@" symbol, stored in `contextNotes` array
- **API Integration**: Combined in `buildSystemMessage()` and sent to all providers
- **Visual Feedback**: Context chips show loaded notes, system prompt indicator (square-terminal icon), mental model indicator (eclipse icon)

### Mental Model Feature (✅ New in September 2025)
The mental model feature provides thinking frameworks that guide how the AI approaches problems, separate from system prompts which define identity/role:

**Key Distinctions:**
- **System Prompts** (`/sys`): Define AI identity, role, and personality - "You are a coding assistant"
- **Mental Models** (`/model`): Define thinking frameworks and methodologies - "Use first principles reasoning"

**Implementation Details:**
- **Commands**: `/model` to load, `/modelclear` to remove mental models
- **File Format**: Standard .md files stored in configurable directory (`mentalModelsPath` setting)
- **Visual Indicator**: Eclipse icon positioned dynamically (left of system prompt when both active)
- **Modal Interface**: File browser with preview, keyboard navigation (arrows, Enter, Escape)
- **Positioning Logic**: Smart indicator placement - mental model takes right edge when alone, moves left when system prompt is also active
- **Persistence**: Mental models saved per conversation in `data.json`
- **API Integration**: Mental models combined with system prompts in `buildSystemMessage()` and sent to all LLM providers

**Architecture:**
```typescript
interface Conversation {
    systemPrompt?: string;    // AI identity/role
    mentalModel?: string;     // Thinking framework
    messages: Message[];
}

// Dynamic positioning based on active contexts
updateIndicatorPositions() {
    if (hasMentalModel && hasSystemPrompt) {
        // Both: mental model at 48px, system prompt at 16px
    } else if (hasMentalModel && !hasSystemPrompt) {
        // Only mental model: takes right edge (16px)
    }
}
```

### Wiki Link Resolution Feature (✅ New in September 2025)
Automatic resolution and interaction with Obsidian wiki links in chat messages:

**Automatic Recognition:**
- Detects `[[Note Name]]` and `[[Note Name|Display Text]]` patterns in both user messages and LLM responses
- Works in all message types: user input, assistant responses, system messages
- Handles both markdown-rendered content and plain text

**Interactive Behavior:**
- **Regular Click**: Silently adds note to context (no chat message)
- **Ctrl+Click** (Cmd+Click on Mac): Opens note in main Obsidian window using native navigation
- **Visual Styling**: Links styled to match Obsidian's appearance with proper hover effects
- **Missing Notes**: Different styling for non-existent notes with error handling

**Technical Implementation:**
```typescript
// Dual processing approach for comprehensive coverage
processAllWikiLinks(container, originalContent) {
    this.enhanceExistingWikiLinks(container);      // Links Obsidian processed
    this.processUnprocessedWikiLinks(container, originalContent);  // Remaining links
}

// Smart text node processing with TreeWalker
collectTextNodes(node, textNodes) {
    // Recursively finds ALL text nodes containing [[links]]
}
```

**Architecture Benefits:**
- **Robust Processing**: Works regardless of Obsidian's markdown processing
- **Performance Optimized**: Only processes when wiki links are actually present
- **Context Integration**: Seamlessly integrates with existing `@` note context system
- **Error Resilient**: Graceful handling of missing notes and edge cases

### Conversation Management (✅ Enhanced)
- **Persistent Storage**: Conversations saved in `data.json` with full message history
- **Date-based Titles**: Uses `toLocaleDateString('en-CA')` for correct local date formatting
- **Conversation Switching**: Load previous conversations via history modal
- **Delete Functionality**: Remove conversations with trash icon in history modal

### Settings Persistence
- Settings stored in `data.json` via Obsidian's `loadData()`/`saveData()`
- Current config: Multi-provider support, API keys, model selection
- System prompt directory configuration
- Mental models directory configuration
- Conversation history and context state

### View Management
- Chat opens in right sidebar using `getRightLeaf(false)`
- Single view instance with `detachLeavesOfType()` before activation
- Proper cleanup in `onunload()` to prevent memory leaks
- Context indicators positioned cleanly above input area

## Development Workflow

### Testing Changes
1. Use `npm run dev` for development with auto-rebuild
2. Reload the plugin in Obsidian developer tools (Ctrl+Shift+I → Console → `app.plugins.disablePlugin('stella'); app.plugins.enablePlugin('stella')`)
3. Test with configured provider (currently Google Gemini)
4. Test all features: conversations, system prompts, mental models, wiki links, note context, provider switching

### Adding New LLM Providers
1. Add provider option to settings interface in `StellaSettingTab`
2. Implement API endpoint in `fetchModelsForProvider()` method
3. Add request format handling in `callLLM()` method with context support
4. Update settings interface with provider-specific fields
5. Test context integration (system prompts + mental models + notes + wiki links) with new provider

### Current Provider Status
- **Working & Tested**: Anthropic Claude, Google Gemini, OpenAI GPT
- **Available**: Ollama (local), LM Studio (local), Custom API
- **Default**: Google Gemini with gemini-2.5-pro model
- **Context Support**: All providers support system prompts, mental models, and note context

## Notable Implementation Patterns

### Windows MCP Server Compatibility
```typescript
// Automatic Windows .cmd handling with shell execution
private fixWindowsCommand(command: string): string {
    if (process.platform !== 'win32') return command;

    const windowsCommands = ['npm', 'npx', 'yarn', 'pnpm', 'node'];
    const baseCommand = command.split(' ')[0];
    if (windowsCommands.includes(baseCommand) && !baseCommand.endsWith('.cmd')) {
        return command.replace(baseCommand, `${baseCommand}.cmd`);
    }
    return command;
}

// Shell execution for .cmd files on Windows
const spawnOptions: any = { stdio: ['pipe', 'pipe', 'pipe'], env };
if (process.platform === 'win32' && command.endsWith('.cmd')) {
    spawnOptions.shell = true;
}
const childProcess = spawn(command, args, spawnOptions);
```

### Context System Architecture
```typescript
// Context system with multiple types
currentSystemPrompt: string | null = null;
currentMentalModel: string | null = null;
contextNotes: Array<{name: string, content: string}> = [];

// Combined system message for API calls
buildSystemMessage(): string {
    // Combines currentSystemPrompt + currentMentalModel + contextNotes
    let systemMessage = '';
    if (this.currentSystemPrompt) {
        systemMessage += this.currentSystemPrompt;
    }
    if (this.currentMentalModel) {
        if (systemMessage) systemMessage += '\n\n';
        systemMessage += this.currentMentalModel;
    }
    // ... contextNotes integration
}

// Visual indicators with positioning logic
updateSystemPromptIndicator() { /* square-terminal icon */ }
updateMentalModelIndicator() { /* eclipse icon */ }
updateIndicatorPositions() { /* dynamic positioning when both active */ }
```

### Event Handling Patterns
```typescript
// Keyboard shortcuts with prevention
if (e.key === '@') {
    e.preventDefault(); // Prevents @ from appearing in input
    this.showNoteSelector();
}
```

### Modal Pattern for File Selection
```typescript
// Consistent modal pattern used for:
// - System prompt selection (file browser with preview)
// - Mental model selection (file browser with preview)
// - Note context selection (quick switcher)
// - Conversation history (clickable list)
```

## Future Roadmap

### Next Phase: MCP Integration
- MCP client implementation for tool connections
- WebSocket support for MCP servers
- Extended context sharing with vault
- Tool invocation commands
- Semantic search capabilities

### Potential Enhancements
- Conversation templates and export functionality
- Advanced context management (folders, tags)
- Plugin ecosystem integration
- Performance optimizations for large vaults

## Current Status
- Phase 1: ✅ **COMPLETE** - All core functionality working smoothly
- Build: ✅ Builds successfully with no runtime errors
- Features: ✅ Multi-provider LLM, conversations, system prompts, mental models, wiki links, note context
- UI/UX: ✅ Clean interface with proper Obsidian integration
- Next: Ready for MCP integration or additional feature development

## Session Notes for Future Development
- **Last Updated**: September 28, 2025
- **Status**: All core features working, Windows MCP compatibility fixed
- **Recent Work**: Fixed Windows MCP server spawning issues with proper shell execution for .cmd files
- **Ready For**: Additional feature development or Phase 2 planning
- **Latest Features**:
  - Windows MCP server compatibility with automatic .cmd handling and shell execution
  - Clean inline note context icon (replacing chip display)
  - Hover tooltips showing filenames for system prompts and mental models
  - `/help` command with extensible command list, formatted as styled code block
  - Consistent visual design across all indicators
- **Known Issues**: None currently blocking

### Current Development Status
- **MCP Integration**: ✅ **WORKING** - Tools executing successfully with proper error handling, Windows compatibility fixed
- **Windows Support**: ✅ **COMPLETE** - MCP servers using npm/npx now work properly on Windows with shell execution
- **Context Indicators**: ✅ **ENHANCED** - Clean inline design with hover tooltips showing relevant info
- **UI/UX**: ✅ **COMPLETED** - Consistent design, proper positioning, informative tooltips
- **Command System**: ✅ **EXTENSIBLE** - Centralized `availableCommands` array that auto-updates help display with styled formatting
- **Next Priority**: Phase 2 planning or additional feature requests