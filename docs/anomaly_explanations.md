# Anomaly Explanations

## Purpose

This document explains the Week 3 explanation layer for OpenSIEM Anomaly Lab.

The goal is to connect three pieces:

1. anomaly scores from the metric baseline
2. retrieved log evidence from the Week 2 search index
3. an LLM-generated plain-English explanation

## High-Level Flow

The explanation pipeline works like this:

1. run the anomaly baseline evaluation
2. select the top anomalous scenarios from `anomod_scenario_summary.csv`
3. retrieve supporting service-log and Kubernetes-event chunks from the Week 2 index
4. send the anomaly summary plus retrieved evidence to Gemini on Vertex AI
5. save the resulting explanations to local processed artifacts

## Commands

Build the Week 2 retrieval index first:

```bash
uv run scripts/build_log_search_index.py
```

Then run evaluation with explanations enabled:

```bash
uv run scripts/evaluate.py --with-explanations
```

You can also rerun just the explanation layer:

```bash
uv run scripts/explain_anomalies.py --top-k-scenarios 3 --retrieval-top-k 6
```

## LLM Runtime

The current Week 3 implementation uses:

- Gemini on Vertex AI
- the existing Node SDK dependency already present in this repo: `@google/genai`
- Application Default Credentials plus the active `gcloud` project when explicit env vars are not set

The Python pipeline calls a small Node helper script so the main anomaly pipeline can stay Python-first without adding a separate Python LLM SDK.

## Outputs

When explanations are enabled, the pipeline writes:

- `data/processed/anomod_scenario_explanations.json`
- `data/processed/anomod_scenario_explanations.md`

Each explanation record includes:

- scenario metadata
- anomaly summary statistics
- retrieved supporting evidence
- the final plain-English explanation

## Caveats

This is an early RAG explanation layer, not a final analyst workflow.

Current limitations:

- retrieval is still based on local latent-semantic vectors rather than a hosted embedding store
- explanation quality depends on the retrieval quality
- the prompt is grounded in logs and Kubernetes events only
- traces and API responses are not yet included in the evidence bundle

Even with those limits, this is enough to satisfy the first Week 3 milestone:

- when an anomaly is detected, retrieve relevant context and pass it to an LLM for a plain-English explanation
