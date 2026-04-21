from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from opensiem_anomaly_lab.retrieval import (
    LOG_CHUNKS_PATH,
    LOG_INDEX_PATH,
    build_log_corpus,
    fit_log_search_index,
    save_log_search_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a semantic-search index over AnoMod log data.")
    parser.add_argument("--system-name", default="TT_data", help="AnoMod system to index. Default: TT_data")
    parser.add_argument(
        "--corpus-output",
        type=Path,
        default=LOG_CHUNKS_PATH,
        help=f"CSV path for saved log chunks. Default: {LOG_CHUNKS_PATH}",
    )
    parser.add_argument(
        "--index-output",
        type=Path,
        default=LOG_INDEX_PATH,
        help=f"Joblib path for saved vector index. Default: {LOG_INDEX_PATH}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    corpus_df = build_log_corpus(system_name=args.system_name)
    index_bundle = fit_log_search_index(corpus_df)
    corpus_path, index_path = save_log_search_artifacts(
        corpus_df=corpus_df,
        index_bundle=index_bundle,
        corpus_path=args.corpus_output,
        index_path=args.index_output,
    )

    print(f"Saved log chunk corpus to: {corpus_path}")
    print(f"Saved log search index to: {index_path}")
    print(f"Indexed chunks: {len(corpus_df):,}")
    print(f"Scenarios: {corpus_df['scenario_name'].nunique()}")
    print(f"Services: {corpus_df['service_name'].nunique()}")
    print(f"Source types: {', '.join(sorted(corpus_df['source_type'].unique()))}")
    print("\nChunks by source type:")
    print(corpus_df["source_type"].value_counts().to_string())
    print("\nChunks by anomaly label:")
    print(corpus_df["is_anomaly"].value_counts().rename(index={0: "normal", 1: "anomaly"}).to_string())


if __name__ == "__main__":
    main()
