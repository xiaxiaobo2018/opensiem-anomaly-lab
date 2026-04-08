# OpenSIEM Anomaly Lab

A public cybersecurity/ML portfolio project for anomaly detection on public SIEM-like datasets. (Inspired by my internship)

## Goals
- Build a reproducible anomaly detection pipeline
- Use public or synthetic security data only
- Demonstrate ingestion, feature engineering, modeling, and evaluation

## Data Source
Current local data source:
- `AnoMod.zip` (stored at `data/anomod/AnoMod.zip`)

Official dataset source:
- Zenodo DOI: https://doi.org/10.5281/zenodo.18342898
- Collection scripts: https://github.com/EvoTestOps/AnoMod

Citation:
- Ke Ping, Hamza Bin Mazhar, Yuqing Wang, Ying Song, and Mika V. Mantyla. 2026. *AnoMod: A Dataset for Anomaly Detection and Root Cause Analysis in Microservice Systems*. MSR '26. https://doi.org/10.1145/3793302.3793324

The archive is extracted into:
- `data/raw/anomod/`

Use:
```bash
uv run scripts/ingest_anomod.py
```

Large raw data files are intentionally excluded from git.

## Planned Stack
- Python
- uv
- pandas
- scikit-learn
- SHAP
- pytest

## Status
Project setup in progress.
