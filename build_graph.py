#!/usr/bin/env python3
"""
Build the Selene Knowledge Graph in Neo4j.

Phase 2: Structural graph — the astrological skeleton.
Phase 3: Knowledge migration — 6,160 chunks from ChromaDB → graph nodes.

Run once to initialize, idempotent via MERGE.
"""

import json
import sys
from pathlib import Path

from neo4j import GraphDatabase

# ── Config ──
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "selene_gnosis"

SELENE_DIR = Path(__file__).parent
CHROMA_DIR = SELENE_DIR.parent / "astro-knowledge" / "chromadb_store"

# ══════════════════════════════════════════════════════════════
# PHASE 2: STRUCTURAL GRAPH — The Astrological Skeleton
# ══════════════════════════════════════════════════════════════

# ── Planets ──
PLANETS = [
    {"id": "sun", "name": "Sun", "type": "luminary", "sect": "diurnal", "symbol": "☉"},
    {"id": "moon", "name": "Moon", "type": "luminary", "sect": "nocturnal", "symbol": "☽"},
    {"id": "mercury", "name": "Mercury", "type": "personal", "sect": "variable", "symbol": "☿"},
    {"id": "venus", "name": "Venus", "type": "personal", "sect": "nocturnal", "symbol": "♀"},
    {"id": "mars", "name": "Mars", "type": "personal", "sect": "nocturnal", "symbol": "♂"},
    {"id": "jupiter", "name": "Jupiter", "type": "social", "sect": "diurnal", "symbol": "♃"},
    {"id": "saturn", "name": "Saturn", "type": "social", "sect": "diurnal", "symbol": "♄"},
    {"id": "uranus", "name": "Uranus", "type": "outer", "sect": "none", "symbol": "♅"},
    {"id": "neptune", "name": "Neptune", "type": "outer", "sect": "none", "symbol": "♆"},
    {"id": "pluto", "name": "Pluto", "type": "outer", "sect": "none", "symbol": "♇"},
    {"id": "north_node", "name": "North Node", "type": "nodal", "sect": "none", "symbol": "☊"},
    {"id": "south_node", "name": "South Node", "type": "nodal", "sect": "none", "symbol": "☋"},
    {"id": "lot_fortune", "name": "Lot of Fortune", "type": "lot", "sect": "none", "symbol": "⊕"},
    {"id": "lot_spirit", "name": "Lot of Spirit", "type": "lot", "sect": "none", "symbol": "⊗"},
]

# ── Signs ──
SIGNS = [
    {"id": "aries", "name": "Aries", "element": "fire", "modality": "cardinal", "polarity": "masculine", "ruler": "mars", "exalt_ruler": "sun", "number": 1, "symbol": "♈"},
    {"id": "taurus", "name": "Taurus", "element": "earth", "modality": "fixed", "polarity": "feminine", "ruler": "venus", "exalt_ruler": "moon", "number": 2, "symbol": "♉"},
    {"id": "gemini", "name": "Gemini", "element": "air", "modality": "mutable", "polarity": "masculine", "ruler": "mercury", "exalt_ruler": None, "number": 3, "symbol": "♊"},
    {"id": "cancer", "name": "Cancer", "element": "water", "modality": "cardinal", "polarity": "feminine", "ruler": "moon", "exalt_ruler": "jupiter", "number": 4, "symbol": "♋"},
    {"id": "leo", "name": "Leo", "element": "fire", "modality": "fixed", "polarity": "masculine", "ruler": "sun", "exalt_ruler": None, "number": 5, "symbol": "♌"},
    {"id": "virgo", "name": "Virgo", "element": "earth", "modality": "mutable", "polarity": "feminine", "ruler": "mercury", "exalt_ruler": "mercury", "number": 6, "symbol": "♍"},
    {"id": "libra", "name": "Libra", "element": "air", "modality": "cardinal", "polarity": "masculine", "ruler": "venus", "exalt_ruler": "saturn", "number": 7, "symbol": "♎"},
    {"id": "scorpio", "name": "Scorpio", "element": "water", "modality": "fixed", "polarity": "feminine", "ruler": "mars", "exalt_ruler": None, "number": 8, "symbol": "♏"},
    {"id": "sagittarius", "name": "Sagittarius", "element": "fire", "modality": "mutable", "polarity": "masculine", "ruler": "jupiter", "exalt_ruler": None, "number": 9, "symbol": "♐"},
    {"id": "capricorn", "name": "Capricorn", "element": "earth", "modality": "cardinal", "polarity": "feminine", "ruler": "saturn", "exalt_ruler": "mars", "number": 10, "symbol": "♑"},
    {"id": "aquarius", "name": "Aquarius", "element": "air", "modality": "fixed", "polarity": "masculine", "ruler": "saturn", "exalt_ruler": None, "number": 11, "symbol": "♒"},
    {"id": "pisces", "name": "Pisces", "element": "water", "modality": "mutable", "polarity": "feminine", "ruler": "jupiter", "exalt_ruler": "venus", "number": 12, "symbol": "♓"},
]

