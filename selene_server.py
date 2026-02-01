#!/usr/bin/env python3
"""
Selene — Unified Astrology & Divination MCP Server

The Moon of Gnosis. Reflects the light of Helios (sweph API) through
the knowledge graph, I Ching divination, and interpretive layers.

Components:
  - Helios bridge: 14+ ephemeris tools via sweph REST API
  - Knowledge graph: 6,160+ chunks across 25 astrological texts
  - I Ching: Hexagram casting with King Wen sequence
  - Resources: Zodiac, planets, houses, aspects, personal charts
  - Prompts: Interpretation templates
"""

import os
import sys
import json
import random
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx
import chromadb
from openai import OpenAI
from neo4j import GraphDatabase
from mcp.server.fastmcp import FastMCP

# ── Config ──
SELENE_DIR = Path(__file__).parent
CHROMA_DIR = SELENE_DIR.parent / "astro-knowledge" / "chromadb_store"
COLLECTION_NAME = "astro_knowledge"
EMBEDDING_MODEL = "text-embedding-3-small"
SWEPH_API_BASE = os.environ.get("SWEPH_API_BASE", "http://baratie:3000")
TRUST_LABELS = {1: "PRIMARY", 2: "BRIDGE", 3: "REFERENCE", 4: "PERIPHERAL"}

# Neo4j
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "selene_gnosis")

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


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single API call. Much faster than one-by-one."""
    if not texts:
        return []
    client = get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


# ── Neo4j ──

_neo4j_driver = None


def get_neo4j():
    """Get or create Neo4j driver singleton."""
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return _neo4j_driver


def neo4j_query(cypher: str, **params) -> list[dict]:
    """Run a Cypher query and return results as list of dicts."""
    driver = get_neo4j()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return [dict(record) for record in result]


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

    Returns full chart with planets, asteroids, houses, angles, aspects with
    applying/separating indicators, and calculated points (Part of Fortune/Spirit).

    Args:
        year: Birth year (e.g. 1990)
        month: Birth month (1-12)
        day: Birth day (1-31)
        hour: Birth hour 24h format (0-23), default 0
        minute: Birth minute (0-59), default 0
        second: Birth second (0-59), default 0
        latitude: Birth location latitude (e.g. 40.7128 for New York)
        longitude: Birth location longitude (e.g. -74.0060 for New York)
    """
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
    """Generate a comprehensive natal chart and optionally save it.

    Returns full chart with planets, houses, dignities, sect, depositors, lots.

    Args:
        name: Name for the chart (used for storage and retrieval)
        year: Birth year (e.g. 1990)
        month: Birth month (1-12)
        day: Birth day (1-31)
        hour: Birth hour 24h format (0-23), default 12
        minute: Birth minute (0-59), default 0
        latitude: Birth location latitude
        longitude: Birth location longitude
        timezone: Timezone string (e.g. 'America/New_York')
        save: Whether to save the chart for future use (default True)
    """
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
    """Retrieve a stored natal chart by name.

    Args:
        name: Name of the stored chart
    """
    data = await call_sweph(f"/chart/{name}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def list_charts() -> str:
    """List all stored natal charts."""
    data = await call_sweph("/charts")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_profections(name: str, age: Optional[int] = None) -> str:
    """Get annual profections for a stored chart, including lord of year and 12-year timeline.

    Args:
        name: Name of the stored chart
        age: Age to calculate for (optional, defaults to current age)
    """
    query = f"?age={age}" if age is not None else ""
    data = await call_sweph(f"/profections/{name}{query}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_zodiacal_releasing(
    name: str,
    lot: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Get Zodiacal Releasing L1 and L2 periods for a stored chart.

    Includes peak periods and loosing of the bond.

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
    """Get all current transits to a stored natal chart, sorted by orb.

    Includes profection context.

    Args:
        name: Name of the stored chart
        major: Only major aspects
        orb: Max orb in degrees
    """
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
    """Get high-level summary of major outer planet transits with timing context (profections + ZR).

    Args:
        name: Name of the stored chart
    """
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
    """Calculate essential dignity score for any planet at any position.

    Returns all 5 dignities plus debilities.

    Args:
        planet: Planet name (e.g. 'mars', 'venus')
        sign: Zodiac sign (if not using longitude)
        degree: Degree 0-30 within sign
        longitude: Ecliptic longitude 0-360 (alternative to sign+degree)
        isDaySect: Is this a day chart?
    """
    parts = [f"planet={planet}"]
    if longitude is not None:
        parts.append(f"longitude={longitude}")
    else:
        if sign:
            parts.append(f"sign={sign}")
            # API requires both sign AND degree; default to 15 (middle of sign)
            parts.append(f"degree={degree if degree is not None else 15}")
        elif degree is not None:
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
    """Get dignity scores for all planets at their current positions, including sect status.

    Args:
        lat: Latitude (for sect calculation)
        lon: Longitude (for sect calculation)
    """
    parts = []
    if lat is not None:
        parts.append(f"lat={lat}")
    if lon is not None:
        parts.append(f"lon={lon}")
    query = f"?{'&'.join(parts)}" if parts else ""
    data = await call_sweph(f"/current-dignities{query}")
    return json.dumps(data, indent=2)


# ── Auto-discover additional sweph endpoints ──

async def discover_and_register():
    """Discover additional endpoints from the sweph API and register them."""
    core_endpoints = {
        "/moon-now", "/planets-now", "/aspects-now", "/weekly-major-phase",
        "/natal-chart", "/generate-chart", "/charts", "/dignity-score",
        "/current-dignities", "/api-info",
    }
    core_prefixes = ["/chart/", "/profections/", "/zr/", "/transits/"]

    try:
        data = await call_sweph("/api-info")
        endpoints = data.get("endpoints", []) if isinstance(data, dict) else []
        registered = 0

        for ep in endpoints:
            if not isinstance(ep, dict):
                continue
            path = ep.get("path", "")
            if not path or path in core_endpoints:
                continue
            if any(path.startswith(p) for p in core_prefixes):
                continue
            # Skip parameterized paths like /chart/:name
            if ":" in path:
                continue

            tool_name = f"sweph_{path.strip('/').replace('/', '_').replace('-', '_')}"
            description = ep.get("description", f"Access the {path} sweph endpoint")

            # Create closure with captured variables
            def _make_tool(p, d):
                async def _dynamic_tool() -> str:
                    result = await call_sweph(p)
                    return json.dumps(result, indent=2)
                _dynamic_tool.__name__ = tool_name
                _dynamic_tool.__doc__ = d
                return _dynamic_tool

            mcp.tool()(_make_tool(path, description))
            registered += 1
            print(f"[selene] Registered: {tool_name} → {path}", file=sys.stderr)

        print(f"[selene] {registered} dynamic endpoints registered", file=sys.stderr)
    except Exception as e:
        print(f"[selene] Endpoint discovery skipped: {e}", file=sys.stderr)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 1b: CHART STORAGE — Selene-managed chart persistence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHARTS_DIR = SELENE_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)


def _load_local_chart(name: str) -> dict | None:
    """Load a chart from Selene's local storage."""
    path = CHARTS_DIR / f"{name.lower()}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_local_chart(name: str, data: dict):
    """Save a chart to Selene's local storage."""
    path = CHARTS_DIR / f"{name.lower()}.json"
    path.write_text(json.dumps(data, indent=2))


def _list_local_charts() -> list[str]:
    """List all locally stored chart names."""
    return sorted([
        f.stem for f in CHARTS_DIR.glob("*.json")
    ])


@mcp.tool()
def store_chart(name: str, chart_data: str) -> str:
    """Store a natal chart in Selene's local storage.
    
    Use this to persist chart data that was calculated via get_natal_chart or generate_chart.
    Charts stored here survive container rebuilds and are the source of truth.
    
    Args:
        name: Name for the chart (e.g. 'buckley', 'katy')
        chart_data: JSON string of the full chart data
    """
    try:
        data = json.loads(chart_data)
    except json.JSONDecodeError:
        return "Error: chart_data must be valid JSON"
    
    _save_local_chart(name, data)
    return f"Chart '{name}' saved to Selene storage. {len(json.dumps(data))} bytes."


@mcp.tool()
def load_chart(name: str) -> str:
    """Load a natal chart from Selene's local storage.
    
    Checks Selene's local storage first, then falls back to the Helios (sweph) API.
    
    Args:
        name: Name of the chart to load
    """
    # Try local first
    data = _load_local_chart(name)
    if data:
        return json.dumps(data, indent=2)
    
    # Fall back to sweph API
    return f"Chart '{name}' not found in Selene storage. Use get_chart(name) to fetch from Helios, then store_chart() to save locally."


@mcp.tool()
def list_stored_charts() -> str:
    """List all charts stored in Selene's local storage."""
    charts = _list_local_charts()
    return json.dumps({
        "source": "selene_local",
        "count": len(charts),
        "charts": charts,
    }, indent=2)


@mcp.tool()
def delete_chart(name: str) -> str:
    """Delete a chart from Selene's local storage.
    
    Args:
        name: Name of the chart to delete
    """
    path = CHARTS_DIR / f"{name.lower()}.json"
    if path.exists():
        path.unlink()
        return f"Chart '{name}' deleted from Selene storage."
    return f"Chart '{name}' not found in Selene storage."


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

    Searches 6,160+ chunks from 25 curated astrological texts (Brennan, Tarnas,
    Lehman, Sasportas, planet PDFs, ZR materials, Gnostic I Ching).

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
    if trust_tier is not None:
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
    tradition: Optional[str] = None,
    author: Optional[str] = None,
    top: int = 5,
) -> str:
    """Search the knowledge graph and return structured JSON results.

    Same parameters as knowledge_search(). Use this for programmatic consumption.
    """
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
    if trust_tier is not None:
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
                "tradition": meta.get("tradition"),
                "planets": [p for p in meta.get("planets", "").split(",") if p],
                "signs": [s for s in meta.get("signs", "").split(",") if s],
                "houses": [h for h in meta.get("houses", "").split(",") if h],
                "aspects": [a for a in meta.get("aspects", "").split(",") if a],
                "techniques": [t for t in meta.get("techniques", "").split(",") if t],
            })

    return json.dumps(output, indent=2)


