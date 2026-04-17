# Data README

This project now uses the `AnoMod` dataset as its main data source.

AnoMod is not just a single metrics file. It is a multi-modal anomaly detection and root-cause dataset collected from microservice systems under both normal and fault-injection scenarios.

## Quick Summary

| Item | Current status |
| --- | --- |
| Main dataset | `AnoMod` |
| Local raw cache | `data/raw/anomod/` |
| Cloud backup / source of truth | `gs://opensiem-data-xia0b0/raw/anomod` |
| Main system used by current baseline | `TT_data` |
| Main modality used by current baseline | `metric_data` |
| Processed outputs | `data/processed/` |

## Dataset Source

| Item | Value |
| --- | --- |
| Dataset name | `AnoMod: A Dataset for Anomaly Detection and Root Cause Analysis in Microservice Systems` |
| DOI | `https://doi.org/10.5281/zenodo.18342898` |
| Collection scripts | `https://github.com/EvoTestOps/AnoMod` |

Citation:

- Ke Ping, Hamza Bin Mazhar, Yuqing Wang, Ying Song, and Mika V. Mantyla. 2026. *AnoMod: A Dataset for Anomaly Detection and Root Cause Analysis in Microservice Systems*. MSR '26. https://doi.org/10.1145/3793302.3793324

## Storage Model In This Repo

This repo uses a hybrid workflow:

| Layer | Purpose | Location |
| --- | --- | --- |
| Local raw cache | Fast local development and repeated pipeline runs | `data/raw/anomod/` |
| Cloud backup / canonical copy | Durable storage and future cloud workflows | `gs://opensiem-data-xia0b0/raw/anomod` |
| Local processed artifacts | Features, model outputs, evaluation results | `data/processed/` |

### Practical meaning

- The pipeline prefers the local raw cache when it exists.
- If the local cache is missing, the repo can fall back to GCS.
- Processed outputs are kept local for fast iteration.

## High-Level Folder Layout

```text
data/
├── raw/
│   └── anomod/
│       ├── TT_data/
│       ├── SN_data/
│       └── __MACOSX/          # archive junk, not meaningful
└── processed/
    ├── anomod_metric_manifest.csv
    ├── anomod_metric_features.csv
    ├── anomod_isolation_forest.joblib
    ├── anomod_train_scores.csv
    ├── anomod_evaluation_scores.csv
    ├── anomod_scenario_summary.csv
    └── anomod_evaluation_metrics.json
```

## What AnoMod Contains

AnoMod contains data from two different microservice systems:

| Top-level folder | System | Notes |
| --- | --- | --- |
| `TT_data` | TrainTicket | This is what the current baseline uses |
| `SN_data` | SocialNetwork | Present locally, but not yet used in the baseline |

## Modalities In Each System

For each scenario, AnoMod collects multiple kinds of evidence:

| Modality | What it contains | Why it matters |
| --- | --- | --- |
| `metric_data` | Time-series metrics like CPU, memory, network, container stats | Best starting point for anomaly detection |
| `trace_data` | Distributed traces across services | Useful for latency analysis and root cause tracing |
| `log_data` | Raw service and pod logs | Useful for debugging, error signatures, and event context |
| `api_responses` | Recorded request/response outcomes | Useful for user-visible failures and endpoint behavior |
| `coverage_data` | Raw code coverage artifacts | Useful for linking faults to executed code paths |
| `coverage_report` | Human-readable coverage reports | Present in `TT_data`; useful for inspection and reporting |

## TT_data Inventory

The current baseline uses `TT_data`, so it is the most important part to understand first.

### TT_data size by modality

These are approximate sizes from the local cache inspection:

| Folder | Approx size |
| --- | --- |
| `TT_data/metric_data` | `1.2G` |
| `TT_data/api_responses` | `393M` |
| `TT_data/trace_data` | `299M` |
| `TT_data/coverage_report` | `195M` |
| `TT_data/log_data` | `106M` |
| `TT_data/coverage_data` | `4.1M` |
| `TT_data` total | `2.1G` |

### TT_data file counts

| Modality | Scenario folders | Total files |
| --- | ---: | ---: |
| `metric_data` | 13 | 13 |
| `trace_data` | 13 | 13 |
| `log_data` | 13 | 719 |
| `api_responses` | 13 | 13 |
| `coverage_data` | 13 | 533 |
| `coverage_report` | 13 | 28042 |

## TT_data Scenarios

Each scenario folder is one experiment run.

There is:

- 1 normal run
- 12 anomalous runs

### Current TT_data scenarios