# ── Houses ──
HOUSES = [
    {"number": 1, "name": "Hour-Marker", "modern": "Self", "angular": "angular", "topics": "life, body, appearance, character", "joy": "mercury"},
    {"number": 2, "name": "Gate of Hades", "modern": "Resources", "angular": "succedent", "topics": "money, possessions, values", "joy": None},
    {"number": 3, "name": "Goddess", "modern": "Communication", "angular": "cadent", "topics": "siblings, neighbors, short travel, communication", "joy": "moon"},
    {"number": 4, "name": "Hypogeion", "modern": "Home", "angular": "angular", "topics": "parents, home, ancestry, foundations", "joy": None},
    {"number": 5, "name": "Good Fortune", "modern": "Creativity", "angular": "succedent", "topics": "children, pleasure, creative expression", "joy": "venus"},
    {"number": 6, "name": "Bad Fortune", "modern": "Service", "angular": "cadent", "topics": "illness, enemies, servants, labor", "joy": "mars"},
    {"number": 7, "name": "Setting", "modern": "Partnership", "angular": "angular", "topics": "marriage, partnerships, open enemies", "joy": None},
    {"number": 8, "name": "Idle Place", "modern": "Transformation", "angular": "succedent", "topics": "death, inheritance, transformation", "joy": None},
    {"number": 9, "name": "God", "modern": "Philosophy", "angular": "cadent", "topics": "foreign travel, philosophy, religion, divination", "joy": "sun"},
    {"number": 10, "name": "Midheaven", "modern": "Career", "angular": "angular", "topics": "career, reputation, public life, authority", "joy": None},
    {"number": 11, "name": "Good Spirit", "modern": "Community", "angular": "succedent", "topics": "friends, hopes, benefactors, alliances", "joy": "jupiter"},
    {"number": 12, "name": "Bad Spirit", "modern": "Hidden Life", "angular": "cadent", "topics": "imprisonment, self-undoing, hidden enemies", "joy": "saturn"},
]

# ── Aspects ──
ASPECTS = [
    {"id": "conjunction", "name": "Conjunction", "degrees": 0, "quality": "neutral", "symbol": "☌"},
    {"id": "sextile", "name": "Sextile", "degrees": 60, "quality": "harmonious", "symbol": "⚹"},
    {"id": "square", "name": "Square", "degrees": 90, "quality": "challenging", "symbol": "□"},
    {"id": "trine", "name": "Trine", "degrees": 120, "quality": "harmonious", "symbol": "△"},
    {"id": "opposition", "name": "Opposition", "degrees": 180, "quality": "challenging", "symbol": "☍"},
]

# ── Techniques ──
TECHNIQUES = [
    {"id": "essential_dignities", "name": "Essential Dignities", "tradition": "hellenistic", "description": "Five levels of planetary strength by sign position"},
    {"id": "sect", "name": "Sect", "tradition": "hellenistic", "description": "Day/night chart distinction affecting planetary expression"},
    {"id": "profections", "name": "Annual Profections", "tradition": "hellenistic", "description": "Year-by-year house activation, lord of the year"},
    {"id": "zodiacal_releasing", "name": "Zodiacal Releasing", "tradition": "hellenistic", "description": "Time lord technique from Vettius Valens using Lot of Spirit/Fortune"},
    {"id": "lots", "name": "Lots / Arabic Parts", "tradition": "hellenistic", "description": "Calculated points from planet pairs + ascendant"},
    {"id": "transits", "name": "Transits", "tradition": "universal", "description": "Current planetary positions aspecting natal chart"},
    {"id": "houses", "name": "House Rulership", "tradition": "hellenistic", "description": "Tracing house lords to their sign/house placement"},
    {"id": "depositors", "name": "Depositor Chains", "tradition": "hellenistic", "description": "Following rulership chains to find final dispositor"},
    {"id": "synastry", "name": "Synastry", "tradition": "universal", "description": "Chart comparison for relationships"},
]