@mcp.tool()
def knowledge_stats() -> str:
    """Get statistics about the knowledge graph collection.

    Shows total chunks, distribution by layer, trust tier, author, and tradition.
    """
    collection = get_collection()
    count = collection.count()
    sample = collection.get(limit=min(count, 2000), include=["metadatas"])

    sources: dict[str, int] = {}
    layers: dict[str, int] = {}
    tiers: dict[str, int] = {}
    traditions: dict[str, int] = {}

    for meta in sample["metadatas"]:
        author = meta.get("source_author", "unknown")
        sources[author] = sources.get(author, 0) + 1
        layer = meta.get("layer", "unknown")
        layers[layer] = layers.get(layer, 0) + 1
        tier = TRUST_LABELS.get(meta.get("trust_tier", 4), "?")
        tiers[tier] = tiers.get(tier, 0) + 1
        tradition = meta.get("tradition", "unknown")
        traditions[tradition] = traditions.get(tradition, 0) + 1

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
    lines.append("\nBy Tradition:")
    for t, c in sorted(traditions.items(), key=lambda x: -x[1]):
        lines.append(f"  {t}: {c}")
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

    Args:
        planet: The planet (sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto)
        sign: Optional zodiac sign
        house: Optional house number (1-12)
        aspect_planet: Optional second planet for aspect interpretation
        aspect_type: Optional aspect type (conjunction, sextile, square, trine, opposition)
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
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                where={"layer": layer_name},
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

# King Wen sequence: KING_WEN[upper_trigram][lower_trigram] → hexagram number
# Verified against standard I Ching reference tables.
# Trigram order: 0=Qian(Heaven), 1=Dui(Lake), 2=Li(Fire), 3=Zhen(Thunder),
#                4=Xun(Wind), 5=Kan(Water), 6=Gen(Mountain), 7=Kun(Earth)
KING_WEN = [
    # Lower→  Qian  Dui   Li  Zhen  Xun   Kan  Gen   Kun
    [ 1, 10, 13, 25, 44,  6, 33, 12],   # Upper: Qian ☰ (Heaven)
    [43, 58, 49, 17, 28, 47, 31, 45],   # Upper: Dui  ☱ (Lake)
    [14, 38, 30, 21, 50, 64, 56, 35],   # Upper: Li   ☲ (Fire)
    [34, 54, 55, 51, 32, 40, 62, 16],   # Upper: Zhen ☳ (Thunder)
    [ 9, 61, 37, 42, 57, 59, 53, 20],   # Upper: Xun  ☴ (Wind)
    [ 5, 60, 63,  3, 48, 29, 39,  8],   # Upper: Kan  ☵ (Water)
    [26, 41, 22, 27, 18,  4, 52, 23],   # Upper: Gen  ☶ (Mountain)
    [11, 19, 36, 24, 46,  7, 15,  2],   # Upper: Kun  ☷ (Earth)
]

# Map binary trigram value → King Wen trigram index
# Binary = line1 + line2*2 + line3*4 (bottom-to-top)
# Trigram lines (bottom-to-top):
#   Qian(Heaven)=111=7, Dui(Lake)=110=3(?), Li(Fire)=101=5, Zhen(Thunder)=100=1
#   Xun(Wind)=011=6,    Kan(Water)=010=2,   Gen(Mountain)=001=4, Kun(Earth)=000=0
#
# Wait — Dui(Lake) bottom-to-top is yang,yang,yin → 1,1,0 → 1+2+0=3
# And Xun(Wind) bottom-to-top is yin,yang,yang → 0,1,1 → 0+2+4=6
TRIGRAM_MAP = {
    0: 7,  # 000 → Kun (Earth)       ☷
    1: 3,  # 001 → Zhen (Thunder)    ☳
    2: 5,  # 010 → Kan (Water)       ☵
    3: 1,  # 011 → Dui (Lake)        ☱
    4: 6,  # 100 → Gen (Mountain)    ☶
    5: 2,  # 101 → Li (Fire)         ☲
    6: 4,  # 110 → Xun (Wind)        ☴
    7: 0,  # 111 → Qian (Heaven)     ☰
}

TRIGRAM_NAMES = {
    0: "☰ Heaven (Qian)",
    1: "☱ Lake (Dui)",
    2: "☲ Fire (Li)",
    3: "☳ Thunder (Zhen)",
    4: "☴ Wind (Xun)",
    5: "☵ Water (Kan)",
    6: "☶ Mountain (Gen)",
    7: "☷ Earth (Kun)",
}


def _cast_coin_line():
    """Traditional three-coin method. Heads=3, Tails=2."""
    coins = [random.choice([2, 3]) for _ in range(3)]
    total = sum(coins)
    return {6: (0, True), 7: (1, False), 8: (0, False), 9: (1, True)}[total]


def _cast_yarrow_line():
    """Simplified yarrow-stalk probabilities: 6=1/16, 7=5/16, 8=7/16, 9=3/16."""
    r = random.random()
    if r < 1 / 16:
        return (0, True)     # Old Yin (6)
    elif r < 6 / 16:
        return (1, False)    # Young Yang (7)
    elif r < 13 / 16:
        return (0, False)    # Young Yin (8)
    else:
        return (1, True)     # Old Yang (9)


def _lines_to_trigram(lines):
    """Convert 3 binary lines (bottom-to-top) to a trigram index."""
    value = lines[0] + (lines[1] * 2) + (lines[2] * 4)
    return TRIGRAM_MAP[value]


