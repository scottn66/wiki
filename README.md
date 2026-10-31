# wiki — source scrapers for LLM knowledge ingest

Three complementary Python scrapers for pulling structured, citeable content out of **Wikipedia**, the **Stanford Encyclopedia of Philosophy (SEP)**, and **arXiv** — the raw-sources layer of an RAG / LLM knowledge pipeline focused on cognitive science and its adjacent fields.

The goal is not "download the internet." Each source plays a distinct role in the evidence chain an LLM needs to answer a question well:

| Source | Role in the pipeline | Why |
|---|---|---|
| **Wikipedia** | Breadth + entity coverage | Dense inline hyperlink graph, canonical page keys, high recall |
| **SEP** | Concept backbone | Peer-reviewed, hand-curated `related_entries`, highest signal-per-page for philosophy-of-mind topics |
| **arXiv** | Primary-source verification | Direct access to recent research PDFs in CS/AI/math/neuroscience |

Each scraper is fetch-primitive first, synthesis-later — the output is structured JSON (or SQLite) that higher layers can render into markdown, index into a vector store, or feed into an LLM's retrieval context.

## Contents

| File | Purpose |
|---|---|
| [`sitehopper3_basic.py`](sitehopper3_basic.py) | **The grown-up Wikipedia scraper.** Canonical key normalization, SQLite `pages`/`edges` store, bounded BFS crawl, real + fake scraper pair for deterministic offline testing, argparse CLI. |
| [`wikiFetcher.py`](wikiFetcher.py) | Title-list Wikipedia fetcher with a strong 6-point soup validator (HTTP status, `noarticletext`, missing h1, missing `mw-parser-output`, empty paragraphs, disambig category filter) and section-aware content extraction. |
| [`wikiSearch.py`](wikiSearch.py) | Keyword-driven MediaWiki search wrapper that builds a shallow 1-hop page graph in memory. Defensive: content-type check, JSON decode fallback, request timeouts. |
| [`plato.py`](plato.py) | SEP scraper. Extracts title, section content keyed by heading, initial preamble paragraph, and the explicit hand-curated `related_entries` cross-reference list. Includes a `DBreader` query layer over the saved cache. |
| [`read_plato.py`](read_plato.py) | NLTK post-processor that builds a lexicon and bigram distribution from the cached SEP content. Demonstrates the "scraper writes JSON → analyzer reads JSON" pattern. |
| [`arxiv.py`](arxiv.py) | arXiv Atom API scraper driven by category keys. Downloads PDFs + persists metadata. |

## Quickstart

```bash
# 1. Clone and set up
git clone https://github.com/scottn66/wiki.git
cd wiki
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Wikipedia — bounded crawl from a seed article
python sitehopper3_basic.py --mode live --start-page "Cognitive_science" --depth 2 --max-connections 8

# 3. Wikipedia — deterministic offline testing (no network)
python sitehopper3_basic.py --mode fake --start-page "Cognitive_science" --depth 3

# 4. SEP — single-article fetch by URL slug
python -c "from plato import SepFetcher; SepFetcher().fetch_sep_article_named('cognitive-science/')"

# 5. arXiv — most-recent papers in a category
python arxiv.py  # defaults to 3 recent AI papers; edit category_key in __main__
```

## Architecture notes

All three scrapers share the same broad shape — fetch, validate, extract, persist, dedup — but solve different sub-problems per source:

```
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  sitehopper3_basic  │   │       plato         │   │       arxiv         │
│  (Wikipedia)        │   │       (SEP)         │   │      (arXiv)        │
├─────────────────────┤   ├─────────────────────┤   ├─────────────────────┤
│ HTML via requests   │   │ HTML via requests   │   │ Atom XML via        │
│ + BeautifulSoup     │   │ + BeautifulSoup     │   │ feedparser          │
│                     │   │                     │   │                     │
│ canonical_page_key  │   │ related_entries     │   │ arxiv_id            │
│ + edges table       │   │ + initial_paragraph │   │ + category index    │
│                     │   │                     │   │                     │
│ SQLite store        │   │ JSON metadata       │   │ JSON metadata       │
│ + bounded BFS       │   │ + DBreader query    │   │ + PDF downloads     │
│ + fake scraper      │   │   layer             │   │                     │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
         │                           │                         │
         └───────────────┬───────────┴─────────────┬────────────┘
                         │                         │
                         ▼                         ▼
                   raw source cache         future: unified
                   (one per source)         Source schema →
                                            markdown emitter
                                            → LLM context
```

### Design choices worth calling out

- **Wikipedia**: canonical page keys solve the "is `Cognitive_science` the same as `cognitive science`?" problem at ingest time instead of at query time. The `pages`/`edges` SQLite schema gives you a real directed graph for BFS crawls and backlink lookups without standing up a graph DB.
- **Wikipedia**: the `WikipediaScraper` / `FakeWikipediaScraper` pair lets the crawler run deterministically offline for testing or demos — no network, same output shape.
- **Wikipedia validation** (in `wikiFetcher.py`) is intentionally strict: any of the 6 checks can fail a page, and each failure returns a reason string. This keeps bad content (disambig pages, deleted articles, empty stubs) out of the cache rather than polluting downstream steps.
- **SEP** doesn't have a formal API, so the scraper is pure HTML. What saves it is SEP's hand-curated `<div id="related-entries">` — you get an explicit, editor-approved citation graph for free. This is why SEP is the cheapest-per-page but highest-signal source in the stack.
- **arXiv's** Atom API exposes metadata only — no references, no citation graph. To reconstruct the inbound/outbound citation network you need an external bridge (e.g. Semantic Scholar) or full PDF reference extraction. This is an intentional limit of the current design, not an oversight.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Required packages: `requests`, `beautifulsoup4`, `feedparser`, `wikipedia-api`, `PyPDF2`, `networkx`, `SPARQLWrapper`, `nltk`, `numpy`, `matplotlib`, `tqdm`.

Tested on Python 3.10+.

## Politeness

All three scrapers identify themselves via a shared user-agent string (`CogSciWikiBot/0.1 (https://github.com/scottn66/wiki; ...)`) and use explicit request timeouts. `sitehopper3_basic.py` respects a configurable `max_connections` cap per hop to avoid hammering Wikipedia. Please be kind to the servers you scrape — particularly SEP, which is a small academic resource.

## Status

- `sitehopper3_basic.py`: mature. Canonicalization, graph store, CLI, fake-mode testing.
- `wikiFetcher.py`: defensive, strongly validated. The validator is the model for how future scrapers should check their inputs.
- `wikiSearch.py`: defensive, side-effect free on import.
- `plato.py`: working, polite (shared user-agent), basic validation.
- `arxiv.py`: working, polite, side-effect free on import. PDF reference extraction is future work.

## What's next

A unified `Source` record schema so all three scrapers emit into the same shape, plus a markdown-emitter layer that turns `Source` records into Obsidian-flavored pages suitable for an LLM knowledge wiki. The long game is a verifiable, compounding knowledge base for cognitive science that bridges philosophical theory (SEP), encyclopedic breadth (Wikipedia), and empirical grounding (arXiv).

---

*Author: Scott Nelson · [scottn66.github.io](https://scottn66.github.io) · [github.com/scottn66](https://github.com/scottn66)*

## Lane

This repo is the **reference/ancestor lane** for source fetching: the original Wikipedia,
SEP and arXiv scrapers, kept as working portfolio code. New source or adapter work, and the
"What's next" ideas above, are carried on in other projects. This repo is not expected to
grow new sources.
