# Selene — Unified Astrology & Divination MCP Server 🌙

The Moon of Gnosis. Merges three MCP servers into a single Python server:

1. **Helios Bridge** — 14+ ephemeris tools wrapping the Swiss Ephemeris REST API (+ auto-discovered endpoints)
2. **Knowledge Graph** — ChromaDB-backed semantic search across 6,160+ chunks from 25 astrological texts
3. **I Ching / Gnostic** — Hexagram casting (King Wen sequence) and wisdom retrieval

## Summary

| Component | Count |
|-----------|-------|
| Tools | 24 static + dynamic |
| Resources | 13 |
| Prompts | 11 |

## Tools (24+)

### Ephemeris (Helios Bridge)
| Tool | Description |
|------|-------------|
| `get_current_moon` | Current moon phase and sign |
| `get_planet_positions` | Current positions of all planets |
| `get_planet_aspects` | Current aspects between planets |
| `get_weekly_moon_phase` | This week's major moon phase |
| `get_natal_chart` | Full natal chart calculation |
| `generate_chart` | Generate and optionally save a natal chart |
| `get_chart` | Retrieve a stored chart by name |
| `list_charts` | List all stored charts |
| `get_profections` | Annual profections for a chart |
| `get_zodiacal_releasing` | ZR L1/L2 periods |
| `get_transits_now` | Current transits to a natal chart |
| `get_transit_summary` | High-level transit summary |
| `get_dignity_score` | Essential dignity score for a planet |
| `get_current_dignities` | Dignity scores for all current planets |
| `sweph_*` | Auto-discovered additional endpoints |

### Local Chart Storage
| Tool | Description |
|------|-------------|
| `store_chart` | Persist chart data locally |
| `load_chart` | Load from local storage (falls back to Helios) |
| `list_stored_charts` | List locally stored charts |
| `delete_chart` | Remove a chart from local storage |

### Knowledge Graph
| Tool | Description |
|------|-------------|
| `knowledge_search` | Semantic search across all texts |
| `knowledge_search_json` | Same, returns JSON |
| `knowledge_stats` | Collection statistics |
| `interpret_placement` | Multi-layered interpretation of a placement |

### I Ching / Gnostic
| Tool | Description |
|------|-------------|
| `cast_hexagram` | I Ching divination (coins or yarrow) |
| `retrieve_wisdom` | Search I Ching / Gnostic wisdom texts |

## Resources (13)

| URI | Description |
|-----|-------------|
| `astrology://zodiac-signs` | 12 zodiac signs with full data |
| `astrology://planets` | 10 planets with dignities & archetypes |
| `astrology://houses` | 12 houses with Rudhyar perspectives |
| `astrology://aspects` | 10 aspects with orbs & meanings |
| `astrology://traditional-astrology` | Hellenistic framework reference |
| `astrology://natal-chart` | Chandra's natal chart |
| `astrology://natal-chart/{name}` | 7 personal charts (chris, katy, micheal, betsy, megan, kelsea, lisa) |

## Prompts (11)

| Prompt | Description |
|--------|-------------|
| `narrative_weekly_forecast` | Poetic narrative forecast weaving natal + transits |
| `interpret_traditional_chart` | Traditional interpretation (Chris Brennan style) |
| `hellenistic_chart_analysis` | Hellenistic techniques analysis |
| `archetypal_chart_analysis` | Archetypal astrology (Richard Tarnas style) |
| `profection_year_analysis` | Annual profection year analysis |
| `traditional_transits_analysis` | Traditional transit analysis |
| `interpret_natal_chart` | House rulership focused interpretation |
| `analyze_current_transits` | Current transits with house rulership |
| `interpret_planets` | Current planetary positions interpretation |
| `moon_energy` | Moon phase & influence analysis |
| `weekly_planning` | Weekly astrological planning guide |

## Setup

Uses the existing astro-knowledge venv:

```bash
/home/atlas/clawd/astro-knowledge/.venv/bin/python selene_server.py
```

## mcporter config

In `~/.mcporter/mcporter.json`:

```json
"selene": {
  "type": "stdio",
  "command": "/home/atlas/clawd/astro-knowledge/.venv/bin/python",
  "args": ["/home/atlas/clawd/selene/selene_server.py"]
}
```

## Environment

- `SWEPH_API_BASE` — Sweph REST API URL (default: `http://baratie:3000`)
- `OPENAI_API_KEY` — OpenAI key (or auto-read from `~/.clawdbot/clawdbot.json`)

## Architecture

- **FastMCP** server with stdio transport
- **httpx** async client for Helios API calls
- **ChromaDB** PersistentClient for knowledge graph (6,160+ chunks)
- **OpenAI** text-embedding-3-small for embeddings
- **King Wen sequence** for I Ching hexagram mapping (verified correct)
- Auto-discovers additional sweph endpoints via `/api-info` at startup
