# Selene Changelog

## 2026-02-02 — The Three-Axis Report System

### Major Features

**3-Axis Chart Reading System**
The `chart_reading` tool now operates on three independent axes:
- **Type** (the medium): `technical` | `narrative` | `poem`
- **Framework** (the lens): `psychological` | `deterministic` | `hellenistic` | `stoic` | `mythological`
- **Size** (the depth): `xs` | `s` | `m` | `l` | `xl`

75 possible combinations from a single chart. Each axis is independently configurable.

**Derivative Houses (Pelletier System)**
- `compute_derivative_houses(chart_data)` computes house-to-house relationships for every planet
- Formula: `(origin - target) % 12 + 1` (clockwise/Pelletier method)
- Asymmetric pairs always sum to 14
- Grouped by aspect geometry (conjunction, semisextile, sextile, square, trine, quincunx, opposition)
- Key connections identified: dignified planets to angular houses
- Pelletier's interpretations queried from ChromaDB for each key connection
- Integrated into `full_chart_computation()` and `_gather_knowledge_for_chart()`

**Dignity-Weighted Narrative Priority**
- Automatically analyzes chart ruler condition vs. strongest planets by dignity score
- Generates priority instructions injected into every reading
- Weak/peregrine chart ruler → ASC archetype treated as CONDITIONAL
- Strongest planet by dignity score gets most narrative weight
- Debilitated planets' shadows named directly (not softened)
- Central narrative tension = gap between ASC mask and dominant planet's reality

**Legacy Chart Format Normalization**
- `_normalize_legacy_chart()` converts old format (dict-keyed planets, string angles) to Helios format
- Handles charts imported before Helios integration
- Infers sect from Sun house position when not present

### New Constants
- `REPORT_TYPES` — 3 report types with full LLM instructions
- `FRAMEWORKS` — 5 interpretive frameworks (expanded from 2 `PERSPECTIVES`)
- `DERIVATIVE_HOUSES` — meanings for all 12 derivative positions
- `ASPECT_GEOMETRY` — 7 geometric relationship types
- `ANGULAR_HOUSES` — {1, 4, 7, 10}
- `PERSPECTIVES` maintained as legacy alias → `FRAMEWORKS`

### New Files
- `elections/2026-elections-brennan-schaim.pdf` — Brennan & Schaim electional report
- `elections/2026-elections-chart-data.pdf` — Chart data for elections
- `elections/2026-elections-summary.md` — Quick reference: all 24 elections + planetary events
- `reports/robin-natal-reading.md` — Robin's natal chart (first reading from new system)
- `reports/lisa-natal-reading.md` — Lisa's natal (narrative, psychological, M)
- `reports/lisa-natal-reading-v2.md` — Lisa's natal (calibrated dignity weighting)
- `reports/lisa-xl-technical.md` — Lisa's natal (technical, psychological, XL)

### Calibration Lessons
- Dignity score should drive narrative weight more than ASC archetype
- A peregrine/debilitated chart ruler delivers its sign's qualities CONDITIONALLY
- Leo ASC + peregrine Sun + Moon domicile 12H = warmth only when emotionally settled or externally recognized
- Mercury detriment = "jumps to conclusions," not "broad thinking" — name shadows directly
- Feedback from real people who know the chart subject is the ultimate calibration tool

### Future Roadmap (parked)
- **Evolutionary Astrology framework** — Pluto polarity point, nodal story, skipped steps
- **Archetypal Astrology framework** — Tarnas, outer planet cycle tracking
- **Framework-specific computation adjuncts** — extra data computed per framework
- **"What the chart wants" auto-detection** — scoring function recommends framework from chart signatures
- **Interactive Telegram flow** — inline buttons for chart selection → type → framework → size
- **Transit query language** — deeper drilling into specific transit periods
- **Full transit cycle tracking** — complete planetary return cycles