# ── Interpretive Layers ──
LAYERS = [
    {"id": "technical", "name": "Technical", "color": "cyan", "description": "Hellenistic technique: dignities, sect, houses, aspects, lots, time-lords"},
    {"id": "psychological", "name": "Psychological", "color": "magenta", "description": "Depth psychology: drives, complexes, attachment, shadow, individuation"},
    {"id": "archetypal", "name": "Archetypal", "color": "yellow", "description": "Jungian archetypes, mythology, collective unconscious, synchronicity"},
    {"id": "philosophical", "name": "Philosophical", "color": "blue", "description": "Stoic fate, free will, determinism, ethics of astrology"},
    {"id": "reference", "name": "Reference", "color": "green", "description": "Practical delineations by planet × sign × house × aspect"},
]

# ── Triplicity rulers (Dorothean system) ──
TRIPLICITIES = {
    # element: (day_ruler, night_ruler, participating_ruler)
    "fire": ("sun", "jupiter", "saturn"),
    "earth": ("venus", "moon", "mars"),
    "air": ("saturn", "mercury", "jupiter"),
    "water": ("venus", "mars", "moon"),  # Mars by night per Dorotheus
}

# ── Detriment relationships (opposite of domicile) ──
DETRIMENTS = {
    "sun": "aquarius", "moon": "capricorn",
    "mercury": "sagittarius",  # also pisces
    "venus": "aries",  # also scorpio
    "mars": "taurus",  # also libra
    "jupiter": "gemini",  # also virgo
    "saturn": "cancer",  # also leo
}
# Second detriment for planets with two domiciles
DETRIMENTS_2 = {
    "mercury": "pisces",
    "venus": "scorpio",
    "mars": "libra",
    "jupiter": "virgo",
    "saturn": "leo",
}

# ── Fall relationships (opposite of exaltation) ──
FALLS = {
    "sun": "libra", "moon": "scorpio",
    "mercury": "pisces", "venus": "virgo",
    "mars": "cancer", "jupiter": "capricorn",
    "saturn": "aries",
}