def _hexagram_number(lines):
    """Given 6 binary lines (bottom-to-top), return King Wen hexagram number."""
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

    # Add trigram info
    lower_tri = _lines_to_trigram(lines[:3])
    upper_tri = _lines_to_trigram(lines[3:])
    result["primary"]["lower_trigram"] = TRIGRAM_NAMES.get(lower_tri, "?")
    result["primary"]["upper_trigram"] = TRIGRAM_NAMES.get(upper_tri, "?")

    # Add hexagram data if available
    if hexagrams:
        hex_data = hexagrams.get(str(number))
        if hex_data:
            result["primary"]["name"] = hex_data.get("name", f"Hexagram {number}")
            meaning = hex_data.get("meaning", "")
            if meaning and meaning != "The wisdom of this hexagram awaits discovery in the eternal gnosis...":
                result["primary"]["meaning"] = meaning[:2000]
            result["primary"]["concepts"] = hex_data.get("concepts", [])

            # Add changing line texts if present
            if changing and "lines" in hex_data:
                result["changing_line_texts"] = {}
                for idx in changing:
                    line_key = str(idx + 1)
                    if line_key in hex_data.get("lines", {}):
                        result["changing_line_texts"][f"line_{idx+1}"] = hex_data["lines"][line_key]

        if transformed_number:
            result["transformed"] = {"number": transformed_number}
            t_data = hexagrams.get(str(transformed_number))
            if t_data:
                result["transformed"]["name"] = t_data.get("name", f"Hexagram {transformed_number}")
                t_meaning = t_data.get("meaning", "")
                if t_meaning and t_meaning != "The wisdom of this hexagram awaits discovery in the eternal gnosis...":
                    result["transformed"]["meaning"] = t_meaning[:2000]
                result["transformed"]["concepts"] = t_data.get("concepts", [])

            # Add transformed trigram info
            t_lower = _lines_to_trigram([1 - l if i in changing else l for i, l in enumerate(lines[:3])])
            t_upper = _lines_to_trigram([1 - l if (i + 3) in changing else l for i, l in enumerate(lines[3:])])
            result["transformed"]["lower_trigram"] = TRIGRAM_NAMES.get(t_lower, "?")
            result["transformed"]["upper_trigram"] = TRIGRAM_NAMES.get(t_upper, "?")

    return json.dumps(result, indent=2)


@mcp.tool()
def retrieve_wisdom(
    query: str,
    top_k: int = 5,
) -> str:
    """Search the Gnostic Book of Changes and I Ching wisdom texts.

    Searches the knowledge graph filtered to I Ching tradition for
    relevant passages from the Gnostic Book of Changes.

    Args:
        query: Search query about I Ching concepts, hexagrams, or wisdom
        top_k: Number of results to return (default 5)
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
    """Complete zodiac sign reference."""
    data = load_json("zodiac_data.json")
    return json.dumps(data, indent=2) if data else "Zodiac data not found"


@mcp.resource("astrology://planets")
def resource_planets() -> str:
    """Complete planetary reference."""
    data = load_json("planets_data.json")
    return json.dumps(data, indent=2) if data else "Planets data not found"


@mcp.resource("astrology://houses")
def resource_houses() -> str:
    """Complete house reference."""
    data = load_json("houses_data.json")
    return json.dumps(data, indent=2) if data else "Houses data not found"


@mcp.resource("astrology://aspects")
def resource_aspects() -> str:
    """Complete aspects reference."""
    data = load_json("aspects_data.json")
    return json.dumps(data, indent=2) if data else "Aspects data not found"


@mcp.resource("astrology://traditional-astrology")
def resource_traditional_astrology() -> str:
    """Traditional astrology reference: Hellenistic techniques, dignities, sect, time lords."""
    data = load_json("traditional_astrology_data.json")
    return json.dumps(data, indent=2) if data else "Traditional astrology data not found"


@mcp.resource("astrology://natal-chart")
def resource_natal_chart() -> str:
    """Chandra's natal chart data."""
    data = load_json("natal_chart_chandra.json")
    return json.dumps(data, indent=2) if data else "Natal chart data not found"


# Personal chart resources — pull from sweph API
CHART_NAMES = ["chris", "katy", "micheal", "betsy", "megan", "kelsea", "lisa"]

for _name in CHART_NAMES:
    def _make_chart_resource(chart_name):
        @mcp.resource(f"astrology://natal-chart/{chart_name}")
        async def _resource() -> str:
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
# SECTION 5: PROMPTS — Interpretation Templates (11 total)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.prompt()
def narrative_weekly_forecast() -> str:
    """Create a narrative weekly astrological forecast weaving natal chart with current transits, expressed as an unfolding story."""
    return """Create a weekly astrological forecast in narrative form for [Date Range].
The forecast should read like a sacred beautifully written text, weaving the client's natal chart with current transits.
Do not list predictions—frame them as destiny unfolding.

## Structural Framework

### Title Format
"[Poetic Theme]: [Specific Personal Journey Reference]"
*[Date Range]*

Examples:
- "Celestial Symphony: The Eclipse at Your Partnership Gateway"
- "Cosmic Crescendo: Your Saturn Return's Final Act"
- "The Alchemical Week: Venus Dances with Your Destiny"

### Section Architecture
1. **Opening Movement - "The Cosmic Choreography/Orchestra/Stage"**
   - Begin with the week's most powerful transit/aspect
   - Connect it immediately to a specific natal placement
   - Use exact degrees and orbs
   - Frame as destiny unfolding

2. **The Major Transit Spotlight - "[Planet/Eclipse Name]: Your [Archetypal Theme]"**
   - Deep dive into the headline transit
   - Show exact aspects and orbs
   - Reveal activated houses and rulers
   - Connect to larger life narrative

3. **The Supporting Cast - "[Secondary Transit's Poetic Name]"**
   - 2-3 secondary transits
   - Show harmonies/tensions with main theme
   - Reference natal aspects
   - Build weekly "plot"

4. **The Natal Chart Callback - "Your Essential [Pattern] Illuminated"**
   - Reference natal configurations activated
   - Show fulfillment/challenge of birth promise
   - Interweave multiple natal placements

5. **The Sacred Geometry - "The Week's [Cosmic Pattern]"**
   - Identify aspect patterns (trines, T-squares, etc.)
   - Include transits + natal planets
   - Explain energetic flow

6. **The Oracle/Whisper/Declaration**
   - End with italicized cosmic guidance
   - Synthesize into poetic wisdom

## Tone & Style Guidelines
- Use sacred/mystical vocabulary ("cosmic amphitheater," "divine orchestration")
- Blend technical with poetic
- Personify planets ("Saturn whispers," "Venus demands")
- Always include: exact degrees, natal placements, orbs, house activations, rulers, timing, larger cycle context
- Favor poetic invitation over prediction
- Use second person voice and present tense
- Frame transits as revelations, journeys, thresholds, paradoxes, and echoes of natal patterns

## Content Requirements
- Exact degrees, orbs, natal placements, house activations, ruler connections
- Cycle context (retrogrades, eclipses, returns)
- Natal-transit dialogue, historical callbacks, future seeding, multivalent meanings"""


@mcp.prompt()
def interpret_traditional_chart() -> str:
    """Get a traditional astrological interpretation based on natal chart."""
    return """Please analyze my natal chart from the natal-chart resource using traditional astrological principles from the traditional-astrology resource. Focus on house rulerships in the style of Chris Brennan, with special attention to:

1. The ruler of my Ascendant and its placement
2. Planetary sect and dignity
3. Annual profections for my current age
4. Time lord techniques
5. Holistic synthesis in the style of Richard Tarnas

Please provide a thorough interpretation focusing on life direction, career, relationships, and spiritual development."""


@mcp.prompt()
def hellenistic_chart_analysis() -> str:
    """Get a Hellenistic astrology analysis of natal chart."""
    return """Please analyze my natal chart from the natal-chart resource using Hellenistic astrological techniques from the traditional-astrology resource. Focus on:

1. Whole sign house placements
2. The Ascendant ruler's condition by sign, house, dignity, and aspects
3. Sect analysis (day/night distinction)
4. Planetary joys and triplicities
5. Lots/Arabic Parts (especially Fortune and Spirit)
6. Time lord systems (annual profections and zodiacal releasing)

Provide a comprehensive reading in the style of Chris Brennan's approach to Hellenistic astrology."""


@mcp.prompt()
def archetypal_chart_analysis() -> str:
    """Get an archetypal astrology analysis of natal chart."""
    return """Please analyze my natal chart from the natal-chart resource using the archetypal astrology approach of Richard Tarnas from the traditional-astrology resource. Focus on:

1. The major planetary archetypes and their complex interactions in my chart
2. Significant aspect patterns and their archetypal meanings
3. The current transits to my natal chart and their archetypal significance
4. How these archetypal patterns might manifest in my personal life and consciousness
5. The deeper philosophical and spiritual implications of these archetypal dynamics

Provide a rich, nuanced interpretation that captures the multivalent symbolism and psychological depth of the Tarnas approach to archetypal astrology."""


