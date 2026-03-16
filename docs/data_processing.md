# Data Processing

## Purpose

This document explains the **data transformation decisions** used in OpenSIEM Anomaly Lab.

It focuses on:

- how the raw dataset is ingested into the project workflow
- how the data is cleaned and normalized
- how the first model-ready feature set is created
- why specific columns are dropped or retained

---

## Current Workflow Overview

The current data workflow has two main stages:

1. **Ingestion**

   - load CICIDS-2017 from Hugging Face
   - convert to pandas
   - normalize column names
   - replace infinite values with missing values
   - save cleaned outputs
2. **Feature preparation**

   - remove label and identifier/context columns
   - keep numeric features only
   - fill missing values
   - save a model-ready feature table

---

## Dataset Snapshot

The current ingestion pipeline loads the public `bvk/CICIDS-2017` dataset.

Observed full dataset shape at ingestion time:

- **Rows:** 2,099,971
- **Columns:** 89

The dataset contains:

- routing/context fields such as source/destination IPs and ports
- flow-level statistical features
- protocol/flag features
- a `label` column for known traffic class
- an `attempted_category` field

---

## Ingestion Decisions

### 1. Programmatic loading

The dataset is loaded programmatically instead of being manually stored inside the repository.

### Why

- keeps the repo lightweight
- avoids committing large raw data files
- makes the pipeline reproducible from code

---

### 2. Column-name normalization

Original dataset column names contain spaces, mixed case, and symbols such as `/`.

During ingestion, column names are normalized into lowercase snake_case.

### Rules used

- trim whitespace
- convert to lowercase
- replace `/` with `_per_`
- replace `-` with `_`
- replace non-word characters with `_`
- collapse repeated underscores

### Examples

| Original               | Normalized             |
| ---------------------- | ---------------------- |
| `Src IP dec`         | `src_ip_dec`         |
| `Flow Bytes/s`       | `flow_bytes_per_s`   |
| `Attempted Category` | `attempted_category` |

---

### 3. Infinite-value handling

Some numerical flow features can contain positive or negative infinity.

Current rule:

- replace `np.inf` and `-np.inf` with `NaN`

### Why

Most downstream ML workflows cannot reliably use infinite values directly.
Replacing infinities early makes later preprocessing more predictable.

---

### 4. Output strategy

The ingestion stage currently writes two outputs:

- `data/processed/cicids_sample_clean.csv`
- `data/processed/cicids_full_clean.parquet`

### Why keep both

#### Sample CSV

Used for:

- fast inspection
- quick testing
- lightweight EDA
- easy repo-visible example data

#### Full Parquet

Used for:

- larger-scale model development
- more efficient storage and reading than CSV
- full dataset experimentation

---

## Sampling Decision

A 5,000-row random sample is generated from the cleaned full dataset.

### Current sampling policy

- sample size: **5000**
- random seed: **42**

### Why

A smaller sample helps with:

- quicker iteration
- easier debugging
- faster notebook work
- lower friction during early feature and model prototyping

The sample is not intended to replace the full dataset, only to speed up early development.

---

## Feature Preparation Decisions

The first feature-preparation stage is intentionally conservative.

The goal is to create a clean baseline feature table for unsupervised anomaly detection.

### Current principle

Focus on **behavioral numeric flow features**, not direct identifiers.

---

## Columns excluded from the first baseline

### 1. Evaluation fields

The following columns are dropped before feature generation:

- `label`
- `attempted_category`

### Why

These fields describe known attack/traffic outcomes or metadata and are useful for **evaluation**, not for unsupervised feature input.

Including them would create leakage and undermine the anomaly-detection objective.

---

### 2. Identifier and context fields

The following columns are also dropped in the first feature baseline:

- `src_ip_dec`
- `src_port`
- `dst_ip_dec`
- `dst_port`
- `timestamp`

### Why

These columns are excluded in the first version because they act more like:

- identifiers
- routing context
- environment-specific address information

Using them too early can lead the model to:

- memorize endpoints
- overfit to specific IP/port patterns
- learn shortcuts instead of traffic behavior

This does not mean these columns are useless forever. They may be reintroduced later through engineered features or grouped behavioral summaries.

---

## Columns retained in the first baseline

After dropping known non-feature columns, the first baseline keeps **numeric columns only**.

These include categories such as:

- flow duration
- packet counts
- byte counts
- packet-length statistics
- packets-per-second and bytes-per-second
- inter-arrival time statistics
- TCP/flag counters
- active/idle timing features
- packet/segment size summaries
- ratio-style numeric fields

### Why

These features better represent traffic behavior and are more appropriate for a first anomaly-detection baseline.

---

## Missing-value policy

Current baseline rule:

- fill missing values with `0`

### Why this was chosen

This is a simple and reproducible starting point for the first model iteration.

It allows:

- the feature matrix to be used directly by baseline ML models
- easy script-based preprocessing
- minimal early complexity

### Caveat

This is a baseline rule, not necessarily the final best practice.
Later versions may use:

- median imputation
- feature-specific imputation
- missingness indicators

---

## Current Feature Philosophy

The first anomaly-detection baseline is designed to answer:

> Can behavioral flow statistics alone separate suspicious traffic from normal traffic reasonably well?

That is why the initial feature policy is intentionally simple:

- remove labels
- remove direct identifiers
- keep numeric flow behavior
- fill missing values
- generate a clean feature table

This gives the project a clearer baseline before introducing more complex feature engineering.

---

## Files produced by the current processing pipeline

### Ingestion stage

- `data/processed/cicids_sample_clean.csv`
- `data/processed/cicids_full_clean.parquet`

### Feature-preparation stage

- `data/processed/cicids_sample_features.csv`

Potential future output:

- `data/processed/cicids_full_features.parquet`

---

## Current limitations

The current data-processing pipeline is intentionally minimal.

Not yet implemented:

- timestamp parsing into engineered time features
- feature scaling/normalization
- constant-column filtering
- sparse-column filtering
- train/test split policy
- endpoint aggregation features
- session/user/entity baselines
- dimensionality reduction
- advanced imputation strategy

These are expected to be added incrementally after the first anomaly baseline is working.

---

## Rationale Summary

The current data-processing design tries to balance:

- simplicity
- reproducibility
- interpretability
- reasonable anti-leakage discipline

The project does **not** attempt to build the most complex preprocessing pipeline first.
Instead, it starts with a clean and explainable baseline that can be improved step by step.

---
