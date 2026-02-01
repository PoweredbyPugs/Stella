#!/usr/bin/env python3
"""
Selene — Unified Astrology MCP Server

The Moon of Gnosis. Reflects the light of Helios (sweph API) through
the knowledge graph, I Ching divination, and interpretive layers.

Components:
  - Helios bridge: 14+ ephemeris tools via sweph REST API
  - Knowledge graph: 6,160+ chunks across 25 astrological texts
  - I Ching: Hexagram casting with King Wen sequence
  - Resources: Zodiac, planets, houses, aspects, personal charts
  - Prompts: 11 interpretation templates
"""

import os
import sys
import json
import random
import asyncio
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx
import chromadb
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

# ── Config ──
SELENE_DIR = Path(__file__).parent
CHROMA_DIR = SELENE_DIR.parent / "astro-knowledge" / "chromadb_store"
COLLECTION_NAME = "astro_knowledge"
EMBEDDING_MODEL = "text-embedding-3-small"
SWEPH_API_BASE = os.environ.get("SWEPH_API_BASE", "http://baratie:3000")
TRUST_LABELS = {1: "PRIMARY", 2: "BRIDGE", 3: "REFERENCE", 4: "PERIPHERAL"}

# ── Init ──
mcp = FastMCP("selene")


# ── Helpers ──

class NoOpEmbedding(chromadb.EmbeddingFunction):
    def __call__(self, input):
        return [[0.0] * 1536 for _ in input]


_openai_client = None
def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client:
        return _openai_client
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        config_path = Path.home() / ".clawdbot" / "clawdbot.json"
        if config_path.exists():
            config = json.loads(config_path.read_text())
            skills = config.get("skills", {}).get("entries", {})
            for skill_name in ["openai-image-gen", "openai-whisper-api"]:
                api_key = skills.get(skill_name, {}).get("apiKey")
                if api_key:
                    break
    if not api_key:
        raise ValueError("No OPENAI_API_KEY found")
    _openai_client = OpenAI(api_key=api_key)
    return _openai_client


_collection = None
def get_collection():
    global _collection
    if _collection:
        return _collection
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    _collection = chroma.get_collection(COLLECTION_NAME, embedding_function=NoOpEmbedding())
    return _collection


def embed_query(text: str) -> list[float]:
    client = get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return response.data[0].embedding


def load_json(filename: str):
    filepath = SELENE_DIR / filename
    if filepath.exists():
        return json.loads(filepath.read_text())
    return None