@mcp.prompt()
def profection_year_analysis() -> str:
    """Get an analysis of your current annual profection."""
    return """Based on my natal chart from the natal-chart resource and traditional techniques from the traditional-astrology resource, please analyze my current annual profection year. Calculate which house and planet is activated this year based on my age, and provide a detailed interpretation of what this means for me. Include:

1. The activated house and its lord
2. The condition of that lord in my natal chart
3. Current transits to that lord and house
4. Key themes and focus areas for this profection year
5. Practical guidance for working with this year's energies

Please use the Chris Brennan approach to annual profections."""


@mcp.prompt()
def traditional_transits_analysis() -> str:
    """Get a traditional analysis of current transits to natal chart."""
    return """Please use the get-planet-positions and get-planet-aspects tools to compare current planetary positions with my natal chart from the natal-chart resource. Then provide a traditional analysis using frameworks from the traditional-astrology resource. Focus on:

1. Transits to my Ascendant ruler and its significance
2. Traditional interpretations of outer planet transits to natal positions
3. Current transits through my whole sign houses and their meanings
4. The relationship between current transits and my annual profection
5. Practical timing insights based on these traditional techniques

Please blend traditional timing techniques with practical guidance for navigating the current astrological weather."""


@mcp.prompt()
def interpret_natal_chart() -> str:
    """Get a personalized natal chart interpretation with focus on house rulership."""
    return """Please analyze my natal chart from the natal-chart resource with a focus on traditional house rulership. For each planet, analyze:

1. Its condition by sign placement (dignity, debility, mutual reception)
2. The house(s) it rules and how its condition affects those life areas
3. Its house placement and how it expresses its energy there
4. Important aspects it makes to other planets and how those modify its expression

Pay special attention to the ruler of the Ascendant as the chart ruler, and how its condition shapes my overall life direction. Include information about any mutual receptions between planets and what that signifies. Conclude with my key strengths, challenges, and potential life direction based on this traditional house rulership analysis."""


@mcp.prompt()
def analyze_current_transits() -> str:
    """Get analysis of current transits to natal chart with emphasis on house rulership."""
    return """Please use the get-planet-positions and get-planet-aspects tools to compare current planetary positions with my natal chart from the natal-chart resource. Focus your analysis on:

1. Transiting planets through natal houses and what areas of life they're activating
2. Transits to natal planets, especially rulers of important houses
3. How transiting planets in their current condition (dignity, debility, retrograde) are affecting the houses they rule in my natal chart
4. The houses currently being activated by transits to their rulers
5. Any temporary mutual receptions between transiting planets and how those might ease or complicate matters

Identify the most significant current transits based on house rulership considerations and provide practical guidance on how to work with these energies."""


@mcp.prompt()
def interpret_planets() -> str:
    """Interpret current planetary positions with house rulership analysis."""
    return """Please use the get-planet-positions and get-planet-aspects tools to analyze the current planetary positions. Then provide an astrological interpretation focusing on:

1. Each planet's current condition (sign dignity/debility, retrograde status)
2. Which houses each planet rules in a natural chart (Aries rising) and how its current condition affects those areas of life collectively
3. Current mutual receptions between planets and their significance
4. The most significant aspects between planets currently forming and how they modify planetary expressions
5. Which life areas (houses) are most supported or challenged right now based on their rulers' conditions and aspects

Provide practical guidance on how to best work with the current cosmic energies in different life domains, based on house rulership considerations."""


@mcp.prompt()
def moon_energy() -> str:
    """Explain the current moon phase and its influence with house rulership context."""
    return """Use the get-current-moon tool to check the current moon phase and sign. Then provide an analysis that includes:

1. The current lunar phase and its general meaning in the lunar cycle
2. The Moon's current sign placement, its dignity/debility status there, and any mutual receptions
3. Which house the Moon would rule (Cancer) in a natural chart and how its current condition affects those matters collectively
4. The house naturally ruled by the sign the Moon is currently in, and how the Moon's presence there affects those matters
5. Activities that are supported or challenged during this lunar phase and sign combination, with house rulership considerations
6. Practical guidance for working with today's lunar energy in different life domains"""


@mcp.prompt()
def weekly_planning() -> str:
    """Create a comprehensive weekly plan based on astrological influences including house rulership."""
    return """Create a comprehensive weekly astrological planning guide by combining multiple celestial influences including house rulership considerations. Use the following tools to gather all relevant astrological data:

1. First, check the get-weekly-moon-phase tool to find the major moon phase this week.
2. Use the void-of-course-moons tool to identify periods when the moon is void of course.
3. Review planetary-ingresses?timeframe=week to see which planets are changing signs and therefore changing their dignity/debility status and rulership effectiveness.
4. Check planetary-stations?timeframe=week to find any planets turning retrograde or direct and how that affects the houses they rule.
5. Analyze important-transits?timeframe=week to identify significant planetary aspects.

For each day of the week, provide:
- The sign and phase of the Moon, its dignity status, and which life areas (houses) are affected by its placement
- Void of course moon periods and what activities to avoid during these times
- Planets changing signs, their new dignity status, and how this affects the houses they rule
- Planets changing direction and how this impacts their ruled houses
- Major aspects forming and which houses/life areas are affected through rulership
- Practical recommendations for each day based on these combined influences

Include a section on which life areas (houses) are most activated this week based on planetary activity of their rulers, and what that means for personal planning. Present this as a practical guide that incorporates house rulership principles while remaining accessible to those with limited astrological knowledge."""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 5b: GRAPH QUERIES — Direct Neo4j knowledge traversals
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def graph_query(
    planet: Optional[str] = None,
    sign: Optional[str] = None,
    house: Optional[int] = None,
    layer: Optional[str] = None,
    author: Optional[str] = None,
    technique: Optional[str] = None,
    limit: int = 5,
) -> str:
    """Query the Neo4j knowledge graph with structured filters. No embeddings needed.

    This is a direct graph traversal — instant results. Use for structured lookups
    like "what does Brennan say about Mars in Aries" or "all psychological
    interpretations of the 12th house."

    Args:
        planet: Planet id (sun, moon, mercury, venus, mars, jupiter, saturn, etc.)
        sign: Sign id (aries, taurus, gemini, etc.)
        house: House number (1-12)
        layer: Interpretive layer (technical, psychological, archetypal, philosophical, reference)
        author: Author name (e.g. 'Chris Brennan', 'Richard Tarnas')
        technique: Technique id (essential_dignities, sect, profections, zodiacal_releasing, etc.)
        limit: Max results (default 5)
    """
    # Build dynamic Cypher query
    matches = ["(i:Interpretation)"]
    wheres = []

    if planet:
        matches.append("(i)-[:DESCRIBES]->(p:Planet {id: $planet})")
    if sign:
        matches.append("(i)-[:DESCRIBES]->(s:Sign {id: $sign})")
    if house is not None:
        matches.append("(i)-[:DESCRIBES]->(h:House {number: $house})")
    if layer:
        matches.append("(i)-[:IN_LAYER]->(l:Layer {id: $layer})")
    if author:
        matches.append("(i)-[:AUTHORED_BY]->(a:Author {name: $author})")
    else:
        matches.append("(i)-[:AUTHORED_BY]->(a:Author)")
    if technique:
        matches.append("(i)-[:DESCRIBES]->(t:Technique {id: $technique})")

    cypher = f"""
        MATCH {', '.join(matches)}
        RETURN i.text AS text, a.name AS author, i.source_title AS title,
               i.trust_tier AS tier
        ORDER BY i.trust_tier ASC
        LIMIT $limit
    """

    params = {"limit": limit}
    if planet: params["planet"] = planet
    if sign: params["sign"] = sign
    if house is not None: params["house"] = house
    if layer: params["layer"] = layer
    if author: params["author"] = author
    if technique: params["technique"] = technique

    results = neo4j_query(cypher, **params)

    if not results:
        return "No results found for this combination."

    # Format output
    parts = [f"Found {len(results)} results:\n"]
    for i, r in enumerate(results):
        text = r["text"][:600] + "..." if len(r["text"]) > 600 else r["text"]
        parts.append(f"[{i+1}] [{r['author']}] (Tier {r['tier']})")
        parts.append(f"    {r['title']}")
        parts.append(f"    {text}\n")

    return "\n".join(parts)


