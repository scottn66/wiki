# siteHopper v3 Notebook Layout

## Files
- `siteHopper3_core_refactor.ipynb`
  - Core refactor narrative and implementation (sections 1-10).
  - Includes utilities, SQLite property-graph store, batching, scraper/page abstractions, crawl builder, tests, benchmarks, and visualization.

- `siteHopper3_experiments.ipynb`
  - Experiment-focused notebook.
  - Includes core setup definitions plus advanced experiments (extended diagnostics, structure extraction, NER, reference counts, priority frontier).

## Suggested usage
1. Run `siteHopper3_core_refactor.ipynb` for stable architecture + baseline performance checks.
2. Use `siteHopper3_experiments.ipynb` for exploratory work and algorithm tuning.

Both notebooks keep the same kernel metadata (`Python (rag-wiki)`) as the source notebook.