def build_structural_graph(driver):
    """Phase 2: Create all structural nodes and relationships."""

    with driver.session() as session:
        print("[Phase 2] Building structural graph...")

        # ── Constraints & indexes ──
        print("  Creating constraints...")
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Planet) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sign) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (h:House) REQUIRE h.number IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Aspect) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Technique) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Layer) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (au:Author) REQUIRE au.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interpretation) REQUIRE i.chunk_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chart) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Element) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Modality) REQUIRE m.id IS UNIQUE",
        ]
        for c in constraints:
            session.run(c)

        # ── Elements & Modalities ──
        print("  Creating elements & modalities...")
        for elem in ["fire", "earth", "air", "water"]:
            session.run("MERGE (e:Element {id: $id}) SET e.name = $name",
                       id=elem, name=elem.title())
        for mod in ["cardinal", "fixed", "mutable"]:
            session.run("MERGE (m:Modality {id: $id}) SET m.name = $name",
                       id=mod, name=mod.title())

        # ── Planets ──
        print(f"  Creating {len(PLANETS)} planets...")
        for p in PLANETS:
            session.run("""
                MERGE (p:Planet {id: $id})
                SET p.name = $name, p.type = $type, p.sect = $sect, p.symbol = $symbol
            """, **p)

        # ── Signs ──
        print(f"  Creating {len(SIGNS)} signs...")
        for s in SIGNS:
            session.run("""
                MERGE (s:Sign {id: $id})
                SET s.name = $name, s.element = $element, s.modality = $modality,
                    s.polarity = $polarity, s.number = $number, s.symbol = $symbol
            """, **{k: v for k, v in s.items() if k not in ("ruler", "exalt_ruler")})

            # Sign → Element
            session.run("""
                MATCH (s:Sign {id: $sign_id}), (e:Element {id: $elem})
                MERGE (s)-[:OF_ELEMENT]->(e)
            """, sign_id=s["id"], elem=s["element"])

            # Sign → Modality
            session.run("""
                MATCH (s:Sign {id: $sign_id}), (m:Modality {id: $mod})
                MERGE (s)-[:OF_MODALITY]->(m)
            """, sign_id=s["id"], mod=s["modality"])

            # Domicile: Planet -[:RULES]-> Sign
            session.run("""
                MATCH (p:Planet {id: $ruler}), (s:Sign {id: $sign_id})
                MERGE (p)-[:RULES {type: 'domicile'}]->(s)
            """, ruler=s["ruler"], sign_id=s["id"])

            # Detriment: Planet -[:DETRIMENT_IN]-> Sign (opposite of domicile)
            # Handled below

            # Exaltation: Planet -[:EXALTED_IN]-> Sign
            if s["exalt_ruler"]:
                session.run("""
                    MATCH (p:Planet {id: $ruler}), (s:Sign {id: $sign_id})
                    MERGE (p)-[:EXALTED_IN]->(s)
                """, ruler=s["exalt_ruler"], sign_id=s["id"])

        # ── Detriment relationships ──
        print("  Creating detriment relationships...")
        for planet_id, sign_id in DETRIMENTS.items():
            session.run("""
                MATCH (p:Planet {id: $planet}), (s:Sign {id: $sign})
                MERGE (p)-[:DETRIMENT_IN]->(s)
            """, planet=planet_id, sign=sign_id)
        for planet_id, sign_id in DETRIMENTS_2.items():
            session.run("""
                MATCH (p:Planet {id: $planet}), (s:Sign {id: $sign})
                MERGE (p)-[:DETRIMENT_IN]->(s)
            """, planet=planet_id, sign=sign_id)

        # ── Fall relationships ──
        print("  Creating fall relationships...")
        for planet_id, sign_id in FALLS.items():
            session.run("""
                MATCH (p:Planet {id: $planet}), (s:Sign {id: $sign})
                MERGE (p)-[:FALL_IN]->(s)
            """, planet=planet_id, sign=sign_id)

        # ── Triplicity rulers ──
        print("  Creating triplicity relationships...")
        for element, (day, night, participating) in TRIPLICITIES.items():
            # Get all signs of this element
            result = session.run(
                "MATCH (s:Sign) WHERE s.element = $elem RETURN s.id AS sign_id",
                elem=element,
            )
            sign_ids = [r["sign_id"] for r in result]
            for sign_id in sign_ids:
                session.run("""
                    MATCH (p:Planet {id: $planet}), (s:Sign {id: $sign})
                    MERGE (p)-[:TRIPLICITY_RULER {sect: 'day'}]->(s)
                """, planet=day, sign=sign_id)
                session.run("""
                    MATCH (p:Planet {id: $planet}), (s:Sign {id: $sign})
                    MERGE (p)-[:TRIPLICITY_RULER {sect: 'night'}]->(s)
                """, planet=night, sign=sign_id)
                session.run("""
                    MATCH (p:Planet {id: $planet}), (s:Sign {id: $sign})
                    MERGE (p)-[:TRIPLICITY_RULER {sect: 'participating'}]->(s)
                """, planet=participating, sign=sign_id)

        # ── Houses ──
        print(f"  Creating {len(HOUSES)} houses...")
        for h in HOUSES:
            session.run("""
                MERGE (h:House {number: $number})
                SET h.name = $name, h.modern_name = $modern, h.angular_status = $angular,
                    h.topics = $topics
            """, **{k: v for k, v in h.items() if k != "joy"})

            # Planetary joy
            if h["joy"]:
                session.run("""
                    MATCH (p:Planet {id: $planet}), (h:House {number: $house})
                    MERGE (p)-[:JOY_IN]->(h)
                """, planet=h["joy"], house=h["number"])

            # Natural sign rulership (Aries=1, Taurus=2, etc.)
            matching_sign = SIGNS[h["number"] - 1]
            session.run("""
                MATCH (s:Sign {id: $sign}), (h:House {number: $house})
                MERGE (s)-[:NATURAL_HOUSE]->(h)
            """, sign=matching_sign["id"], house=h["number"])

        # ── Sign oppositions (for aspect geometry) ──
        print("  Creating sign oppositions...")
        for i, s in enumerate(SIGNS):
            opposite = SIGNS[(i + 6) % 12]
            session.run("""
                MATCH (s1:Sign {id: $s1}), (s2:Sign {id: $s2})
                MERGE (s1)-[:OPPOSES]->(s2)
            """, s1=s["id"], s2=opposite["id"])

        # ── Aspects ──
        print(f"  Creating {len(ASPECTS)} aspects...")
        for a in ASPECTS:
            session.run("""
                MERGE (a:Aspect {id: $id})
                SET a.name = $name, a.degrees = $degrees, a.quality = $quality, a.symbol = $symbol
            """, **a)

        # ── Techniques ──
        print(f"  Creating {len(TECHNIQUES)} techniques...")
        for t in TECHNIQUES:
            session.run("""
                MERGE (t:Technique {id: $id})
                SET t.name = $name, t.tradition = $tradition, t.description = $description
            """, **t)

        # ── Layers ──
        print(f"  Creating {len(LAYERS)} interpretive layers...")
        for l in LAYERS:
            session.run("""
                MERGE (l:Layer {id: $id})
                SET l.name = $name, l.color = $color, l.description = $description
            """, **l)

        # ── Sect teams ──
        print("  Creating sect relationships...")
        session.run("""
            MATCH (s:Planet {id: 'sun'}), (j:Planet {id: 'jupiter'}), (sa:Planet {id: 'saturn'})
            MERGE (s)-[:SECT_TEAM {role: 'light'}]->(:SectTeam:Diurnal {id: 'diurnal'})
            MERGE (j)-[:SECT_TEAM {role: 'benefic'}]->(:SectTeam:Diurnal {id: 'diurnal'})
            MERGE (sa)-[:SECT_TEAM {role: 'malefic'}]->(:SectTeam:Diurnal {id: 'diurnal'})
        """)
        session.run("""
            MATCH (m:Planet {id: 'moon'}), (v:Planet {id: 'venus'}), (ma:Planet {id: 'mars'})
            MERGE (m)-[:SECT_TEAM {role: 'light'}]->(:SectTeam:Nocturnal {id: 'nocturnal'})
            MERGE (v)-[:SECT_TEAM {role: 'benefic'}]->(:SectTeam:Nocturnal {id: 'nocturnal'})
            MERGE (ma)-[:SECT_TEAM {role: 'malefic'}]->(:SectTeam:Nocturnal {id: 'nocturnal'})
        """)

        # Count what we built
        result = session.run("MATCH (n) RETURN count(n) AS nodes")
        nodes = result.single()["nodes"]
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS rels")
        rels = result.single()["rels"]
        print(f"\n[Phase 2 complete] {nodes} nodes, {rels} relationships")