async def call_sweph(endpoint: str, method: str = "GET", body: dict = None) -> dict:
    """Call the Helios (sweph) REST API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{SWEPH_API_BASE}{endpoint}"
        if method == "POST":
            resp = await client.post(url, json=body)
        else:
            resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 1: HELIOS BRIDGE — Ephemeris Tools
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_current_moon() -> str:
    """Get the current moon phase and sign."""
    data = await call_sweph("/moon-now")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_planet_positions() -> str:
    """Get current positions of all planets."""
    data = await call_sweph("/planets-now")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_planet_aspects() -> str:
    """Get current aspects between planets."""
    data = await call_sweph("/aspects-now")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_weekly_moon_phase() -> str:
    """Get this week's major moon phase."""
    data = await call_sweph("/weekly-major-phase")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_natal_chart(
    year: int,
    month: int,
    day: int,
    latitude: float,
    longitude: float,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> str:
    """Calculate a comprehensive natal chart for a specific birth date, time, and location.
    Returns full chart with planets, asteroids, houses, angles, aspects with applying/separating indicators, and calculated points (Part of Fortune/Spirit)."""
    params = urlencode({
        "year": year, "month": month, "day": day,
        "hour": hour, "minute": minute, "second": second,
        "latitude": latitude, "longitude": longitude,
    })
    data = await call_sweph(f"/natal-chart?{params}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def generate_chart(
    name: str,
    year: int,
    month: int,
    day: int,
    latitude: float,
    longitude: float,
    hour: int = 12,
    minute: int = 0,
    timezone: Optional[str] = None,
    save: bool = True,
) -> str:
    """Generate a comprehensive natal chart and optionally save it. Returns full chart with planets, houses, dignities, sect, depositors, lots."""
    body = {
        "name": name, "year": year, "month": month, "day": day,
        "hour": hour, "minute": minute,
        "latitude": latitude, "longitude": longitude,
    }
    if timezone:
        body["timezone"] = timezone
    if save is not None:
        body["save"] = save
    data = await call_sweph("/generate-chart", method="POST", body=body)
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_chart(name: str) -> str:
    """Retrieve a stored natal chart by name."""
    data = await call_sweph(f"/chart/{name}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def list_charts() -> str:
    """List all stored natal charts."""
    data = await call_sweph("/charts")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_profections(name: str, age: Optional[int] = None) -> str:
    """Get annual profections for a stored chart, including lord of year and 12-year timeline."""
    query = f"?age={age}" if age is not None else ""
    data = await call_sweph(f"/profections/{name}{query}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_zodiacal_releasing(
    name: str,
    lot: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Get Zodiacal Releasing L1 and L2 periods for a stored chart. Includes peak periods and loosing of the bond.
    
    Args:
        name: Name of the stored chart
        lot: 'spirit' or 'fortune'
        date: Target date YYYY-MM-DD
    """
    parts = []
    if lot:
        parts.append(f"lot={lot}")
    if date:
        parts.append(f"date={date}")
    query = f"?{'&'.join(parts)}" if parts else ""
    data = await call_sweph(f"/zr/{name}{query}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_transits_now(
    name: str,
    major: Optional[bool] = None,
    orb: Optional[float] = None,
) -> str:
    """Get all current transits to a stored natal chart, sorted by orb. Includes profection context."""
    parts = []
    if major:
        parts.append("major=true")
    if orb is not None:
        parts.append(f"orb={orb}")
    query = f"?{'&'.join(parts)}" if parts else ""
    data = await call_sweph(f"/transits/{name}/now{query}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_transit_summary(name: str) -> str:
    """Get high-level summary of major outer planet transits with timing context (profections + ZR)."""
    data = await call_sweph(f"/transits/{name}/summary")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_dignity_score(
    planet: str,
    sign: Optional[str] = None,
    degree: Optional[float] = None,
    longitude: Optional[float] = None,
    isDaySect: Optional[bool] = None,
) -> str:
    """Calculate essential dignity score for any planet at any position. Returns all 5 dignities plus debilities."""
    parts = [f"planet={planet}"]
    if longitude is not None:
        parts.append(f"longitude={longitude}")
    else:
        if sign:
            parts.append(f"sign={sign}")
        if degree is not None:
            parts.append(f"degree={degree}")
    if isDaySect is not None:
        parts.append(f"isDaySect={'true' if isDaySect else 'false'}")
    data = await call_sweph(f"/dignity-score?{'&'.join(parts)}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_current_dignities(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> str:
    """Get dignity scores for all planets at their current positions, including sect status."""
    parts = []
    if lat is not None:
        parts.append(f"lat={lat}")
    if lon is not None:
        parts.append(f"lon={lon}")
    query = f"?{'&'.join(parts)}" if parts else ""
    data = await call_sweph(f"/current-dignities{query}")
    return json.dumps(data, indent=2)


# Auto-discover additional sweph endpoints
async def discover_and_register():
    """Discover additional endpoints from the sweph API and register them."""
    core_endpoints = {
        "/moon-now", "/planets-now", "/aspects-now", "/weekly-major-phase",
        "/natal-chart", "/generate-chart", "/charts", "/dignity-score",
        "/current-dignities",
    }
    core_prefixes = ["/chart/", "/profections/", "/zr/", "/transits/"]
    
    try:
        data = await call_sweph("/api-info")
        endpoints = data.get("endpoints", [])
        for ep in endpoints:
            path = ep.get("path", "")
            if not path or path in core_endpoints:
                continue
            if any(path.startswith(p) for p in core_prefixes):
                continue
            if ":" in path:
                continue
                
            tool_name = f"sweph_{path.strip('/').replace('/', '_').replace('-', '_')}"
            description = ep.get("description", f"Access the {path} endpoint")
            
            # Register as a dynamic tool via the function approach
            # (FastMCP doesn't support dynamic registration easily, 
            #  so we'll just note these are available via the API)
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 2: KNOWLEDGE GRAPH — Search & Interpretation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def knowledge_search(
    query: str,
    layer: Optional[str] = None,
    trust_tier: Optional[int] = None,
    planet: Optional[str] = None,
    sign: Optional[str] = None,
    house: Optional[str] = None,
    aspect: Optional[str] = None,
    technique: Optional[str] = None,
    tradition: Optional[str] = None,
    author: Optional[str] = None,
    top: int = 5,
) -> str:
    """Search the astrology knowledge graph with natural language.
    
    Searches 6,160+ chunks from 25 curated astrological texts (Brennan, Tarnas, Lehman, Sasportas, planet PDFs, ZR materials, Gnostic I Ching).
    
    Filters:
    - layer: technical | psychological | archetypal | philosophical | reference
    - trust_tier: 1 (primary) | 2 (bridge) | 3 (reference) | 4 (peripheral)
    - planet: sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto, north_node, south_node, lot_fortune, lot_spirit
    - sign: aries through pisces
    - house: 1-12
    - aspect: conjunction, sextile, square, trine, opposition
    - technique: essential_dignities, sect, zodiacal_releasing, profections, lots, transits, synastry, houses
    - tradition: hellenistic, modern, evolutionary, archetypal, jungian, iching, stoic
    - author: filter by author name
    - top: number of results (default 5)
    """
    collection = get_collection()
    
    # Enhance query with entity context
    query_enhanced = query
    if planet:
        query_enhanced = f"{planet} {query_enhanced}"
    if sign:
        query_enhanced = f"{query_enhanced} {sign}"
    if house:
        query_enhanced = f"{query_enhanced} {house}th house"
    if aspect:
        query_enhanced = f"{query_enhanced} {aspect}"
    if technique:
        query_enhanced = f"{query_enhanced} {technique.replace('_', ' ')}"

    query_embedding = embed_query(query_enhanced)

    # Metadata filters (exact match only)
    conditions = []
    if layer:
        conditions.append({"layer": layer})
    if trust_tier:
        conditions.append({"trust_tier": trust_tier})
    if tradition:
        conditions.append({"tradition": tradition})
    if author:
        conditions.append({"source_author": author})

    where_filter = None
    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top,
        where=where_filter,
    )

    if not results["documents"][0]:
        return "No results found."

    output_parts = [f'Results for: "{query}" ({collection.count()} chunks searched)\n']

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        tier = meta.get("trust_tier", 4)
        tier_label = TRUST_LABELS.get(tier, "?")
        relevance = round(1 - dist, 3)

        header = (
            f"[{i+1}] [{meta.get('layer', '?').upper()}] [{tier_label}] "
            f"— {meta.get('source_author', '?')}: {meta.get('source_title', '?')}"
        )

        tags = []
        for key in ["planets", "signs", "houses", "aspects", "techniques"]:
            val = meta.get(key, "")
            if val:
                tags.append(f"{key}={val}")

        text = doc[:800] + "..." if len(doc) > 800 else doc

        output_parts.append(f"{header}\nRelevance: {relevance}")
        if tags:
            output_parts.append(f"Tags: {', '.join(tags)}")
        output_parts.append(f"\n{text}\n")
        output_parts.append("─" * 60)

    return "\n".join(output_parts)


@mcp.tool()
def knowledge_search_json(
    query: str,
    layer: Optional[str] = None,
    trust_tier: Optional[int] = None,
    planet: Optional[str] = None,
    sign: Optional[str] = None,
    house: Optional[str] = None,
    technique: Optional[str] = None,
    top: int = 5,
) -> str:
    """Search the knowledge graph and return structured JSON results. Same parameters as knowledge_search()."""
    collection = get_collection()

    query_enhanced = query
    if planet:
        query_enhanced = f"{planet} {query_enhanced}"
    if sign:
        query_enhanced = f"{query_enhanced} {sign}"
    if house:
        query_enhanced = f"{query_enhanced} {house}th house"
    if technique:
        query_enhanced = f"{query_enhanced} {technique.replace('_', ' ')}"

    query_embedding = embed_query(query_enhanced)

    conditions = []
    if layer:
        conditions.append({"layer": layer})
    if trust_tier:
        conditions.append({"trust_tier": trust_tier})

    where_filter = None
    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top,
        where=where_filter,
    )

    output = []
    if results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "text": doc,
                "relevance": round(1 - dist, 4),
                "author": meta.get("source_author"),
                "title": meta.get("source_title"),
                "layer": meta.get("layer"),
                "trust_tier": meta.get("trust_tier"),
                "planets": [p for p in meta.get("planets", "").split(",") if p],
                "signs": [s for s in meta.get("signs", "").split(",") if s],
                "techniques": [t for t in meta.get("techniques", "").split(",") if t],
            })

    return json.dumps(output, indent=2)


@mcp.tool()
def knowledge_stats() -> str:
    """Get statistics about the knowledge graph collection."""
    collection = get_collection()
    count = collection.count()
    sample = collection.get(limit=min(count, 1000), include=["metadatas"])

    sources, layers, tiers = {}, {}, {}
    for meta in sample["metadatas"]:
        author = meta.get("source_author", "unknown")
        sources[author] = sources.get(author, 0) + 1
        layer = meta.get("layer", "unknown")
        layers[layer] = layers.get(layer, 0) + 1
        tier = TRUST_LABELS.get(meta.get("trust_tier", 4), "?")
        tiers[tier] = tiers.get(tier, 0) + 1

    lines = [f"Astrology Knowledge Graph — {count} chunks\n"]
    lines.append("By Layer:")
    for l, c in sorted(layers.items(), key=lambda x: -x[1]):
        lines.append(f"  {l}: {c}")
    lines.append("\nBy Trust Tier:")
    for t, c in sorted(tiers.items(), key=lambda x: -x[1]):
        lines.append(f"  {t}: {c}")
    lines.append("\nBy Author:")
    for a, c in sorted(sources.items(), key=lambda x: -x[1]):
        lines.append(f"  {a}: {c}")
    return "\n".join(lines)


@mcp.tool()
def interpret_placement(
    planet: str,
    sign: Optional[str] = None,
    house: Optional[str] = None,
    aspect_planet: Optional[str] = None,
    aspect_type: Optional[str] = None,
) -> str:
    """Get a multi-layered interpretation for a specific astrological placement.
    
    Automatically queries across all interpretive layers:
    - Technical (Hellenistic): dignity, sect, condition
    - Psychological: depth psychology perspective
    - Reference: practical delineation from multiple authors
    - Archetypal: Jungian/mythological perspective
    """
    collection = get_collection()

    query_parts = [planet.title()]
    if sign:
        query_parts.append(f"in {sign.title()}")
    if house:
        query_parts.append(f"in the {house}th house")
    if aspect_planet and aspect_type:
        query_parts.append(f"{aspect_type} {aspect_planet.title()}")

    query_text = " ".join(query_parts)
    query_embedding = embed_query(query_text)

    layers_to_query = ["technical", "psychological", "reference", "archetypal"]
    output_parts = [f"Multi-layered interpretation: {query_text}\n"]

    for layer_name in layers_to_query:
        where = {"layer": layer_name}
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                where=where,
            )
            if results["documents"][0]:
                output_parts.append(f"\n{'═' * 40}")
                output_parts.append(f"[{layer_name.upper()}]")
                output_parts.append(f"{'═' * 40}")
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    author = meta.get("source_author", "?")
                    text = doc[:600] + "..." if len(doc) > 600 else doc
                    output_parts.append(f"\n— {author}:")
                    output_parts.append(text)
        except Exception:
            pass

    return "\n".join(output_parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 3: I CHING — Divination
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# King Wen sequence: [upper_trigram][lower_trigram] → hexagram number
KING_WEN = [
    [1, 44, 33, 12, 20, 23, 35, 14],   # Heaven
    [9, 5, 26, 11, 10, 58, 38, 54],     # Lake
    [13, 49, 30, 55, 37, 63, 22, 36],   # Fire
    [25, 17, 21, 51, 42, 3, 27, 24],    # Thunder
    [6, 47, 64, 40, 59, 29, 4, 7],      # Water
    [53, 39, 52, 15, 62, 56, 31, 33],   # Mountain
    [45, 28, 48, 46, 32, 50, 57, 48],   # Wind
    [2, 24, 7, 19, 15, 36, 46, 11],     # Earth
]

TRIGRAM_MAP = [2, 5, 3, 4, 7, 0, 6, 1]  # binary → traditional order


def _cast_coin_line():
    coins = [random.choice([2, 3]) for _ in range(3)]
    total = sum(coins)
    return {6: (0, True), 7: (1, False), 8: (0, False), 9: (1, True)}[total]


def _cast_yarrow_line():
    r = random.random()
    if r < 0.0625:
        return (0, True)    # Old Yin
    elif r < 0.3125:
        return (1, False)   # Young Yang
    elif r < 0.6875:
        return (0, False)   # Young Yin
    else:
        return (1, True)    # Old Yang


def _lines_to_trigram(lines):
    value = lines[0] + (lines[1] * 2) + (lines[2] * 4)
    return TRIGRAM_MAP[value]


def _hexagram_number(lines):
    lower = _lines_to_trigram(lines[:3])
    upper = _lines_to_trigram(lines[3:])
    return KING_WEN[upper][lower]


@mcp.tool()
def cast_hexagram(
    question: str,
    method: str = "coins",
) -> str:
    """Cast an I Ching hexagram for divination.
    
    Uses traditional casting methods (coins or yarrow stalks) with authentic
    King Wen sequence. Returns primary hexagram, changing lines, and 
    transformed hexagram with full interpretive text.
    
    Args:
        question: The question for divination
        method: 'coins' (default) or 'yarrow'
    """
    hexagrams = load_json("hexagrams.json")
    cast_fn = _cast_yarrow_line if method == "yarrow" else _cast_coin_line
    
    lines = []
    changing = []
    for i in range(6):
        value, is_changing = cast_fn()
        lines.append(value)
        if is_changing:
            changing.append(i)
    
    number = _hexagram_number(lines)
    
    transformed = None
    transformed_number = None
    if changing:
        t_lines = list(lines)
        for idx in changing:
            t_lines[idx] = 1 - t_lines[idx]
        transformed_number = _hexagram_number(t_lines)
    
    # Build response
    result = {
        "question": question,
        "method": method,
        "primary": {
            "number": number,
            "lines": lines,
            "line_types": [
                "old yin (changing)" if lines[i] == 0 and i in changing
                else "old yang (changing)" if lines[i] == 1 and i in changing
                else "young yin" if lines[i] == 0
                else "young yang"
                for i in range(6)
            ],
        },
        "changing_lines": [i + 1 for i in changing],
    }
    
    # Add hexagram data if available
    if hexagrams:
        hex_data = hexagrams.get(str(number))
        if hex_data:
            result["primary"]["name"] = hex_data.get("name", f"Hexagram {number}")
            result["primary"]["meaning"] = hex_data.get("meaning", "")
            result["primary"]["judgment"] = hex_data.get("judgment", "")
            result["primary"]["image"] = hex_data.get("image", "")
            
            # Add changing line texts
            if changing and "lines" in hex_data:
                result["changing_line_texts"] = {}
                for idx in changing:
                    line_key = str(idx + 1)
                    if line_key in hex_data["lines"]:
                        result["changing_line_texts"][f"line_{idx+1}"] = hex_data["lines"][line_key]
        
        if transformed_number:
            result["transformed"] = {"number": transformed_number}
            t_data = hexagrams.get(str(transformed_number))
            if t_data:
                result["transformed"]["name"] = t_data.get("name", f"Hexagram {transformed_number}")
                result["transformed"]["meaning"] = t_data.get("meaning", "")
    
    return json.dumps(result, indent=2)


@mcp.tool()
def retrieve_wisdom(
    query: str,
    top_k: int = 3,
) -> str:
    """Search the Gnostic Book of Changes and I Ching wisdom texts.
    
    Searches the knowledge graph filtered to I Ching tradition for
    relevant passages from the Gnostic Book of Changes.
    """
    collection = get_collection()
    query_embedding = embed_query(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"tradition": "iching"},
    )
    
    if not results["documents"][0]:
        return "No wisdom passages found."
    
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text": doc[:1000],
            "relevance": round(1 - dist, 3),
            "source": meta.get("source_title", "Unknown"),
        })
    
    return json.dumps(output, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 4: RESOURCES — Static Astrological Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.resource("astrology://zodiac-signs")
def resource_zodiac_signs() -> str:
    """Complete zodiac sign reference with elements, qualities, rulers, archetypes, and psychological functions."""
    data = load_json("zodiac_data.json")
    return json.dumps(data, indent=2) if data else "Zodiac data not found"


@mcp.resource("astrology://planets")
def resource_planets() -> str:
    """Complete planetary reference with dignities, archetypes, psychological functions, and traditional/modern meanings."""
    data = load_json("planets_data.json")
    return json.dumps(data, indent=2) if data else "Planets data not found"


@mcp.resource("astrology://houses")
def resource_houses() -> str:
    """Complete house reference with themes, natural rulers, psychological domains, and traditional meanings."""
    data = load_json("houses_data.json")
    return json.dumps(data, indent=2) if data else "Houses data not found"


@mcp.resource("astrology://aspects")
def resource_aspects() -> str:
    """Complete aspects reference with orbs, nature, keywords, and interpretive frameworks."""
    data = load_json("aspects_data.json")
    return json.dumps(data, indent=2) if data else "Aspects data not found"


@mcp.resource("astrology://traditional-astrology")
def resource_traditional_astrology() -> str:
    """Traditional astrology reference covering Hellenistic techniques, dignities, sect, and time lord systems."""
    data = load_json("traditional_astrology_data.json")
    return json.dumps(data, indent=2) if data else "Traditional astrology data not found"


@mcp.resource("astrology://natal-chart")
def resource_natal_chart() -> str:
    """Chandra's natal chart — complete chart data with planets, houses, aspects, dignities, and calculated points."""
    data = load_json("natal_chart_chandra.json")
    return json.dumps(data, indent=2) if data else "Natal chart data not found"


# Personal chart resources — these pull from the sweph API
CHART_NAMES = ["chris", "katy", "micheal", "betsy", "megan", "kelsea", "lisa"]

for _name in CHART_NAMES:
    def _make_chart_resource(chart_name):
        @mcp.resource(f"astrology://natal-chart/{chart_name}")
        async def _resource() -> str:
            f"""Natal chart for {chart_name.title()}."""
            try:
                data = await call_sweph(f"/chart/{chart_name}")
                return json.dumps(data, indent=2)
            except Exception as e:
                return f"Error loading chart for {chart_name}: {e}"
        _resource.__name__ = f"resource_chart_{chart_name}"
        _resource.__doc__ = f"Natal chart for {chart_name.title()}."
        return _resource
    _make_chart_resource(_name)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 5: PROMPTS — Interpretation Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.prompt()
def narrative_weekly_forecast() -> str:
    """Create a narrative weekly astrological forecast that weaves the client's natal chart with current transits, expressed as an unfolding story."""
    return """Create a weekly astrological forecast in narrative form for [Date Range]. 
The forecast should read like a sacred beautifully written text, weaving the client's natal chart with current transits. 
Do not list predictions—frame them as destiny unfolding.

## Structural Framework

### Title Format
"[Poetic Theme]: [Specific Personal Journey Reference]"

### Section Architecture
1. **Opening Movement** — Begin with the week's most powerful transit, connect to natal placement
2. **The Major Transit Spotlight** — Deep dive into headline transit with exact degrees and orbs
3. **The Supporting Cast** — 2-3 secondary transits building the weekly "plot"
4. **The Natal Chart Callback** — Natal configurations activated this week
5. **The Sacred Geometry** — Aspect patterns (trines, T-squares, etc.)
6. **The Oracle** — Italicized cosmic guidance synthesizing everything

Use sacred/mystical vocabulary. Personify planets. Include exact degrees, natal placements, orbs, house activations, rulers, timing, and larger cycle context. Favor poetic invitation over prediction."""


@mcp.prompt()
def interpret_traditional_chart() -> str:
    """Get a traditional astrological interpretation based on natal chart."""
    return "Please analyze my natal chart from the natal-chart resource using traditional astrological principles from the traditional-astrology resource. Focus on house rulerships in the style of Chris Brennan, with special attention to:\n\n1. The ruler of my Ascendant and its placement\n2. Planetary sect and dignity\n3. Annual profections for my current age\n4. Time lord techniques\n5. Holistic synthesis in the style of Richard Tarnas\n\nPlease provide a thorough interpretation focusing on life direction, career, relationships, and spiritual development."


@mcp.prompt()
def hellenistic_chart_analysis() -> str:
    """Get a Hellenistic astrology analysis of natal chart."""
    return "Please analyze my natal chart from the natal-chart resource using Hellenistic astrological techniques from the traditional-astrology resource. Focus on:\n\n1. Whole sign house placements\n2. The Ascendant ruler's condition by sign, house, dignity, and aspects\n3. Sect analysis (day/night distinction)\n4. Planetary joys and triplicities\n5. Lots/Arabic Parts (especially Fortune and Spirit)\n6. Time lord systems (annual profections and zodiacal releasing)\n\nProvide a comprehensive reading in the style of Chris Brennan's approach to Hellenistic astrology."


@mcp.prompt()
def archetypal_chart_analysis() -> str:
    """Get an archetypal astrology analysis of natal chart."""
    return "Please analyze my natal chart from the natal-chart resource using the archetypal astrology approach of Richard Tarnas from the traditional-astrology resource. Focus on:\n\n1. The major planetary archetypes and their complex interactions\n2. Significant aspect patterns and their archetypal meanings\n3. Current transits and their archetypal significance\n4. How these archetypal patterns manifest in personal life and consciousness\n5. The deeper philosophical and spiritual implications\n\nProvide a rich, nuanced interpretation capturing the multivalent symbolism and psychological depth of the Tarnas approach."


@mcp.prompt()
def profection_year_analysis() -> str:
    """Get an analysis of your current annual profection."""
    return "Based on my natal chart and traditional techniques, analyze my current annual profection year. Include:\n\n1. The activated house and its lord\n2. The condition of that lord in my natal chart\n3. Current transits to that lord and house\n4. Key themes and focus areas for this profection year\n5. Practical guidance for working with this year's energies\n\nUse the Chris Brennan approach to annual profections."


@mcp.prompt()
def traditional_transits_analysis() -> str:
    """Get a traditional analysis of current transits to natal chart."""
    return "Use the get-planet-positions and get-planet-aspects tools to compare current planetary positions with my natal chart. Then provide a traditional analysis focusing on:\n\n1. Transits to my Ascendant ruler and its significance\n2. Traditional interpretations of outer planet transits to natal positions\n3. Current transits through my whole sign houses\n4. The relationship between current transits and my annual profection\n5. Practical timing insights based on traditional techniques\n\nBlend traditional timing techniques with practical guidance."


@mcp.prompt()
def interpret_natal_chart() -> str:
    """Get a personalized natal chart interpretation with focus on house rulership."""
    return "Analyze my natal chart with a focus on traditional house rulership. For each planet:\n\n1. Its condition by sign placement (dignity, debility, mutual reception)\n2. The house(s) it rules and how its condition affects those life areas\n3. Its house placement and how it expresses its energy there\n4. Important aspects and how they modify its expression\n\nPay special attention to the ruler of the Ascendant as chart ruler. Include mutual receptions and conclude with key strengths, challenges, and potential life direction."


@mcp.prompt()
def analyze_current_transits() -> str:
    """Get analysis of current transits to natal chart with emphasis on house rulership."""
    return "Use get-planet-positions and get-planet-aspects to compare current positions with my natal chart. Focus on:\n\n1. Transiting planets through natal houses and activated life areas\n2. Transits to natal planets, especially rulers of important houses\n3. How transiting planets' conditions affect the houses they rule in my natal chart\n4. Temporary mutual receptions between transiting planets\n\nIdentify the most significant current transits and provide practical guidance."


@mcp.prompt()
def interpret_planets() -> str:
    """Interpret current planetary positions with house rulership analysis."""
    return "Use get-planet-positions and get-planet-aspects to analyze current positions. Then:\n\n1. Each planet's current condition (sign dignity/debility, retrograde)\n2. Which houses each planet rules in a natural chart and how its condition affects those areas\n3. Current mutual receptions and their significance\n4. Most significant forming aspects and how they modify planetary expressions\n5. Which life areas are most supported or challenged now\n\nProvide practical guidance for different life domains."


@mcp.prompt()
def moon_energy() -> str:
    """Explain the current moon phase and its influence with house rulership context."""
    return "Use get-current-moon to check the current moon phase and sign. Then:\n\n1. Current lunar phase and its meaning in the lunar cycle\n2. Moon's sign placement, dignity/debility, and any mutual receptions\n3. Cancer (Moon's house) in a natural chart — how Moon's condition affects those matters\n4. The house ruled by Moon's current sign — how Moon's presence affects those matters\n5. Supported or challenged activities during this lunar phase/sign\n6. Practical guidance for working with today's lunar energy"


@mcp.prompt()
def weekly_planning() -> str:
    """Create a comprehensive weekly plan based on astrological influences including house rulership."""
    return """Create a weekly astrological planning guide using:

1. get-weekly-moon-phase for this week's major moon phase
2. void-of-course-moons for VOC periods
3. planetary-ingresses?timeframe=week for sign changes
4. planetary-stations?timeframe=week for retrograde/direct stations
5. important-transits?timeframe=week for significant aspects

For each day provide:
- Moon sign, phase, dignity status, and affected life areas
- VOC periods and what to avoid
- Planets changing signs and how it affects their ruled houses
- Planets changing direction and impact on ruled houses
- Major aspects and affected houses/life areas
- Practical recommendations

Include which life areas are most activated this week based on planetary ruler activity."""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    mcp.run(transport="stdio")
