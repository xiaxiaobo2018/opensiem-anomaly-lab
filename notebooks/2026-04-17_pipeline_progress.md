# OpenSIEM Pipeline Progress

Timestamp: `2026-04-17 15:54:50 +08`
Stage: `Baseline pipeline wired end-to-end`

## Simple Block Diagram

```text
AnoMod Metric Data
local cache: data/raw/anomod/TT_data/metric_data/
or fallback: gs://opensiem-data-xia0b0/raw/anomod
            |
            v
scripts/ingest_anomod.py
- discover scenario metric CSVs
- infer labels from folder names
- write manifest
            |
            v
scripts/prepare_features.py
- read metric_name / timestamp / value
- aggregate by scenario + timestamp + metric_name
- compute mean / std / min / max
- pivot to feature table
            |
            v
data/processed/anomod_metric_features.csv
1002 rows x 138 columns
            |
            v
scripts/train.py
- train IsolationForest
- use only normal windows for training
            |
            v
data/processed/anomod_isolation_forest.joblib
            |
            v
scripts/evaluate.py
- score held-out normal + anomalous windows
- write metrics and scenario summary
            |
            v
Outputs
- anomod_evaluation_metrics.json
- anomod_scenario_summary.csv
- anomod_evaluation_scores.csv
```

## Current Dataset Shape

- Scenarios: `13`
- Normal scenarios: `1`
- Anomalous scenarios: `12`
- Feature table: `1002 rows x 138 columns`
- Metadata columns: `6`
- Feature columns: `132`
- Training rows: `36`
- Evaluation rows: `966`

## Current Model Shape

- Model: `IsolationForest`
- Training split: first `70%` of normal windows
- Evaluation split: remaining normal windows + all anomaly windows

## Latest Baseline Metrics

- Accuracy: `0.8002`
- Precision: `0.9797`
- Recall: `0.8137`
- F1: `0.8890`
- ROC AUC: `0.4459`
- Average Precision: `0.9861`

## Progress Note

The pipeline is now reproducible end to end on AnoMod metric data.
It is a useful baseline, but it is not yet well calibrated on held-out normal windows.
The next likely upgrade is better thresholding/calibration and richer features from traces/logs.

## Layman Explanation

In simple terms, the current pipeline tries to learn what "normal system behavior" looks like from the healthy AnoMod run, using only infrastructure and service metrics such as CPU, memory, and network activity.

It works like this:

1. The pipeline reads the raw metric files for each test scenario.
2. It groups the metric readings by time window so each moment becomes one compact snapshot of system behavior.
3. It turns those snapshots into a table of numbers the model can learn from.
4. It trains an anomaly detector on normal snapshots only, so the model builds a picture of what healthy behavior looks like.
5. It then checks the abnormal scenarios and asks: "How far does this look from normal?"
6. Finally, it writes out scores and summaries showing which scenarios looked most unusual.

So the current version is not yet explaining root cause or reading logs/traces.
It is mainly answering this first question:

"Can we detect that a system run looks abnormal just from its metric patterns?"