@mcp.tool()
def graph_rulership_web(sign: str) -> str:
    """Get the complete rulership web for a sign from the graph.

    Returns which planet rules it, is exalted in it, in detriment, in fall,
    and the triplicity rulers. Pure graph traversal, instant.

    Args:
        sign: Sign id (aries, taurus, gemini, etc.)
    """
    results = neo4j_query("""
        MATCH (s:Sign {id: $sign})
        OPTIONAL MATCH (ruler:Planet)-[:RULES]->(s)
        OPTIONAL MATCH (exalted:Planet)-[:EXALTED_IN]->(s)
        OPTIONAL MATCH (detriment:Planet)-[:DETRIMENT_IN]->(s)
        OPTIONAL MATCH (fall:Planet)-[:FALL_IN]->(s)
        OPTIONAL MATCH (trip_day:Planet)-[:TRIPLICITY_RULER {sect: 'day'}]->(s)
        OPTIONAL MATCH (trip_night:Planet)-[:TRIPLICITY_RULER {sect: 'night'}]->(s)
        OPTIONAL MATCH (trip_part:Planet)-[:TRIPLICITY_RULER {sect: 'participating'}]->(s)
        OPTIONAL MATCH (s)-[:OF_ELEMENT]->(e:Element)
        OPTIONAL MATCH (s)-[:OF_MODALITY]->(m:Modality)
        OPTIONAL MATCH (s)-[:NATURAL_HOUSE]->(h:House)
        OPTIONAL MATCH (opp:Sign)<-[:OPPOSES]-(s)
        RETURN s.name AS sign, s.symbol AS symbol,
               e.name AS element, m.name AS modality,
               h.number AS natural_house, h.topics AS house_topics,
               ruler.name AS ruler, exalted.name AS exalted,
               collect(DISTINCT detriment.name) AS detriments,
               collect(DISTINCT fall.name) AS falls,
               trip_day.name AS triplicity_day,
               trip_night.name AS triplicity_night,
               trip_part.name AS triplicity_participating,
               opp.name AS opposite_sign
    """, sign=sign.lower())

    if not results:
        return f"Sign '{sign}' not found."

    return json.dumps(results[0], indent=2, default=str)


@mcp.tool()
def graph_planet_condition(planet: str, sign: str) -> str:
    """Get a planet's full condition in a given sign from the graph.

    Returns all dignity relationships plus relevant interpretations
    from the knowledge graph. No embeddings needed.

    Args:
        planet: Planet id (sun, moon, mercury, etc.)
        sign: Sign id (aries, taurus, etc.)
    """
    # Structural dignities
    dignities = neo4j_query("""
        MATCH (p:Planet {id: $planet})
        OPTIONAL MATCH (p)-[r:RULES]->(s:Sign {id: $sign})
        OPTIONAL MATCH (p)-[e:EXALTED_IN]->(s2:Sign {id: $sign})
        OPTIONAL MATCH (p)-[d:DETRIMENT_IN]->(s3:Sign {id: $sign})
        OPTIONAL MATCH (p)-[f:FALL_IN]->(s4:Sign {id: $sign})
        OPTIONAL MATCH (p)-[t:TRIPLICITY_RULER]->(s5:Sign {id: $sign})
        RETURN p.name AS planet, p.sect AS sect, p.type AS type,
               r IS NOT NULL AS domicile,
               e IS NOT NULL AS exaltation,
               d IS NOT NULL AS detriment,
               f IS NOT NULL AS fall,
               t IS NOT NULL AS triplicity
    """, planet=planet.lower(), sign=sign.lower())

    # Top interpretations from each layer
    interpretations = neo4j_query("""
        MATCH (i:Interpretation)-[:DESCRIBES]->(p:Planet {id: $planet}),
              (i)-[:DESCRIBES]->(s:Sign {id: $sign}),
              (i)-[:IN_LAYER]->(l:Layer),
              (i)-[:AUTHORED_BY]->(a:Author)
        RETURN l.id AS layer, a.name AS author, left(i.text, 300) AS excerpt,
               i.trust_tier AS tier
        ORDER BY l.id, i.trust_tier ASC
        LIMIT 10
    """, planet=planet.lower(), sign=sign.lower())

    output = {
        "condition": dignities[0] if dignities else {},
        "interpretations_by_layer": {},
    }

    for interp in interpretations:
        layer = interp["layer"]
        if layer not in output["interpretations_by_layer"]:
            output["interpretations_by_layer"][layer] = []
        output["interpretations_by_layer"][layer].append({
            "author": interp["author"],
            "excerpt": interp["excerpt"],
            "tier": interp["tier"],
        })

    return json.dumps(output, indent=2)


