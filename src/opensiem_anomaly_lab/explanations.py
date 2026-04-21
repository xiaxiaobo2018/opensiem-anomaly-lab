from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from opensiem_anomaly_lab.ingestion import PROCESSED_DIR
from opensiem_anomaly_lab.retrieval import load_log_search_index, search_log_index


EXPLANATIONS_JSON_PATH = PROCESSED_DIR / "anomod_scenario_explanations.json"
EXPLANATIONS_MARKDOWN_PATH = PROCESSED_DIR / "anomod_scenario_explanations.md"
NODE_EXPLAINER_SCRIPT = Path("scripts/generate_vertex_completion.mjs")

DEFAULT_LLM_MODEL = "gemini-2.5-flash"
DEFAULT_LLM_LOCATION = "global"

DEFAULT_RETRIEVAL_QUERIES = [
    {
        "query": "exception error failed failure stack trace timeout refused unavailable",
        "source_type": "service_log",
        "top_k": 3,
    },
    {
        "query": "TokenException token expired unauthorized authentication security",
        "source_type": "service_log",
        "top_k": 2,
    },
    {
        "query": "database connection pool transaction timeout mysql jdbc refused",
        "source_type": "service_log",
        "top_k": 2,
    },
    {
        "query": "readiness probe failed i/o timeout connect refused unhealthy pod restart",
        "source_type": "kubernetes_event",
        "top_k": 2,
    },
]


def select_explanation_candidates(
    scenario_summary_df: pd.DataFrame,
    top_k_scenarios: int = 3,
    min_predicted_anomaly_rate: float = 0.5,
) -> pd.DataFrame:
    candidate_df = scenario_summary_df.copy()
    candidate_df = candidate_df[candidate_df["predicted_anomaly_rate"] >= min_predicted_anomaly_rate].copy()
    candidate_df = candidate_df.sort_values(
        ["mean_anomaly_score", "predicted_anomaly_rate"],
        ascending=[False, False],
    ).reset_index(drop=True)
    return candidate_df.head(top_k_scenarios).copy()


def retrieve_scenario_evidence(
    index_bundle: dict[str, Any],
    scenario_name: str,
    retrieval_top_k: int = 6,
) -> list[dict[str, Any]]:
    evidence_rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int]] = set()

    for query_spec in DEFAULT_RETRIEVAL_QUERIES:
        results_df = search_log_index(
            index_bundle=index_bundle,
            query=query_spec["query"],
            top_k=query_spec["top_k"],
            scenario_name=scenario_name,
            source_type=query_spec["source_type"],
        )

        for row in results_df.itertuples(index=False):
            evidence_key = (str(row.relative_path), int(row.chunk_index))
            if evidence_key in seen_keys:
                continue
            seen_keys.add(evidence_key)
            evidence_rows.append(
                {
                    "similarity": float(row.similarity),
                    "query": query_spec["query"],
                    "source_type": row.source_type,
                    "service_name": row.service_name,
                    "relative_path": row.relative_path,
                    "chunk_index": int(row.chunk_index),
                    "preview_text": row.preview_text,
                }
            )

    evidence_rows.sort(key=lambda item: item["similarity"], reverse=True)
    return evidence_rows[:retrieval_top_k]


def build_explanation_prompt(
    scenario_row: pd.Series,
    evidence_rows: list[dict[str, Any]],
) -> str:
    evidence_blocks: list[str] = []
    for index, evidence in enumerate(evidence_rows, start=1):
        evidence_blocks.append(
            "\n".join(
                [
                    f"Evidence {index}",
                    f"- source_type: {evidence['source_type']}",
                    f"- service_name: {evidence['service_name']}",
                    f"- path: {evidence['relative_path']}",
                    f"- retrieval_query: {evidence['query']}",
                    f"- similarity: {evidence['similarity']:.4f}",
                    evidence["preview_text"],
                ]
            )
        )

    evidence_text = "\n\n".join(evidence_blocks) if evidence_blocks else "No supporting evidence was retrieved."

    return f"""You are a security and reliability analyst helping explain an anomalous microservice run.

You must stay grounded in the supplied evidence.
Do not guess hidden causes that are not supported by the retrieved context.
If the evidence is weak or mixed, say so plainly.

Anomaly summary:
- total windows: {int(scenario_row['windows'])}
- mean anomaly score: {float(scenario_row['mean_anomaly_score']):.4f}
- max anomaly score: {float(scenario_row['max_anomaly_score']):.4f}
- predicted anomaly rate: {float(scenario_row['predicted_anomaly_rate']):.2%}

Retrieved evidence:
{evidence_text}

Write a concise plain-English explanation with exactly these section headers:
Summary:
Evidence:
Caveats:
"""