| Scenario base name | Interpreted type |
| --- | --- |
| `Normal_case_em` | Normal baseline |
| `Lv_P_CPU_preserve` | Performance/resource fault |
| `Lv_P_DISKIO_preserve` | Performance/resource fault |
| `Lv_P_NETLOSS_preserve` | Performance/resource fault |
| `Lv_D_cachelimit` | Dependency/data-layer fault |
| `Lv_D_CONNECTION_POOL_exhaustion` | Dependency/data-layer fault |
| `Lv_D_TRANSACTION_timeout` | Dependency/data-layer fault |
| `Lv_S_DNSFAIL_preserve_no_order` | Service/platform fault |
| `Lv_S_HTTPABORT_preserve` | Service/platform fault |
| `Lv_S_KILLPOD_preserve` | Service/platform fault |
| `Lv_C_exception_injection` | Code/business-logic fault |
| `Lv_C_security_check` | Code/business-logic fault |
| `Lv_C_travel_detail_failure` | Code/business-logic fault |

### What the scenario prefixes likely mean

This is an interpretation from the folder names, but it matches the data well:

| Prefix | Likely meaning |
| --- | --- |
| `P` | Performance or resource faults |
| `D` | Dependency or data-layer faults |
| `S` | Service or platform faults |
| `C` | Code or business-logic faults |

## What Each TT_data Modality Looks Like

### 1. metric_data

In `TT_data`, each scenario has one large CSV file.

| Property | Description |
| --- | --- |
| Format | One CSV per scenario |
| Granularity | Many metric rows per timestamp |
| Key columns | `metric_name`, `timestamp`, `datetime`, `value`, plus many Prometheus/Kubernetes labels |
| Current baseline usage | Yes |

Example metric signals include:

- CPU usage
- memory usage
- network receive/transmit
- container-level metrics
- node-level metrics

### 2. trace_data

In `TT_data`, each scenario has one SkyWalking trace JSON file.

| Property | Description |
| --- | --- |
| Format | One JSON per scenario |
| Top-level keys | `metadata`, `traces` |
| Trace contents | summary, involved services, spans, timing, error flags |
| Current baseline usage | No |

This is useful later for:

- tracing which service path slowed down
- identifying cross-service propagation of faults
- building root-cause explanations

### 3. log_data

In `TT_data`, logs are stored per pod/service directory.

| Property | Description |
| --- | --- |
| Format | Many `.log` files per scenario |
| Supporting files | `kubernetes_events_*.json`, `log_collection_report_*.json` |
| Current baseline usage | No |

Important note:

- even the normal scenario can contain warnings or stack traces
- so "error-looking text in logs" does not automatically mean the scenario is anomalous

### 4. api_responses

In `TT_data`, each scenario has one `api_responses.jsonl` file.

| Property | Description |
| --- | --- |
| Format | JSON Lines |
| Per record | timestamp, method, URL, status code, request/response headers, request body, response body |
| Current baseline usage | No |

This is useful later for:

- endpoint-level failure analysis
- status code shifts
- user-visible behavior changes

### 5. coverage_data

| Property | Description |
| --- | --- |
| Format | Raw JaCoCo `.exec` files |
| Scope | Usually one per instrumented service |
| Current baseline usage | No |

### 6. coverage_report

| Property | Description |
| --- | --- |
| Format | `coverage-summary.txt`, `coverage.xml`, `merged.exec` |
| Scope | Per service |
| Current baseline usage | No |

This is mainly useful if you later want to connect anomalous behavior to what code actually executed.

## TT_data Scenario Density

The current baseline treats each unique metric timestamp as one observation window.

From the current local inspection:

