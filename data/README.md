# Data Setup

This project uses public cybersecurity datasets only.

## Dataset
CICIDS-2017

## Raw data source
The dataset is loaded programmatically via Hugging Face Datasets.

Example:
```python
from datasets import load_dataset

ds = load_dataset("bvk/CICIDS-2017")
```

## Raw data
Raw source files are not stored in this repository.
The dataset is downloaded and cached locally by the `datasets` library.

`data/raw/` is reserved for optional local raw files or small test inputs.

## Processed data
Generated outputs are written to `data/processed/`, including:
- `cicids_sample_clean.csv`
- `cicids_full_clean.parquet`
- `cicids_sample_features.csv`
