# Selene — Unified Astrology & Divination MCP Server 🌙

The Moon of Gnosis. Merges three MCP servers into a single Python server:

1. **Helios Bridge** — 14+ ephemeris tools wrapping the Swiss Ephemeris REST API (+ auto-discovered endpoints)
2. **Knowledge Graph** — ChromaDB-backed semantic search across 6,500+ chunks from 26 astrological texts
3. **Chart Reading System** — 3-axis report generation (Type × Framework × Size = 75 combinations)
4. **I Ching / Gnostic** — Hexagram casting (King Wen sequence) and wisdom retrieval

## Chart Reading System

The core feature. Generates complete chart readings through three independent axes:

### Type (the medium — HOW)
| Type | Description |
|------|-------------|
| `technical` | Data-forward. Astro language preserved. For practitioners. |
| `narrative` | Human-first portrait. No jargon. Tech appendix at end. |
| `poem` | Artistic distillation. Verse or lyric prose. Tech appendix. |

### Framework (the lens — WHAT)
| Framework | Description |
|-----------|-------------|
| `psychological` | Attachment, shadow, individuation. Non-fatalist. |
| `deterministic` | GTEI. Necessitated unfolding via Absolute Self-Consistency. |
| `hellenistic` | Sect, dignity, lots, timing. Vettius Valens lineage. |
| `stoic` | Virtue, fate, discipline of assent. Marcus Aurelius meets the chart. |
| `mythological` | Gods, archetypes, hero's journey. |

### Size (the depth — HOW MUCH)
| Size | Length | Description |
|------|--------|-------------|
| `xs` | 3-5 sentences | The Glance |
| `s` | 2-3 paragraphs | Key Themes |
| `m` | 1-2 pages | Working Reading |
| `l` | 3-5 pages | Full Narrative |
| `xl` | 5-10+ pages | The Deep Dive |

### Computation Pipeline

Every reading runs the full computation regardless of size:
1. **Natal chart** (planets, angles, lots, depositors, sect)
2. **Whole sign houses** (computed by Selene from ASC sign)
3. **Essential dignities** (domicile, exaltation, triplicity, term, face, detriment, fall)
4. **Derivative houses** (Pelletier system — house-to-house relationships + aspect geometry)
5. **Dignity-weighted narrative priority** (strongest planets drive narrative weight)
6. **Current aspects** between all planets
7. **Profections** (annual, lord of year)
8. **Zodiacal Releasing** (Spirit + Fortune, L1/L2, peak periods)
9. **Transits** to natal chart
10. **Knowledge graph queries** (grounded in 26-text corpus)

### Dignity-Weighted Narrative Priority

A key calibration: dignity score determines which planets dominate the narrative.
- Strongest planet by score → most narrative real estate
- Weak/peregrine chart ruler → ASC archetype treated as CONDITIONAL
- Debilitated planets → shadows named directly, not softened
- The gap between ASC mask and dominant planet = central narrative tension

## Summary

| Component | Count |
|-----------|-------|
| Tools | 24+ static + dynamic |
| Resources | 13 |
| Prompts | 11 |
| Knowledge chunks | 6,500+ |
| Source texts | 26 |
| Embedding model | text-embedding-3-large (3072 dims) |

## Tools (24+)

### Chart Reading
| Tool | Description |
|------|-------------|
| `chart_reading` | **Main tool.** Full computation + knowledge graph + narrative synthesis. 3-axis: type × framework × size. |
| `full_chart_computation` | Raw computation only (all data, no narrative instructions) |

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
| `astrology://natal-chart/{name}` | Personal charts (chris, lisa, robin, + others) |

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

## Elections

2026 electional astrology data from Brennan & Schaim stored in `elections/`:
- `2026-elections-summary.md` — Quick reference for all 24 election windows
- Full PDF reports for detailed analysis

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
- **ChromaDB** PersistentClient for knowledge graph (6,500+ chunks, text-embedding-3-large)
- **Neo4j** graph database for structural ontology (planets, signs, houses, aspects, authors)
- **OpenAI** text-embedding-3-large (3072 dims) for embeddings
- **King Wen sequence** for I Ching hexagram mapping (verified correct)
- Auto-discovers additional sweph endpoints via `/api-info` at startup

## Roadmap

- [ ] Evolutionary Astrology framework (Pluto polarity, nodal story, skipped steps)
- [ ] Archetypal Astrology framework (Tarnas, outer planet cycles)
- [ ] Framework-specific computation adjuncts (extra data per framework)
- [ ] "What the chart wants" auto-detection (recommend framework from chart signatures)
- [ ] Interactive Telegram flow (inline buttons for chart → type → framework → size)
- [ ] Transit query language (drill into specific transit periods)
- [ ] Full transit cycle tracking (planetary returns, progressions)
