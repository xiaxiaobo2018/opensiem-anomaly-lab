from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from opensiem_anomaly_lab.retrieval import LOG_INDEX_PATH, load_log_search_index, search_log_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the AnoMod log semantic index.")
    parser.add_argument("query", help="Natural-language or keyword query to search for")
    parser.add_argument("--top-k", type=int, default=5, help="How many results to return")
    parser.add_argument("--scenario-name", help="Optional exact scenario filter")
    parser.add_argument("--fault-family", help="Optional fault-family filter, e.g. p, d, s, c")
    parser.add_argument("--source-type", help="Optional source-type filter, e.g. service_log or kubernetes_event")
    parser.add_argument(
        "--index-path",
        type=Path,
        default=LOG_INDEX_PATH,
        help=f"Path to the built joblib index. Default: {LOG_INDEX_PATH}",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=500,
        help="Maximum characters to print for each result preview",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    index_bundle = load_log_search_index(index_path=args.index_path)
    results_df = search_log_index(
        index_bundle=index_bundle,
        query=args.query,
        top_k=args.top_k,
        scenario_name=args.scenario_name,
        fault_family=args.fault_family,
        source_type=args.source_type,
    )

    if results_df.empty:
        print("No matching log chunks found for the requested filters.")
        return

    for rank, row in enumerate(results_df.itertuples(index=False), start=1):
        preview = row.preview_text[: args.preview_chars].strip()
        print(f"[{rank}] similarity={row.similarity:.4f}")
        print(
            "    "
            f"scenario={row.scenario_name} | fault={row.fault_family}/{row.fault_type} | "
            f"service={row.service_name} | source={row.source_type}"
        )
        print(f"    path={row.relative_path}")
        print(f"    {preview}")
        print()


if __name__ == "__main__":
    main()