# ══════════════════════════════════════════════════════════════
# PHASE 3: KNOWLEDGE MIGRATION — ChromaDB chunks → Graph nodes
# ══════════════════════════════════════════════════════════════

def migrate_knowledge(driver):
    """Phase 3: Transform ChromaDB chunks into graph Interpretation nodes."""
    import chromadb

    class NoOpEmbedding(chromadb.EmbeddingFunction):
        def __call__(self, input):
            return [[0.0] * 1536 for _ in input]

    print("\n[Phase 3] Migrating knowledge from ChromaDB...")
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = chroma.get_collection("astro_knowledge", embedding_function=NoOpEmbedding())

    total = collection.count()
    print(f"  Source: {total} chunks in ChromaDB")

    # ── Create authors first ──
    batch_size = 100
    offset = 0
    authors_seen = set()
    chunks_migrated = 0

    with driver.session() as session:
        while offset < total:
            results = collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas", "embeddings"],
            )

            if not results["ids"]:
                break

            for i, (chunk_id, doc, meta, embedding) in enumerate(zip(
                results["ids"],
                results["documents"],
                results["metadatas"],
                results["embeddings"] if results["embeddings"] is not None else [None] * len(results["ids"]),
            )):
                author = meta.get("source_author", "unknown")
                title = meta.get("source_title", "unknown")
                layer = meta.get("layer", "reference")
                trust_tier = meta.get("trust_tier", 4)
                tradition = meta.get("tradition", "")

                # Create Author node
                if author not in authors_seen:
                    session.run("""
                        MERGE (a:Author {name: $name})
                    """, name=author)
                    authors_seen.add(author)

                # Create Interpretation node with embedding
                session.run("""
                    MERGE (i:Interpretation {chunk_id: $chunk_id})
                    SET i.text = $text,
                        i.source_title = $title,
                        i.trust_tier = $tier,
                        i.tradition = $tradition,
                        i.embedding = $embedding
                """, chunk_id=chunk_id, text=doc, title=title,
                     tier=trust_tier, tradition=tradition,
                     embedding=embedding)

                # Link to Author
                session.run("""
                    MATCH (i:Interpretation {chunk_id: $chunk_id}),
                          (a:Author {name: $author})
                    MERGE (i)-[:AUTHORED_BY]->(a)
                """, chunk_id=chunk_id, author=author)

                # Link to Layer
                session.run("""
                    MATCH (i:Interpretation {chunk_id: $chunk_id}),
                          (l:Layer {id: $layer})
                    MERGE (i)-[:IN_LAYER]->(l)
                """, chunk_id=chunk_id, layer=layer)

                # ── Link to entities from metadata tags ──

                # Planets
                planets_str = meta.get("planets", "")
                if planets_str:
                    for planet_tag in planets_str.split(","):
                        planet_tag = planet_tag.strip().lower()
                        if planet_tag:
                            session.run("""
                                MATCH (i:Interpretation {chunk_id: $chunk_id}),
                                      (p:Planet {id: $planet})
                                MERGE (i)-[:DESCRIBES]->(p)
                            """, chunk_id=chunk_id, planet=planet_tag)

                # Signs
                signs_str = meta.get("signs", "")
                if signs_str:
                    for sign_tag in signs_str.split(","):
                        sign_tag = sign_tag.strip().lower()
                        if sign_tag:
                            session.run("""
                                MATCH (i:Interpretation {chunk_id: $chunk_id}),
                                      (s:Sign {id: $sign})
                                MERGE (i)-[:DESCRIBES]->(s)
                            """, chunk_id=chunk_id, sign=sign_tag)

                # Houses
                houses_str = meta.get("houses", "")
                if houses_str:
                    for house_tag in houses_str.split(","):
                        house_tag = house_tag.strip()
                        if house_tag.isdigit():
                            session.run("""
                                MATCH (i:Interpretation {chunk_id: $chunk_id}),
                                      (h:House {number: $house})
                                MERGE (i)-[:DESCRIBES]->(h)
                            """, chunk_id=chunk_id, house=int(house_tag))

                # Aspects
                aspects_str = meta.get("aspects", "")
                if aspects_str:
                    for aspect_tag in aspects_str.split(","):
                        aspect_tag = aspect_tag.strip().lower()
                        if aspect_tag:
                            session.run("""
                                MATCH (i:Interpretation {chunk_id: $chunk_id}),
                                      (a:Aspect {id: $aspect})
                                MERGE (i)-[:DESCRIBES]->(a)
                            """, chunk_id=chunk_id, aspect=aspect_tag)

                # Techniques
                techniques_str = meta.get("techniques", "")
                if techniques_str:
                    for tech_tag in techniques_str.split(","):
                        tech_tag = tech_tag.strip().lower()
                        if tech_tag:
                            session.run("""
                                MATCH (i:Interpretation {chunk_id: $chunk_id}),
                                      (t:Technique {id: $tech})
                                MERGE (i)-[:DESCRIBES]->(t)
                            """, chunk_id=chunk_id, tech=tech_tag)

                chunks_migrated += 1

            offset += batch_size
            print(f"  Migrated {chunks_migrated}/{total} chunks...", end="\r")

        print(f"\n  Authors: {len(authors_seen)}")

        # Final counts
        result = session.run("MATCH (n) RETURN count(n) AS nodes")
        nodes = result.single()["nodes"]
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS rels")
        rels = result.single()["rels"]
        result = session.run("MATCH (i:Interpretation) RETURN count(i) AS interps")
        interps = result.single()["interps"]
        result = session.run("MATCH (i:Interpretation)-[:DESCRIBES]->() RETURN count(*) AS links")
        links = result.single()["links"]

        print(f"\n[Phase 3 complete]")
        print(f"  Total nodes: {nodes}")
        print(f"  Total relationships: {rels}")
        print(f"  Interpretation nodes: {interps}")
        print(f"  Entity links (DESCRIBES): {links}")


