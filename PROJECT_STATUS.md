# Stella × OpenClaw Integration — Project Status

## ✅ Working
- OpenClaw WebSocket provider (`src/providers/openclaw.ts`)
- Gateway protocol v3 handshake with connect.challenge support
- Provider dropdown: "OpenClaw (Robin)" with dedicated settings UI
- `chat.send` → agent run → `chat` event streaming → response displayed
- Persistent session (`agent:main:main`) shared with Telegram/iMessage/webchat
- Full agent tools, memory, MCP servers accessible from Obsidian
- Model auto-set to `openclaw:main`

## 🔧 Needs Work

### Streaming Quality
- **Not real-time**: Response appears all at once or in large chunks instead of token-by-token
  - `updateContent()` is called correctly but DOM may not repaint between rapid event batches
  - Investigate: requestAnimationFrame, chunked rendering, or yielding to event loop between updates
- **Garbled/missing text**: Some words lost or concatenated during tool-heavy responses
  - Likely cause: content array has `tool_use`/`tool_result` blocks interspersed with `text` blocks
  - Delta calculation may miss text when array structure shifts between events
  - Fix: track text parts by index, not just total length

### Markdown Rendering
- **Tables render as raw pipes during streaming** — only rendered as markdown after `onComplete`
  - `contentEl.textContent = accumulatedResponse` during stream = no markdown
  - Could use incremental `MarkdownRenderer.renderMarkdown()` during stream (perf concern?)
  - Or: render markdown every N characters / on a debounce timer during streaming

### UI Polish
- **Bulbasaur GIF missing**: `ENOENT` on load — path expects `Stella/bulbasaur.gif` but file missing or misnamed
- **Loading state**: Bulbasaur loading animation fails silently

## 📋 Future Features
- [ ] Load `chat.history` from gateway on plugin start (method already implemented in provider)
- [ ] Wire abort button to `chat.abort` 
- [ ] Show tool execution status in chat (tool names, progress)
- [ ] Dedicated Obsidian session option (vs shared main session)
- [ ] Attachments — send images/files through the WebSocket
- [ ] Connection status indicator in the UI
- [ ] Auto-reconnect on disconnect

## Architecture
```
Stella Plugin (Obsidian)
  └─ src/providers/openclaw.ts (WebSocket client)
       └─ ws://127.0.0.1:18789 (OpenClaw Gateway)
            └─ agent:main:main session
                 └─ Claude + tools + memory + MCP
```

## Config
- **Gateway URL**: `ws://127.0.0.1:18789` (local) or `wss://atlas.tail4a61d3.ts.net` (Tailscale)
- **Gateway Token**: stored in plugin settings as `customApiKey`
- **Client ID**: `gateway-client` (mode: `backend`) — bypasses browser origin check
- **Gateway config**: `app://obsidian.md` added to `controlUi.allowedOrigins` (may not be needed with backend mode)

## Dev Notes
- Source: `~/Documents/KAI/.obsidian/plugins/Stella-dev/`
- Deploy: `npm run deploy` → copies to `../Stella/`
- The provider only sends the latest user message — OpenClaw manages all history server-side
- Plugin's local conversation history is a separate view (Obsidian-only log)
