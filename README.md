# 🌙 Selene — Unified Astrology MCP Server

> *Σελήνη — The Moon. She reflects the light of Helios through knowledge, making meaning from data.*

Selene is the interpretive intelligence layer of **Gnosis**, a modular astrology system. She unifies ephemeris calculations, a curated knowledge graph, and I Ching divination into a single MCP (Model Context Protocol) server.

## Architecture

```
Gnosis (the system)
├── Helios ☀️  — Swiss Ephemeris REST API (planetary calculations)
│   └── Docker: sweph @ baratie:3000
├── Selene 🌙  — This server (MCP interface for LLMs)
│   ├── Helios Bridge (14 ephemeris tools)
│   ├── Knowledge Graph (6,160+ chunks, 25 texts, ChromaDB)
│   ├── I Ching Divination (hexagram casting + Gnostic wisdom)
│   ├── Resources (zodiac, planets, houses, aspects, charts)
│   └── Prompts (11 interpretation templates)
└── [Future: Orchestrator — Helios → Selene → Narrative]
```

## Tools (20)

### ☀️ Helios Bridge — Ephemeris
| Tool | Description |
|---|---|
| `get_current_moon` | Current moon phase and sign |
| `get_planet_positions` | All current planetary positions |
| `get_planet_aspects` | Current aspects between planets |
| `get_weekly_moon_phase` | This week's major moon phase |
| `get_natal_chart` | Calculate natal chart (date, time, location) |
| `generate_chart` | Generate + store a natal chart |
| `get_chart` | Retrieve stored chart by name |
| `list_charts` | List all stored charts |
| `get_profections` | Annual profections for a chart |
| `get_zodiacal_releasing` | ZR L1/L2 periods (Spirit/Fortune) |
| `get_transits_now` | Current transits to a natal chart |
| `get_transit_summary` | Major outer planet transit summary |
| `get_dignity_score` | Essential dignity for any placement |
| `get_current_dignities` | All planets' dignity scores now |

### 📚 Knowledge Graph
| Tool | Description |
|---|---|
| `knowledge_search` | Semantic search across 25 astrological texts |
| `knowledge_search_json` | Same, structured JSON output |
| `knowledge_stats` | Collection statistics |
| `interpret_placement` | Multi-layered interpretation (technical → archetypal) |

### 🎴 I Ching
| Tool | Description |
|---|---|
| `cast_hexagram` | Traditional I Ching divination (coins/yarrow) |
| `retrieve_wisdom` | Search the Gnostic Book of Changes |

## Resources (13)

- `astrology://zodiac-signs` — 12 signs with elements, rulers, archetypes
- `astrology://planets` — 10 planets with dignities and meanings
- `astrology://houses` — 12 houses with themes and rulers
- `astrology://aspects` — Aspect types with orbs and interpretations
- `astrology://traditional-astrology` — Hellenistic technique reference
- `astrology://natal-chart` — Chandra's natal chart
- `astrology://natal-chart/{name}` — Personal charts (chris, katy, micheal, betsy, megan, kelsea, lisa)

## Prompts (11)

Interpretation templates for LLMs: narrative weekly forecast, Hellenistic analysis, archetypal analysis, profection year, transit analysis, weekly planning, and more.

## Knowledge Graph

6,160+ chunks from 25 curated texts across 5 interpretive layers:

| Layer | Color | Sources |
|---|---|---|
| **Technical** | 🔵 | Brennan (Hellenistic), Lehman (Dignities) |
| **Psychological** | 🟣 | Sasportas (Houses), Green (Outer Planets) |
| **Archetypal** | 🟡 | Tarnas (Cosmos & Psyche) |
| **Philosophical** | 🔷 | Stoic essays, fate/free will |
| **Reference** | 🟢 | Planet PDFs (Sun–Pluto + Nodes), Wen, ZR materials |

## Setup

```bash
# Dependencies (uses existing astro-knowledge venv)
cd /path/to/selene
pip install mcp chromadb openai httpx pydantic

# Run
python selene_server.py

# Or via mcporter
npx mcporter call selene.get_current_moon
npx mcporter call selene.knowledge_search query="Saturn return"
npx mcporter call selene.cast_hexagram question="What now?"
```

### mcporter config
```json
{
  "selene": {
    "type": "stdio",
    "command": "python",
    "args": ["selene_server.py"]
  }
}
```

### Environment
- `SWEPH_API_BASE` — Helios REST API URL (default: `http://baratie:3000`)
- `OPENAI_API_KEY` — For embeddings (or auto-reads from clawdbot config)

## Naming

From the Greek Σελήνη (Selene), goddess of the Moon. Where Helios (the Sun) provides raw astronomical truth, Selene reflects that light through curated knowledge to create meaning. Part of the **Gnosis** (Γνῶσις — Knowledge) system.

## License

Private. Part of the Gnosis astrology project.