@mcp.tool()
def graph_stats() -> str:
    """Get statistics about the Neo4j knowledge graph."""
    stats = {}

    counts = neo4j_query("""
        MATCH (i:Interpretation) WITH count(i) AS interps
        MATCH (p:Planet) WITH interps, count(p) AS planets
        MATCH (s:Sign) WITH interps, planets, count(s) AS signs
        MATCH (h:House) WITH interps, planets, signs, count(h) AS houses
        MATCH (a:Author) WITH interps, planets, signs, houses, count(a) AS authors
        MATCH ()-[r:DESCRIBES]->() WITH interps, planets, signs, houses, authors, count(r) AS describes
        MATCH ()-[r2:RULES]->() WITH interps, planets, signs, houses, authors, describes, count(r2) AS rules
        RETURN interps, planets, signs, houses, authors, describes, rules
    """)

    if counts:
        c = counts[0]
        stats = {
            "interpretations": c["interps"],
            "planets": c["planets"],
            "signs": c["signs"],
            "houses": c["houses"],
            "authors": c["authors"],
            "describes_relationships": c["describes"],
            "rules_relationships": c["rules"],
        }

    # Author breakdown
    authors = neo4j_query("""
        MATCH (i:Interpretation)-[:AUTHORED_BY]->(a:Author)
        RETURN a.name AS author, count(i) AS chunks
        ORDER BY chunks DESC
    """)
    stats["authors_detail"] = {a["author"]: a["chunks"] for a in authors}

    # Layer breakdown
    layers = neo4j_query("""
        MATCH (i:Interpretation)-[:IN_LAYER]->(l:Layer)
        RETURN l.id AS layer, count(i) AS chunks
        ORDER BY chunks DESC
    """)
    stats["layers"] = {l["layer"]: l["chunks"] for l in layers}

    return json.dumps(stats, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 6: CHART READING — Full Computation + Knowledge-Grounded Narrative
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# The chart reading pipeline:
#   1. full_chart_computation(name) — gathers ALL data from Helios into one payload
#   2. _gather_knowledge(chart_data) — queries knowledge graph for every placement
#   3. chart_reading(name, size, perspective) — returns computation + knowledge + narrative prompt
#
# The LLM receives everything it needs to write the interpretation.
# Selene provides data + sources + guidelines. The LLM synthesizes.


# ── Size definitions ──

CHART_SIZES = {
    "xs": {
        "label": "XS — The Glance",
        "target_length": "3-5 sentences",
        "depth": """Distilled portrait. Every lens touched in a phrase or sentence.
Who this person is at their core, their dominant strength, their central tension,
where they are right now in life. Like a therapist's first-session impression.
No astrology language — pure human insight, compressed to its essence.

CLOSING: End the entire reading with ONE quote or beautifully written sentence
in the spirit of a Stoic, Jung, or Alan Watts — something that captures
the essence of this person's chart. If the knowledge graph has a perfect
passage, use it. Otherwise, compose one.""",
        "knowledge_results": 1,  # per query
    },
    "s": {
        "label": "S — Key Themes",
        "target_length": "2-3 paragraphs",
        "depth": """Portrait plus the 2-3 most dominant life themes fleshed out.
What drives this person, what holds them back, how they relate to others.
The central psychological tension and the primary coping strategy.
Where they are in their life's arc right now and why it matters.
Written as insight, not analysis. Like a letter from someone who understands.

CLOSING: End with ONE quote or beautifully written sentence — Stoic, Jungian,
or contemplative in tone — that captures the whole.""",
        "knowledge_results": 2,
    },
    "m": {
        "label": "M — Working Reading",
        "target_length": "1-2 pages",
        "depth": """All interpretive lenses addressed with moderate depth.
How this person presents to the world vs. who they are inside. Their emotional
patterns — what feels safe, what triggers defense, how they process experience.
What they attract in relationships and why. How early life shaped their coping.
Their natural gifts and where they overcompensate. How motivation and purpose
flow through their life. The current chapter and what it's asking of them.
Written as a continuous narrative — warm, direct, psychologically grounded.
Knowledge graph material absorbed and synthesized, never cited as astrology.

SECTION CLOSINGS: At the end of 2-3 key sections, include a one-sentence
summary written beautifully — in the spirit of a Stoic, Jung, or Alan Watts.
These are distillations, not decorations. End the full reading with a quote
from the knowledge graph if one fits, or compose a closing aphorism.""",
        "knowledge_results": 3,
    },
    "l": {
        "label": "L — Full Narrative",
        "target_length": "3-5 pages",
        "depth": """Full narrative interpretation across all lenses.

How the face this person shows the world differs from who they are when
alone. The emotional interior — how they take in experience, what soothes
them, what overwhelms them, and how that resonates outward into how people
perceive them. What they attract in relationships and why — the feedback
loop between self and other. How early life conditions shaped their coping
strategies, attachment patterns, and sense of safety. What operates below
awareness — the patterns they can't see but others can. Where their life
is more private vs. public-facing and what that means.

Strengths described not as gifts but as *developed capacities* — things
this person has built through effort. Challenges described not as flaws
but as friction points where growth is available. The internal logic of
how motivation, energy, and purpose flow through their life.

Psychological frameworks woven throughout: attachment theory, Jungian
individuation, shadow work, internal family systems, developmental stages.
The knowledge graph material fully absorbed and expressed as insight.
The current life chapter given biographical weight — where have they been,
where are they now, what's being asked of them.

SECTION CLOSINGS: End most sections with a one-sentence closing —
beautifully written in the voice of a Stoic, Jung, or Alan Watts.
If the knowledge graph contains a passage that captures the section's
essence, quote it directly (attributed). Otherwise compose an aphorism
that distills the section. These closings are the heartbeat of the reading.""",
        "knowledge_results": 4,
    },
    "xl": {
        "label": "XL — The Deep Dive",
        "target_length": "5-10+ pages",
        "depth": """Exhaustive meaning-making. The full operating system of a person.

Every lens explored in full depth, expressed entirely as human experience:

- The face and the interior: How the identity they project interacts with
  who they actually feel themselves to be. Where these align, where they
  create tension, where one compensates for the other.
- The emotional body: How this person receives and processes experience.
  What feels safe. What triggers defense. What they do with difficult
  feelings — intellectualize, somatize, project, suppress, act out.
  The attachment style implied by their emotional patterning.
- The mirror: What this person attracts in others. What gets projected
  outward. The feedback loop between how they see themselves and how
  the world reflects them back. Relationship patterns.
- Formative imprints: What childhood and early family conditions likely
  shaped their coping strategies. Not deterministic — but the soil the
  seed grew in. The internalized parent. The wound that became a skill.
- The conscious and the unconscious: What this person manages deliberately
  vs. what operates below awareness. The blind spots. The shadow material.
  What they've exiled from identity that still runs the show.
- Private and public: Where the weight of their life falls — inward builder
  or outward performer? Where do they invest energy that nobody sees?
- Strengths and overcompensation: Natural capacities — and the places
  where strength becomes rigidity, where a gift gets overused because
  the alternative feels too vulnerable.
- The internal economy: How motivation, energy, and purpose flow through
  their life. Where it pools (obsession, hyperfocus). Where it leaks
  (avoidance, scattered attention, chronic depletion).
- The current chapter: Where are they in the larger arc? What season of
  life is this? What's ending, what's beginning, what's being demanded?

The knowledge graph provides the scholarly depth. Absorb it completely.
Express it as human truth. The reader should feel *seen* — not analyzed.

Actionable synthesis: What does this person need to understand about
themselves right now? Where are the growth edges? What's the invitation?
What would a wise friend who could see everything say to them?

SECTION CLOSINGS — CRITICAL:
After EVERY section, include a closing quote or aphorism. Two options:
1. PREFERRED: A direct quote from the knowledge graph source material
   that resonates with the section's insight. Attribute it:
   *"The soul becomes dyed with the color of its thoughts." — Marcus Aurelius*
   Search the knowledge graph excerpts for passages from Tarnas, Sasportas,
   the Gnostic Book of Changes, Stoic philosophy, or the archetypal layer
   that match the section's theme. Use the actual text when it fits.
2. FALLBACK: If no knowledge graph passage fits, compose a one-sentence
   aphorism in the spirit of the Stoics, Jung, or Alan Watts. Make it
   beautiful, specific to this section, not generic.

These closings are not decoration. They are the resonant frequency of each
section — the thing that lingers after the analysis fades.""",
        "knowledge_results": 5,
    },
}


# ── Perspectives ──

PERSPECTIVES = {
    "psychological": """Interpretive philosophy: NON-FATALIST, NON-DETERMINISTIC.
The chart describes archetypal fields of possibility, not fixed outcomes.

CRITICAL RULES FOR THE NARRATIVE:
- Write for a HUMAN who does NOT know astrology. No jargon. No "Mercury rules
  your 1st house" or "peregrine Sun in the 9th." Translate everything into
  lived experience, psychology, and felt human reality.
- Do NOT name planets, signs, houses, or aspects explicitly. Instead, describe
  what they MEAN in this person's life. "You lead with analytical precision
  and a restless need to solve things" rather than "Mercury in Aries in the 8th."
- The astrological data is your SOURCE MATERIAL, not your output. You read it,
  synthesize it, and deliver human insight. Like a doctor who reads bloodwork
  but tells the patient "you need more rest" — not "your cortisol is 22 µg/dL."
- Use psychological frameworks: attachment patterns, individuation, shadow work,
  defense mechanisms, internal family systems, developmental psychology.
  These are the LANGUAGE of the output.
- Speak about patterns of experience: how this person takes in the world,
  what feels safe, where they overcompensate, what they project onto others,
  where their blind spots live, what strengths they undervalue.
- The knowledge graph excerpts are your scholarly foundation. Absorb their
  insights but express them in everyday language. Never cite authors by name
  unless the reader would benefit from the reference.

Voice: Warm, direct, insightful. Like a brilliant therapist who also happens
to understand your whole life structure. Speak to the person. Second person.
No filler, no flattery. Say the true thing.""",

    "deterministic": """Interpretive philosophy: DETERMINISTIC (GTEI framework).
The chart is a necessitated expression of Absolute Self-Consistency (ASC).
Every placement, aspect, and timing event is the only possible configuration
— the singular, self-consistent solution to this person's coherence equation.

Analyze through the 5 Primordial Categories:
- Distinction/Unity: This individual chart within the collective
- Relation/Separation: Aspects and house relationships as necessitated connections
- Potentiality/Actuality: Natal chart as potential, timing as actualization
- Quantity/Quality: Dignities (quantitative) yielding qualitative expression
- Process/State: Timing techniques as process, natal positions as state

"Free will" is reinterpreted as self-generated determinism — the maximally
coherent pathway from this IEI's internal potentials.

Voice: Authoritative, philosophical. Frame everything as necessitated unfolding.
End with a human-readable synthesis in everyday language and one
coherence-aiding question for the reader.""",
}


@mcp.tool()
async def full_chart_computation(name: str) -> str:
    """Gather ALL computational data for a natal chart in one call.

    Returns every piece of astrological data Helios can compute:
    planets, dignities, depositors, houses, angles, lots, sect,
    aspects, profections, zodiacal releasing, and current transits.

    This is the raw data layer. Always maximal, regardless of report size.

    Args:
        name: Chart name (must exist in Helios or local storage)
    """
    results = {}
    errors = []

    # 1. Full chart data (planets, houses, angles, lots, depositors, sect)
    try:
        results["chart"] = await call_sweph(f"/chart/{name}")
    except Exception as e:
        errors.append(f"chart: {e}")
        # Try local storage as fallback
        local = _load_local_chart(name)
        if local:
            results["chart"] = local
        else:
            return json.dumps({"error": f"Chart '{name}' not found", "details": errors})

    # 2. Essential dignities for every planet in the chart
    chart = results.get("chart", {})
    planets = chart.get("planets", [])
    sect = chart.get("sect", {})
    is_day = sect.get("isDaySect", True)

    dignity_results = []
    for p in planets:
        p_name = p.get("name", "")
        lon = p.get("longitude")
        if lon and p_name not in ("North Node", "South Node", "Chiron"):
            try:
                dignity = await call_sweph(
                    f"/dignity-score?planet={p_name}&longitude={lon}&isDaySect={'true' if is_day else 'false'}"
                )
                dignity_results.append(dignity)
            except Exception as e:
                errors.append(f"dignity {p_name}: {e}")
    results["dignities"] = dignity_results

    # 3. Current aspects between all planets
    try:
        results["current_aspects"] = await call_sweph("/aspects-now")
    except Exception as e:
        errors.append(f"aspects: {e}")

    # 4. Profections
    try:
        results["profections"] = await call_sweph(f"/profections/{name}")
    except Exception as e:
        errors.append(f"profections: {e}")

    # 5. Zodiacal Releasing (both lots)
    for lot in ["spirit", "fortune"]:
        try:
            results[f"zr_{lot}"] = await call_sweph(f"/zr/{name}?lot={lot}")
        except Exception as e:
            errors.append(f"zr_{lot}: {e}")

    # 6. Current transits to natal
    try:
        results["transits"] = await call_sweph(f"/transits/{name}/now?major=true")
    except Exception as e:
        errors.append(f"transits: {e}")

    # 7. Transit summary (compact view with timing context)
    try:
        results["transit_summary"] = await call_sweph(f"/transits/{name}/summary")
    except Exception as e:
        errors.append(f"transit_summary: {e}")

    # 8. Current planetary positions (for context)
    try:
        results["current_positions"] = await call_sweph("/planets-now")
    except Exception as e:
        errors.append(f"current_positions: {e}")

    # 9. Current moon
    try:
        results["current_moon"] = await call_sweph("/moon-now")
    except Exception as e:
        errors.append(f"current_moon: {e}")

    if errors:
        results["_warnings"] = errors

    return json.dumps(results, indent=2)


def _gather_knowledge_for_chart(chart_data: dict, results_per_query: int = 3) -> list[dict]:
    """Query the Neo4j knowledge graph for every significant placement in the chart.

    Uses graph traversals — NO embedding API calls. Instant.

    Pulls interpretive material across all layers for every planet,
    plus timing techniques (profections, ZR).

    Returns a list of {query, layer, results} dicts.
    """
    knowledge_hits = []
    chart = chart_data.get("chart", {})
    planets = chart.get("planets", [])

    # Map planet names to graph IDs
    name_to_id = {
        "Sun": "sun", "Moon": "moon", "Mercury": "mercury", "Venus": "venus",
        "Mars": "mars", "Jupiter": "jupiter", "Saturn": "saturn",
        "Uranus": "uranus", "Neptune": "neptune", "Pluto": "pluto",
        "North Node": "north_node", "South Node": "south_node", "Chiron": None,
    }

    for p in planets:
        pname = p.get("name", "")
        sign = p.get("sign", "")
        house = p.get("house", "")
        planet_id = name_to_id.get(pname)
        if not planet_id:
            continue
        sign_id = sign.lower() if sign else None
        house_num = int(house) if house and str(house).isdigit() else None

        # ── Planet + Sign: technical layer (dignity, rulership) ──
        if sign_id:
            results = neo4j_query("""
                MATCH (i:Interpretation)-[:DESCRIBES]->(p:Planet {id: $planet}),
                      (i)-[:DESCRIBES]->(s:Sign {id: $sign}),
                      (i)-[:IN_LAYER]->(l:Layer {id: 'technical'}),
                      (i)-[:AUTHORED_BY]->(a:Author)
                RETURN i.text AS text, a.name AS author, i.source_title AS title,
                       i.trust_tier AS tier
                ORDER BY i.trust_tier ASC
                LIMIT $limit
            """, planet=planet_id, sign=sign_id, limit=results_per_query)

            if results:
                knowledge_hits.append({
                    "query": f"{pname} in {sign} (technical)",
                    "results": [{"text": r["text"][:500], "author": r["author"],
                                 "title": r["title"], "tier": r["tier"]} for r in results],
                })

        # ── Planet + House: psychological layer ──
        if house_num:
            results = neo4j_query("""
                MATCH (i:Interpretation)-[:DESCRIBES]->(p:Planet {id: $planet}),
                      (i)-[:DESCRIBES]->(h:House {number: $house}),
                      (i)-[:IN_LAYER]->(l:Layer {id: 'psychological'}),
                      (i)-[:AUTHORED_BY]->(a:Author)
                RETURN i.text AS text, a.name AS author, i.source_title AS title,
                       i.trust_tier AS tier
                ORDER BY i.trust_tier ASC
                LIMIT $limit
            """, planet=planet_id, house=house_num, limit=results_per_query)

            if results:
                knowledge_hits.append({
                    "query": f"{pname} in house {house} (psychological)",
                    "results": [{"text": r["text"][:500], "author": r["author"],
                                 "title": r["title"], "tier": r["tier"]} for r in results],
                })

        # ── Planet + Sign: reference layer (delineations) ──
        if sign_id:
            results = neo4j_query("""
                MATCH (i:Interpretation)-[:DESCRIBES]->(p:Planet {id: $planet}),
                      (i)-[:DESCRIBES]->(s:Sign {id: $sign}),
                      (i)-[:IN_LAYER]->(l:Layer {id: 'reference'}),
                      (i)-[:AUTHORED_BY]->(a:Author)
                RETURN i.text AS text, a.name AS author, i.source_title AS title,
                       i.trust_tier AS tier
                ORDER BY i.trust_tier ASC
                LIMIT $limit
            """, planet=planet_id, sign=sign_id, limit=results_per_query)

            if results:
                knowledge_hits.append({
                    "query": f"{pname} in {sign} (reference)",
                    "results": [{"text": r["text"][:500], "author": r["author"],
                                 "title": r["title"], "tier": r["tier"]} for r in results],
                })

    # ── Archetypal layer: notable dignities/debilities ──
    dignities = chart_data.get("dignities", [])
    for d in dignities:
        if d.get("detriment") or d.get("fall") or d.get("domicile") or d.get("exaltation"):
            planet_name = d.get("planet", "")
            sign_name = d.get("sign", "")
            condition = d.get("condition", "")
            planet_id = planet_name.lower()
            sign_id = sign_name.lower()

            results = neo4j_query("""
                MATCH (i:Interpretation)-[:DESCRIBES]->(p:Planet {id: $planet}),
                      (i)-[:DESCRIBES]->(s:Sign {id: $sign}),
                      (i)-[:IN_LAYER]->(l:Layer {id: 'archetypal'}),
                      (i)-[:AUTHORED_BY]->(a:Author)
                RETURN i.text AS text, a.name AS author, i.source_title AS title,
                       i.trust_tier AS tier
                ORDER BY i.trust_tier ASC
                LIMIT $limit
            """, planet=planet_id, sign=sign_id, limit=results_per_query)

            if results:
                knowledge_hits.append({
                    "query": f"{planet_name} in {sign_name} ({condition}, archetypal)",
                    "results": [{"text": r["text"][:500], "author": r["author"],
                                 "title": r["title"], "tier": r["tier"]} for r in results],
                })

    # ── Timing: profections ──
    profections = chart_data.get("profections", {})
    lord_of_year = profections.get("profection", {}).get("lordOfYear", "")
    if lord_of_year:
        lord_id = lord_of_year.lower()
        results = neo4j_query("""
            MATCH (i:Interpretation)-[:DESCRIBES]->(t:Technique {id: 'profections'}),
                  (i)-[:DESCRIBES]->(p:Planet {id: $planet}),
                  (i)-[:AUTHORED_BY]->(a:Author)
            RETURN i.text AS text, a.name AS author, i.source_title AS title,
                   i.trust_tier AS tier
            ORDER BY i.trust_tier ASC
            LIMIT $limit
        """, planet=lord_id, limit=results_per_query)

        if results:
            knowledge_hits.append({
                "query": f"Lord of year: {lord_of_year} (profections)",
                "results": [{"text": r["text"][:500], "author": r["author"],
                             "title": r["title"], "tier": r["tier"]} for r in results],
            })

    # ── Timing: ZR ──
    zr_spirit = chart_data.get("zr_spirit", {})
    zr_sign = zr_spirit.get("activePeriod", {}).get("sign", "")
    zr_ruler = zr_spirit.get("activePeriod", {}).get("ruler", "")
    if zr_sign:
        results = neo4j_query("""
            MATCH (i:Interpretation)-[:DESCRIBES]->(t:Technique {id: 'zodiacal_releasing'}),
                  (i)-[:IN_LAYER]->(l:Layer {id: 'technical'}),
                  (i)-[:AUTHORED_BY]->(a:Author)
            RETURN i.text AS text, a.name AS author, i.source_title AS title,
                   i.trust_tier AS tier
            ORDER BY i.trust_tier ASC
            LIMIT $limit
        """, limit=results_per_query)

        if results:
            knowledge_hits.append({
                "query": f"ZR Spirit L1: {zr_sign} ruled by {zr_ruler}",
                "results": [{"text": r["text"][:500], "author": r["author"],
                             "title": r["title"], "tier": r["tier"]} for r in results],
            })

    # ── Structural context: rulership web for key planets ──
    # Get the dignity relationships for the chart from the graph itself
    for p in planets[:7]:  # Traditional planets only
        planet_id = name_to_id.get(p.get("name", ""))
        if not planet_id:
            continue
        sign_id = p.get("sign", "").lower()
        if not sign_id:
            continue

        # What dignity does this planet have in this sign?
        dignity_info = neo4j_query("""
            MATCH (p:Planet {id: $planet})
            OPTIONAL MATCH (p)-[:RULES]->(s:Sign {id: $sign})
            OPTIONAL MATCH (p)-[:EXALTED_IN]->(s2:Sign {id: $sign})
            OPTIONAL MATCH (p)-[:DETRIMENT_IN]->(s3:Sign {id: $sign})
            OPTIONAL MATCH (p)-[:FALL_IN]->(s4:Sign {id: $sign})
            OPTIONAL MATCH (p)-[:TRIPLICITY_RULER]->(s5:Sign {id: $sign})
            RETURN s IS NOT NULL AS domicile,
                   s2 IS NOT NULL AS exalted,
                   s3 IS NOT NULL AS detriment,
                   s4 IS NOT NULL AS fall,
                   s5 IS NOT NULL AS triplicity
        """, planet=planet_id, sign=sign_id)

        if dignity_info:
            d = dignity_info[0]
            conditions = []
            if d["domicile"]: conditions.append("domicile")
            if d["exalted"]: conditions.append("exaltation")
            if d["detriment"]: conditions.append("detriment")
            if d["fall"]: conditions.append("fall")
            if d["triplicity"]: conditions.append("triplicity ruler")
            if conditions:
                knowledge_hits.append({
                    "query": f"{p['name']} in {p['sign']} (graph dignity)",
                    "results": [{"text": f"{p['name']} is in {', '.join(conditions)} in {p['sign']}. "
                                         f"This is a structural relationship from the astrological ontology.",
                                 "author": "graph", "title": "Structural Ontology", "tier": 0}],
                })

    return knowledge_hits


@mcp.tool()
async def chart_reading(
    name: str,
    size: str = "m",
    perspective: str = "psychological",
) -> str:
    """Generate a complete chart reading: full computation + knowledge graph + narrative prompt.

    This is the main chart interpretation tool. It:
    1. Computes ALL chart data from Helios (always maximal)
    2. Queries the knowledge graph for every placement (grounded in the corpus)
    3. Returns everything packaged with narrative guidelines for the requested size

    The LLM receives: raw data + source material + interpretation instructions.
    The LLM synthesizes the narrative.

    Args:
        name: Chart name (e.g. 'chris', 'katy', 'megan')
        size: xs | s | m | l | xl (default: m)
        perspective: psychological (default) | deterministic (GTEI)
    """
    size = size.lower()
    if size not in CHART_SIZES:
        return f"Invalid size '{size}'. Choose from: xs, s, m, l, xl"

    perspective = perspective.lower()
    if perspective not in PERSPECTIVES:
        return f"Invalid perspective '{perspective}'. Choose from: psychological, deterministic"

    size_config = CHART_SIZES[size]
    perspective_text = PERSPECTIVES[perspective]

    # ── Step 1: Full computation (always maximal) ──
    computation_json = await full_chart_computation(name)
    computation = json.loads(computation_json)

    if "error" in computation:
        return json.dumps(computation)

    # ── Step 2: Knowledge graph queries (grounded in corpus) ──
    knowledge = _gather_knowledge_for_chart(
        computation,
        results_per_query=size_config["knowledge_results"],
    )

    # ── Step 3: Package everything ──
    output = {
        "report_config": {
            "chart_name": name,
            "size": size_config["label"],
            "target_length": size_config["target_length"],
            "perspective": perspective,
        },
        "narrative_instructions": f"""
=== CHART READING: {name.upper()} ===
Size: {size_config['label']}
Target length: {size_config['target_length']}

=== DEPTH GUIDELINES ===
{size_config['depth']}

=== NARRATIVE STRUCTURE ===
Use these as section headers (## headers in markdown). They are the framework.
Each section is a clear container. The narrative weaves within each section.
Adapt header names to feel natural for this specific person, but follow the order.

## First Impression
Who this person appears to be. The face they show. How the world reads them.

## The Interior
How they actually feel inside. Emotional processing style. What soothes them,
what overwhelms them. The gap (or alignment) between the face and the interior.

## The Roots
How early life and family shaped their patterns. Attachment style. What the
home environment taught them about safety, stability, love, and self-worth.

## The Mind
How they think, communicate, process information. The quality and orientation
of their intellectual life. What their mind is drawn to.

## The Drive
What powers them. Creative and professional output. Natural strengths.
Where the drive overheats — compulsion, overwork, self-exploitation.

## The Mirror
What they attract in others. Relationship patterns. What gets projected.
The feedback loop between self-image and how others reflect them back.

## The Blind Spots
What operates below awareness. Shadow material. Unconscious patterns.
The things they can't see about themselves that others can.

## The Current Chapter
Where they are right now in life's larger arc. What season this is.
What's ending, beginning, or being demanded. The biographical moment.

## The Invitation
What this moment is asking of them. The growth edge. Actionable insight.
What a wise friend who could see everything would say.

=== PERSPECTIVE ===
{perspective_text}

=== CRITICAL OUTPUT RULES ===
- NO astrological jargon in the narrative. No planet names, sign names, house
  numbers, aspect names, or degree positions. Translate EVERYTHING into
  psychology, behavior, felt experience, and human reality.
- The computation data and knowledge graph are your RAW MATERIALS. Read them,
  synthesize them, and output HUMAN INSIGHT.
- The reader should feel deeply understood, not lectured about their chart.
- Weave, don't section. This is a continuous narrative, not a report.
- Every size gets full computation. The sizing controls elaboration depth only.
""",
        "computation": computation,
        "knowledge_graph": knowledge,
    }

    return json.dumps(output, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import asyncio

    # Try to discover additional sweph endpoints before starting
    try:
        asyncio.get_event_loop().run_until_complete(discover_and_register())
    except Exception as e:
        print(f"[selene] Startup discovery skipped: {e}", file=sys.stderr)

    mcp.run(transport="stdio")
