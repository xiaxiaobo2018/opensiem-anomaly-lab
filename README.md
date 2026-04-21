# OpenSIEM Anomaly Lab

A public cybersecurity/ML portfolio project for anomaly detection on public SIEM-like datasets. (Inspired by my internship)

## Goals

- Build a reproducible anomaly detection pipeline
- Use public or synthetic security data only
- Demonstrate ingestion, feature engineering, modeling, and evaluation

## Data Source

Current raw data source:

- `gs://opensiem-data-xia0b0/raw/anomod/TT_data/...`

Official dataset source:

- Zenodo DOI: https://doi.org/10.5281/zenodo.18342898
- Collection scripts: https://github.com/EvoTestOps/AnoMod

Citation:

- Ke Ping, Hamza Bin Mazhar, Yuqing Wang, Ying Song, and Mika V. Mantyla. 2026. *AnoMod: A Dataset for Anomaly Detection and Root Cause Analysis in Microservice Systems*. MSR '26. https://doi.org/10.1145/3793302.3793324

The repo now uses a hybrid raw-data workflow:

- local metric cache first: `data/raw/anomod/TT_data/metric_data/`
- GCS fallback/source of truth: `gs://opensiem-data-xia0b0/raw/anomod`
- processed outputs stay local in `data/processed/`

Before running the baseline, authenticate once:

```bash
gcloud auth application-default login
```

If the data ever moves, point the repo at the new location with:

```bash
export ANOMOD_GCS_PREFIX=gs://YOUR_BUCKET/raw/anomod
```

If you want to refresh the local metric cache from GCS:

```bash
uv run scripts/sync_anomod_metrics_from_gcs.py
```

## Planned Stack

- Python
- uv
- pandas
- scikit-learn
- SHAP
- pytest

## Week 2 Log Retrieval

The repo now includes a first local retrieval layer over `AnoMod` `TT_data/log_data`.

It builds a searchable corpus from service logs plus Kubernetes event JSON, then uses local latent-semantic vectors to return the most relevant chunks for a query.

Build the log index:

```bash
uv run scripts/build_log_search_index.py
```

Query it:

```bash
uv run scripts/search_logs.py "TokenException token expired"
uv run scripts/search_logs.py "connection pool exhaustion database timeout" --top-k 8
uv run scripts/search_logs.py "Readiness probe failed i/o timeout" --source-type kubernetes_event
```

Artifacts are written to `data/processed/`.
See `docs/log_retrieval.md` for details.

## Week 3 Anomaly Explanations

The repo now includes a first RAG-style explanation layer.

It takes scored anomalous scenarios, retrieves supporting log evidence from the Week 2 search index, and sends that context to Gemini on Vertex AI for a plain-English explanation.

Build the retrieval index first:

```bash
uv run scripts/build_log_search_index.py
```

Run evaluation with explanations enabled:

```bash
uv run scripts/evaluate.py --with-explanations
```

Or rerun only the explanation step:

```bash
uv run scripts/explain_anomalies.py --top-k-scenarios 3 --retrieval-top-k 6
```

See `docs/anomaly_explanations.md` for details.

## Baseline Pipeline

Run the first local baseline end to end with:

```bash
uv run scripts/sync_anomod_metrics_from_gcs.py
uv run scripts/ingest_anomod.py
uv run scripts/prepare_features.py
uv run scripts/train.py
uv run scripts/evaluate.py
```

You only need the sync step when the local metric cache is missing or stale.
Artifacts are written to `data/processed/`.

## Current Status

The repository now has:

- a first local baseline for AnoMod metric anomaly detection
- a first local semantic-search layer over AnoMod logs
- a first LLM-backed anomaly explanation workflow over retrieved log evidence

- ingestion builds a scenario manifest from the local metric cache when available, otherwise from GCS
- feature preparation converts metric timestamps into model-ready feature vectors
- training fits an `IsolationForest` on normal windows
- evaluation scores anomalous runs and writes metrics plus per-scenario summaries
- log retrieval builds searchable chunks from `TT_data/log_data`
- semantic search returns relevant log and Kubernetes-event evidence for fault-oriented queries
- explanation generation retrieves scenario evidence and writes plain-English anomaly summaries via Gemini on Vertex AI

The next major step is to enrich the baseline with traces, logs, root-cause signals, and model interpretation.