| Scenario | Metric rows | Unique metric timestamps | Approx span (seconds) | API calls | Traces | Log files |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Normal_case_em_20251103T134716Z` | 217605 | 52 | 765 | 7310 | 4688 | 53 |
| `Lv_P_CPU_preserve_20251103T140939Z_em` | 395839 | 97 | 1440 | 7623 | 5000 | 53 |
| `Lv_P_DISKIO_preserve_20251103T144212Z_em` | 259241 | 63 | 930 | 7623 | 5000 | 53 |
| `Lv_P_NETLOSS_preserve_20251103T150613Z_em` | 267430 | 65 | 960 | 7518 | 4895 | 54 |
| `Lv_D_cachelimit_20251103T170657Z_em` | 307480 | 82 | 1215 | 7537 | 4914 | 53 |
| `Lv_D_CONNECTION_POOL_exhaustion_20251103T173702Z_em` | 295734 | 76 | 1125 | 7533 | 4910 | 53 |
| `Lv_D_TRANSACTION_timeout_20251103T180430Z_em` | 299460 | 75 | 1110 | 7519 | 4896 | 54 |
| `Lv_S_DNSFAIL_preserve_no_order_20251103T153116Z_em` | 262475 | 63 | 930 | 7545 | 4922 | 53 |
| `Lv_S_HTTPABORT_preserve_20251103T155524Z_em` | 533892 | 132 | 1965 | 7583 | 4960 | 53 |
| `Lv_S_KILLPOD_preserve_20251103T163624Z_em` | 260771 | 65 | 960 | 7623 | 5000 | 54 |
| `Lv_C_exception_injection_20251103T185917Z_em` | 329632 | 84 | 1245 | 7554 | 4931 | 54 |
| `Lv_C_security_check_20251103T183145Z_em` | 300295 | 75 | 1110 | 7520 | 4897 | 53 |
| `Lv_C_travel_detail_failure_20251103T192904Z_em` | 289686 | 73 | 1080 | 7585 | 4962 | 53 |

## SN_data At A Glance

`SN_data` is the second system in AnoMod.
It is present locally, but the current repo baseline does not use it yet.

### Key difference from TT_data

`SN_data` is organized differently:

| Aspect | `TT_data` | `SN_data` |
| --- | --- | --- |
| Metrics layout | One large CSV per scenario | Many smaller metric CSVs per scenario |
| Traces layout | One SkyWalking JSON per scenario | `all_traces.csv`, `all_traces.json`, `available_services.json` |
| Logs layout | Many pod directories | Service-level log files |
| API response files | One JSONL file per scenario | Multiple summary and response files |

### SN_data file counts

| Modality | Scenario folders | Total files |
| --- | ---: | ---: |
| `metric_data` | 13 | 208 |
| `trace_data` | 13 | 39 |
| `log_data` | 13 | 166 |
| `api_responses` | 13 | 53 |
| `coverage_data` | 13 | 8544 |

### Example SN_data metrics layout

Example files in one normal scenario:

- `system_cpu_usage.csv`
- `system_memory_usage_percent.csv`
- `socialnet_container_cpu.csv`
- `socialnet_container_memory.csv`
- `jaeger_spans_rate.csv`
- `metadata.txt`

So `SN_data` is not plug-compatible with the current `TT_data` baseline and would need its own ingestion path.

## What The Current Pipeline Uses

| Dataset section | Used right now? | Notes |
| --- | --- | --- |
| `TT_data/metric_data` | Yes | This is the current anomaly baseline input |
| `TT_data/trace_data` | No | Good candidate for root-cause stage |
| `TT_data/log_data` | No | Good candidate for failure signatures and explanations |
| `TT_data/api_responses` | No | Good candidate for endpoint-level degradation analysis |
| `TT_data/coverage_data` | No | Potential future code-path analysis |
| `TT_data/coverage_report` | No | Potential future interpretation/reporting |
| `SN_data/*` | No | Present, but not yet integrated |

## Current Pipeline Relationship To Data

In plain language, the current repo is using only the easiest structured part of AnoMod:

1. read `TT_data/metric_data`
2. group rows by scenario and timestamp
3. aggregate each metric into compact numerical features
4. train an anomaly detector on the normal run
5. score the anomalous runs against that normal profile

So the current baseline answers only this question:

> Can abnormal TrainTicket runs be detected from their metric patterns alone?

It does **not** yet answer:

- which service caused the issue
- what endpoint degraded
- what traces show the failure path
- what logs explain the anomaly
- how behavior compares between `TT_data` and `SN_data`

## Processed Outputs In This Repo

The baseline pipeline currently writes these outputs:

| File | Purpose |
| --- | --- |
| `data/processed/anomod_metric_manifest.csv` | Scenario inventory and source paths |
| `data/processed/anomod_metric_features.csv` | Timestamp-level feature table |
| `data/processed/anomod_isolation_forest.joblib` | Trained baseline model |
| `data/processed/anomod_train_scores.csv` | Scores on training windows |
| `data/processed/anomod_evaluation_scores.csv` | Scores on evaluation windows |
| `data/processed/anomod_scenario_summary.csv` | Scenario-level anomaly summary |
| `data/processed/anomod_evaluation_metrics.json` | Evaluation metrics |
| `data/processed/anomod_training_summary.json` | Training metadata summary |

## Important Notes

| Note | Meaning |
| --- | --- |
| `__MACOSX` folders | Archive noise from extraction; ignore them |
| `.DS_Store` files | Finder metadata; ignore them |
| Normal logs may still look noisy | Warnings or stack traces can appear even in normal runs |
| `SN_data` and `TT_data` are not shaped the same | They need different ingestion logic |

## Recommended Mental Model

Think of AnoMod as one fault-injection experiment dataset where each scenario gives you several synchronized views of the same run:

| View | What it tells you |
| --- | --- |
| Metrics | How the system behaved numerically |
| Traces | How requests moved through services |
| Logs | What the services reported internally |
| API responses | What clients observed |
| Coverage | What code paths were executed |

That combination is what makes AnoMod useful for both:

- anomaly detection
- root-cause analysis
