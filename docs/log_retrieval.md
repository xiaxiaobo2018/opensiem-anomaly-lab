# Log Retrieval

## Purpose

This document explains the Week 2 retrieval layer for OpenSIEM Anomaly Lab.

The goal is to support semantic-style search over a sample SIEM corpus built from the `AnoMod` `TT_data/log_data` modality.

## What It Indexes

The current retrieval pipeline reads local AnoMod raw logs from:

- `data/raw/anomod/TT_data/log_data/`

It currently indexes two source types:

- service and pod `.log` files
- `kubernetes_events_*.json` event files

It does not yet index:

- `log_collection_report_*.json`
- traces
- API responses
- coverage artifacts

## Retrieval Design

The pipeline follows four steps:

1. Discover scenario folders under `TT_data/log_data`
2. Split each service log into timestamp-aware chunks so stack traces stay grouped
3. Convert each chunk into a vector using local latent-semantic embeddings
4. Search the saved vector index with a natural-language or keyword query

## Embedding Strategy

To keep Week 2 fully local and reproducible, the repo currently uses:

- `TfidfVectorizer`
- `TruncatedSVD`
- cosine similarity over normalized dense vectors

This is not yet a hosted embedding model or FAISS/Chroma deployment, but it does provide a practical local vector-search baseline over the AnoMod log corpus.

## Scripts

Build the index:

```bash
uv run scripts/build_log_search_index.py
```

Query the index:

```bash
uv run scripts/search_logs.py "TokenException token expired"
uv run scripts/search_logs.py "connection pool exhaustion database timeout" --top-k 8
uv run scripts/search_logs.py "Readiness probe failed i/o timeout" --source-type kubernetes_event
```

## Outputs

The build step writes:

- `data/processed/anomod_log_chunks.csv`
- `data/processed/anomod_log_search_index.joblib`

Each chunk keeps metadata such as:

- `scenario_name`
- `fault_family`
- `fault_type`
- `service_name`
- `source_type`
- `relative_path`

## Why This Matters

This gives the project its first retrieval layer over real AnoMod log evidence.

That unlocks the next step for Week 3:

- when an anomaly is detected, retrieve the most relevant log chunks
- pass those chunks into an LLM
- generate a plain-English anomaly explanation grounded in retrieved context