def verify_graph(driver):
    """Run verification queries to confirm the graph is correct."""
    print("\n[Verification]")
    with driver.session() as session:
        queries = [
            ("Planets", "MATCH (p:Planet) RETURN count(p) AS n"),
            ("Signs", "MATCH (s:Sign) RETURN count(s) AS n"),
            ("Houses", "MATCH (h:House) RETURN count(h) AS n"),
            ("Aspects", "MATCH (a:Aspect) RETURN count(a) AS n"),
            ("Techniques", "MATCH (t:Technique) RETURN count(t) AS n"),
            ("Layers", "MATCH (l:Layer) RETURN count(l) AS n"),
            ("Authors", "MATCH (a:Author) RETURN count(a) AS n"),
            ("Interpretations", "MATCH (i:Interpretation) RETURN count(i) AS n"),
            ("RULES rels", "MATCH ()-[r:RULES]->() RETURN count(r) AS n"),
            ("EXALTED_IN rels", "MATCH ()-[r:EXALTED_IN]->() RETURN count(r) AS n"),
            ("DETRIMENT_IN rels", "MATCH ()-[r:DETRIMENT_IN]->() RETURN count(r) AS n"),
            ("FALL_IN rels", "MATCH ()-[r:FALL_IN]->() RETURN count(r) AS n"),
            ("TRIPLICITY rels", "MATCH ()-[r:TRIPLICITY_RULER]->() RETURN count(r) AS n"),
            ("DESCRIBES rels", "MATCH ()-[r:DESCRIBES]->() RETURN count(r) AS n"),
            ("AUTHORED_BY rels", "MATCH ()-[r:AUTHORED_BY]->() RETURN count(r) AS n"),
            ("IN_LAYER rels", "MATCH ()-[r:IN_LAYER]->() RETURN count(r) AS n"),
        ]

        for label, query in queries:
            result = session.run(query)
            n = result.single()["n"]
            print(f"  {label}: {n}")

        # Sample: Mars rules what?
        print("\n  Sample: Mars rules...")
        result = session.run("""
            MATCH (p:Planet {id: 'mars'})-[:RULES]->(s:Sign)
            RETURN s.name AS sign
        """)
        for r in result:
            print(f"    → {r['sign']}")

        # Sample: What describes Saturn?
        print("\n  Sample: Top 3 interpretations mentioning Saturn...")
        result = session.run("""
            MATCH (i:Interpretation)-[:DESCRIBES]->(p:Planet {id: 'saturn'}),
                  (i)-[:IN_LAYER]->(l:Layer),
                  (i)-[:AUTHORED_BY]->(a:Author)
            RETURN a.name AS author, l.id AS layer, left(i.text, 100) AS excerpt
            LIMIT 3
        """)
        for r in result:
            print(f"    [{r['layer']}] {r['author']}: {r['excerpt']}...")


if __name__ == "__main__":
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    try:
        driver.verify_connectivity()
        print(f"Connected to Neo4j at {NEO4J_URI}\n")

        if "--phase2-only" in sys.argv:
            build_structural_graph(driver)
        elif "--phase3-only" in sys.argv:
            migrate_knowledge(driver)
        elif "--verify" in sys.argv:
            verify_graph(driver)
        else:
            build_structural_graph(driver)
            migrate_knowledge(driver)
            verify_graph(driver)

    finally:
        driver.close()
