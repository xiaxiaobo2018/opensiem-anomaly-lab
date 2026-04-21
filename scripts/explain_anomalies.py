from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from opensiem_anomaly_lab.explanations import (
    DEFAULT_LLM_LOCATION,
    DEFAULT_LLM_MODEL,
    EXPLANATIONS_JSON_PATH,
    EXPLANATIONS_MARKDOWN_PATH,
    build_explanation_records,
    save_explanation_artifacts,
)
from opensiem_anomaly_lab.ingestion import PROCESSED_DIR


SCENARIO_SUMMARY_PATH = PROCESSED_DIR / "anomod_scenario_summary.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate LLM explanations for anomalous AnoMod scenarios.")
    parser.add_argument(
        "--scenario-summary-path",
        type=Path,
        default=SCENARIO_SUMMARY_PATH,
        help=f"Scenario summary CSV path. Default: {SCENARIO_SUMMARY_PATH}",
    )
    parser.add_argument("--top-k-scenarios", type=int, default=3, help="How many anomalous scenarios to explain")
    parser.add_argument("--retrieval-top-k", type=int, default=6, help="How many retrieved chunks to pass to the LLM")
    parser.add_argument("--llm-model", default=DEFAULT_LLM_MODEL, help=f"LLM model. Default: {DEFAULT_LLM_MODEL}")
    parser.add_argument(
        "--llm-location",
        default=DEFAULT_LLM_LOCATION,
        help=f"Vertex location. Default: {DEFAULT_LLM_LOCATION}",
    )
    parser.add_argument("--llm-project", help="Optional explicit Google Cloud project override")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=EXPLANATIONS_JSON_PATH,
        help=f"JSON output path. Default: {EXPLANATIONS_JSON_PATH}",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=EXPLANATIONS_MARKDOWN_PATH,
        help=f"Markdown output path. Default: {EXPLANATIONS_MARKDOWN_PATH}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.scenario_summary_path.exists():
        raise FileNotFoundError(
            f"Could not find scenario summary at {args.scenario_summary_path}. Run scripts/evaluate.py first."
        )

    scenario_summary_df = pd.read_csv(args.scenario_summary_path)
    records = build_explanation_records(
        scenario_summary_df=scenario_summary_df,
        top_k_scenarios=args.top_k_scenarios,
        retrieval_top_k=args.retrieval_top_k,
        model=args.llm_model,
        location=args.llm_location,
        project=args.llm_project,
    )
    json_path, markdown_path = save_explanation_artifacts(
        records=records,
        json_path=args.json_output,
        markdown_path=args.markdown_output,
    )

    print(f"Saved explanation JSON to: {json_path}")
    print(f"Saved explanation Markdown to: {markdown_path}")
    print(f"Explained scenarios: {len(records)}")


if __name__ == "__main__":
    main()