def call_vertex_completion(
    prompt: str,
    model: str = DEFAULT_LLM_MODEL,
    location: str = DEFAULT_LLM_LOCATION,
    project: str | None = None,
    script_path: Path = NODE_EXPLAINER_SCRIPT,
) -> str:
    payload = {
        "prompt": prompt,
        "model": model,
        "location": location,
    }
    if project:
        payload["project"] = project

    completed = subprocess.run(
        ["node", str(script_path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    response_payload = json.loads(completed.stdout)
    return str(response_payload["text"]).strip()


def build_explanation_records(
    scenario_summary_df: pd.DataFrame,
    top_k_scenarios: int = 3,
    retrieval_top_k: int = 6,
    model: str = DEFAULT_LLM_MODEL,
    location: str = DEFAULT_LLM_LOCATION,
    project: str | None = None,
) -> list[dict[str, Any]]:
    candidate_df = select_explanation_candidates(
        scenario_summary_df=scenario_summary_df,
        top_k_scenarios=top_k_scenarios,
    )
    index_bundle = load_log_search_index()
    records: list[dict[str, Any]] = []

    for rank, scenario_row in enumerate(candidate_df.to_dict(orient="records"), start=1):
        scenario_series = pd.Series(scenario_row)
        evidence_rows = retrieve_scenario_evidence(
            index_bundle=index_bundle,
            scenario_name=str(scenario_row["scenario_name"]),
            retrieval_top_k=retrieval_top_k,
        )
        prompt = build_explanation_prompt(
            scenario_row=scenario_series,
            evidence_rows=evidence_rows,
        )
        explanation_text = call_vertex_completion(
            prompt=prompt,
            model=model,
            location=location,
            project=project,
        )
        records.append(
            {
                "rank": rank,
                "scenario_name": scenario_row["scenario_name"],
                "fault_label": scenario_row["fault_label"],
                "fault_family": scenario_row["fault_family"],
                "fault_type": scenario_row["fault_type"],
                "windows": int(scenario_row["windows"]),
                "mean_anomaly_score": float(scenario_row["mean_anomaly_score"]),
                "max_anomaly_score": float(scenario_row["max_anomaly_score"]),
                "predicted_anomaly_rate": float(scenario_row["predicted_anomaly_rate"]),
                "retrieved_evidence": evidence_rows,
                "explanation": explanation_text,
            }
        )

    return records


def render_explanations_markdown(records: list[dict[str, Any]]) -> str:
    sections = ["# AnoMod Scenario Explanations", ""]

    for record in records:
        sections.append(f"## {record['rank']}. {record['scenario_name']}")
        sections.append("")
        sections.append(
            f"- fault family: `{record['fault_family']}` | fault type: `{record['fault_type']}` | "
            f"predicted anomaly rate: `{record['predicted_anomaly_rate']:.2%}`"
        )
        sections.append(
            f"- mean anomaly score: `{record['mean_anomaly_score']:.4f}` | "
            f"max anomaly score: `{record['max_anomaly_score']:.4f}`"
        )
        sections.append("")
        sections.append(record["explanation"])
        sections.append("")
        sections.append("Top Retrieved Evidence:")
        for evidence in record["retrieved_evidence"]:
            sections.append(
                f"- `{evidence['source_type']}` `{evidence['service_name']}` "
                f"`{evidence['relative_path']}` similarity `{evidence['similarity']:.4f}`"
            )
        sections.append("")

    return "\n".join(sections).strip() + "\n"


def save_explanation_artifacts(
    records: list[dict[str, Any]],
    json_path: Path = EXPLANATIONS_JSON_PATH,
    markdown_path: Path = EXPLANATIONS_MARKDOWN_PATH,
) -> tuple[Path, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    markdown_path.write_text(render_explanations_markdown(records), encoding="utf-8")
    return json_path, markdown_path
