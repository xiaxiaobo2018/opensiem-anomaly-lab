# Data Processing

## Purpose

This document explains the baseline data workflow used in OpenSIEM Anomaly Lab for the `AnoMod` dataset.

The first baseline focuses on:

- using a local metric cache for fast iteration, with GCS as fallback
- discovering scenario-level metric files
- building timestamp-level feature vectors from Prometheus-style metrics
- training a first unsupervised anomaly detector
- evaluating how well anomalous scenarios separate from the normal run

## Current Workflow Overview

The current baseline has four stages:

1. `scripts/ingest_anomod.py`
   - discover local cached metric CSVs first, or fall back to GCS
   - build a manifest of scenario labels
2. `scripts/sync_anomod_metrics_from_gcs.py`
   - refresh the local metric cache from GCS when needed
3. `scripts/prepare_features.py`
   - read metric CSVs scenario by scenario
   - aggregate repeated metric series at each timestamp
   - pivot the metrics into a model-ready feature table
4. `scripts/train.py`
   - train an `IsolationForest` on normal windows only
5. `scripts/evaluate.py`
   - score held-out normal windows and all anomalous windows
   - save metrics and per-scenario anomaly summaries

## AnoMod Input Assumptions

The baseline currently uses `TT_data/metric_data/*/*.csv` from either:

- local cache: `data/raw/anomod/TT_data/metric_data/`
- `gs://opensiem-data-xia0b0/raw/anomod`

Each scenario folder represents one run, such as:

- `Normal_case_em_...`
- `Lv_P_CPU_preserve_...`
- `Lv_D_TRANSACTION_timeout_...`

The metric CSVs contain repeated measurements for metric names such as CPU, memory, network, and container health indicators.

## Ingestion Decisions

### 1. Use scenario folders as labels

AnoMod already encodes run-level context in folder names.

The baseline converts that into:

- `is_anomaly`
- `fault_family`
- `fault_type`
- `fault_label`

`Normal_case...` is treated as normal traffic. All `Lv_*` runs are treated as anomalous.

### 2. Use a hybrid raw-data setup

The raw AnoMod metric files are treated this way:

- local cache for normal development runs
- GCS as canonical backup and fallback

The pipeline prefers local files whenever they exist.

Why:

- avoids keeping multi-gigabyte raw data on the laptop
- keeps development fast once the cache exists
- keeps the dataset location stable across machines
- makes it easier to move preprocessing or training onto cloud compute later

### 3. Focus on metric data first

AnoMod also contains traces, logs, API responses, and coverage artifacts.

The first local baseline intentionally uses only metrics because they are:

- structured
- lightweight enough for local iteration
- already aligned to anomaly detection

This keeps the first model simple and reproducible.

## Feature Preparation Decisions

### 1. One observation per scenario timestamp

The raw CSVs contain many rows per timestamp because each metric can appear across multiple series and labels.

To build a baseline table, the pipeline groups by:

- scenario metadata
- timestamp
- metric name

Then it computes:

- `mean`
- `std`
- `min`
- `max`

for each metric at that timestamp.

### 2. Pivot metric summaries into columns

After aggregation, the pipeline pivots the data so each row becomes one timestamp window and each feature column becomes a `stat__metric_name` pair.

Examples:

- `mean__container_memory_usage_bytes`
- `max__node_network_receive_bytes_total`
- `std__rate_node_cpu_seconds_total_5m`

Missing values are filled with `0` after the pivot step.

## Modeling Decisions

### 1. Unsupervised first model

The first baseline uses `IsolationForest`.

Why:

- it matches the anomaly-detection framing
- it does not require multiclass supervised labels
- it gives a simple starting point before trying more specialized models

### 2. Train only on normal windows

The normal scenario is sorted by timestamp and split chronologically:

- first 70% for training
- remaining 30% for evaluation

All anomalous scenario windows are included in evaluation only.

This gives a simple baseline for answering:

- can the model learn the normal metric profile?
- do anomalous runs drift away from that profile?

## Outputs

The current pipeline writes:

- `data/processed/anomod_metric_manifest.csv`
- `data/processed/anomod_metric_features.csv`
- `data/processed/anomod_isolation_forest.joblib`
- `data/processed/anomod_train_scores.csv`
- `data/processed/anomod_evaluation_scores.csv`
- `data/processed/anomod_scenario_summary.csv`
- `data/processed/anomod_evaluation_metrics.json`

## Caveats

This is a true baseline, not the final intended pipeline.

Known simplifications:

- processed outputs are still local
- only metric data is used
- labels come from scenario folders, not fault onset timestamps
- the model does not yet explain anomalies
- traces, logs, and root-cause annotations are not yet fused in

Those are good next steps once the baseline is stable.
