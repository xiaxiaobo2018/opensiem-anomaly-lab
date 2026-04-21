from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from opensiem_anomaly_lab.ingestion import RAW_ANOMOD_DIR, parse_scenario_metadata


LOG_DATA_ROOT = Path("TT_data/log_data")
LOG_CHUNKS_PATH = Path("data/processed/anomod_log_chunks.csv")
LOG_INDEX_PATH = Path("data/processed/anomod_log_search_index.joblib")

LOG_ENTRY_START_RE = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2}[ T]|[A-Z]+\s+\d{4}-\d{2}-\d{2}|Picked up JAVA_TOOL_OPTIONS|Traceback|Exception in thread)"
)

DEFAULT_MAX_CHARS_PER_CHUNK = 2800
DEFAULT_MAX_ENTRIES_PER_CHUNK = 12
DEFAULT_OVERLAP_ENTRIES = 2
DEFAULT_MAX_FEATURES = 50_000
DEFAULT_MAX_COMPONENTS = 256


def get_log_data_root(
    extracted_dir: Path = RAW_ANOMOD_DIR,
    system_name: str = "TT_data",
) -> Path:
    log_root = extracted_dir / system_name / "log_data"
    if not log_root.exists():
        raise FileNotFoundError(
            f"Could not find AnoMod log data at {log_root}. "
            "Week 2 semantic search currently expects the local raw cache."
        )
    return log_root


def infer_service_name(pod_name: str) -> str:
    if pod_name.startswith("ts-"):
        match = re.match(r"^(?P<service>.+)-[a-z0-9]{8,10}-[a-z0-9]{5}$", pod_name)
        if match:
            return match.group("service")
    return pod_name


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def humanize_identifier(value: str) -> str:
    return re.sub(r"[_\-]+", " ", value).strip()


def split_log_into_entries(text: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line and not current:
            continue

        if current and LOG_ENTRY_START_RE.match(line):
            entry = clean_text("\n".join(current))
            if entry:
                entries.append(entry)
            current = [line]
            continue

        current.append(line)

    if current:
        entry = clean_text("\n".join(current))
        if entry:
            entries.append(entry)

    if entries:
        return entries

    fallback = clean_text(text)
    return [fallback] if fallback else []


def chunk_entries(
    entries: list[str],
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
    max_entries_per_chunk: int = DEFAULT_MAX_ENTRIES_PER_CHUNK,
    overlap_entries: int = DEFAULT_OVERLAP_ENTRIES,
) -> list[str]:
    if not entries:
        return []

    chunks: list[str] = []
    buffer: list[str] = []

    for entry in entries:
        candidate = buffer + [entry]
        candidate_text = "\n\n".join(candidate)
        should_flush = (
            bool(buffer)
            and (
                len(candidate) > max_entries_per_chunk
                or len(candidate_text) > max_chars_per_chunk
            )
        )

        if should_flush:
            chunks.append(clean_text("\n\n".join(buffer)))
            overlap = buffer[-overlap_entries:] if overlap_entries > 0 else []
            buffer = overlap + [entry]
        else:
            buffer = candidate

    if buffer:
        chunks.append(clean_text("\n\n".join(buffer)))

    return [chunk for chunk in chunks if chunk]


def build_service_log_chunks(
    scenario_dir: Path,
    relative_path: Path,
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
    max_entries_per_chunk: int = DEFAULT_MAX_ENTRIES_PER_CHUNK,
    overlap_entries: int = DEFAULT_OVERLAP_ENTRIES,
) -> list[dict[str, Any]]:
    pod_name = relative_path.parent.name
    service_name = infer_service_name(pod_name)
    source_path = scenario_dir / relative_path
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    entries = split_log_into_entries(text)
    chunks = chunk_entries(
        entries,
        max_chars_per_chunk=max_chars_per_chunk,
        max_entries_per_chunk=max_entries_per_chunk,
        overlap_entries=overlap_entries,
    )

    rows: list[dict[str, Any]] = []
    for chunk_index, chunk_text in enumerate(chunks):
        rows.append(
            {
                "source_type": "service_log",
                "pod_name": pod_name,
                "service_name": service_name,
                "source_path": str(source_path),
                "relative_path": str(relative_path),
                "chunk_index": chunk_index,
                "preview_text": chunk_text,
            }
        )
    return rows


def summarize_kubernetes_event(item: dict[str, Any]) -> str:
    involved_object = item.get("involvedObject", {}) or {}
    message = clean_text(str(item.get("message", "")))
    parts = [
        f"type={item.get('type', 'unknown')}",
        f"reason={item.get('reason', 'unknown')}",
        f"kind={involved_object.get('kind', 'unknown')}",
        f"name={involved_object.get('name', 'unknown')}",
        f"first_timestamp={item.get('firstTimestamp', 'unknown')}",
        f"last_timestamp={item.get('lastTimestamp', 'unknown')}",
        f"message={message}",
    ]
    return "\n".join(parts)


def build_kubernetes_event_chunks(scenario_dir: Path, relative_path: Path) -> list[dict[str, Any]]:
    source_path = scenario_dir / relative_path
    payload = json.loads(source_path.read_text(encoding="utf-8", errors="ignore"))
    rows: list[dict[str, Any]] = []

    for chunk_index, item in enumerate(payload.get("items", [])):
        event_text = summarize_kubernetes_event(item)
        if not event_text:
            continue

        rows.append(
            {
                "source_type": "kubernetes_event",
                "pod_name": "kubernetes",
                "service_name": "kubernetes",
                "source_path": str(source_path),
                "relative_path": str(relative_path),
                "chunk_index": chunk_index,
                "preview_text": event_text,
            }
        )

    return rows


def build_log_corpus(
    extracted_dir: Path = RAW_ANOMOD_DIR,
    system_name: str = "TT_data",
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
    max_entries_per_chunk: int = DEFAULT_MAX_ENTRIES_PER_CHUNK,
    overlap_entries: int = DEFAULT_OVERLAP_ENTRIES,
) -> pd.DataFrame:
    log_root = get_log_data_root(extracted_dir=extracted_dir, system_name=system_name)
    rows: list[dict[str, Any]] = []
    chunk_id = 0

    for scenario_dir in sorted(path for path in log_root.iterdir() if path.is_dir()):
        metadata = parse_scenario_metadata(scenario_dir.name)

        for source_path in sorted(scenario_dir.rglob("*")):
            if not source_path.is_file():
                continue

            relative_path = source_path.relative_to(scenario_dir)
            row_batch: list[dict[str, Any]] = []

            if source_path.suffix == ".log":
                row_batch = build_service_log_chunks(
                    scenario_dir=scenario_dir,
                    relative_path=relative_path,
                    max_chars_per_chunk=max_chars_per_chunk,
                    max_entries_per_chunk=max_entries_per_chunk,
                    overlap_entries=overlap_entries,
                )
            elif source_path.suffix == ".json" and source_path.name.startswith("kubernetes_events_"):
                row_batch = build_kubernetes_event_chunks(
                    scenario_dir=scenario_dir,
                    relative_path=relative_path,
                )

            for row in row_batch:
                search_text = clean_text(
                    "\n".join(
                        [
                            f"scenario_name={metadata['scenario_name']}",
                            f"scenario_text={humanize_identifier(str(metadata['scenario_name']))}",
                            f"fault_family={metadata['fault_family']}",
                            f"fault_family_text={humanize_identifier(str(metadata['fault_family']))}",
                            f"fault_type={metadata['fault_type']}",
                            f"fault_type_text={humanize_identifier(str(metadata['fault_type']))}",
                            f"source_type={row['source_type']}",
                            f"service_name={row['service_name']}",
                            f"service_name_text={humanize_identifier(str(row['service_name']))}",
                            "",
                            row["preview_text"],
                        ]
                    )
                )
                rows.append(
                    {
                        "chunk_id": chunk_id,
                        **metadata,
                        **row,
                        "search_text": search_text,
                    }
                )
                chunk_id += 1

    corpus_df = pd.DataFrame(rows)
    if corpus_df.empty:
        raise ValueError(f"No log chunks were discovered under {log_root}")

    return corpus_df.sort_values(["scenario_name", "source_type", "service_name", "chunk_index"]).reset_index(drop=True)


def fit_log_search_index(
    corpus_df: pd.DataFrame,
    max_features: int = DEFAULT_MAX_FEATURES,
    max_components: int = DEFAULT_MAX_COMPONENTS,
) -> dict[str, Any]:
    texts = corpus_df["search_text"].tolist()
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        max_features=max_features,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    feature_count = tfidf_matrix.shape[1]
    component_count = min(max_components, tfidf_matrix.shape[0] - 1, feature_count - 1)

    if component_count >= 2:
        svd = TruncatedSVD(n_components=component_count, random_state=42)
        embeddings = svd.fit_transform(tfidf_matrix)
    else:
        svd = None
        embeddings = tfidf_matrix.toarray()

    tfidf_matrix = normalize(tfidf_matrix, norm="l2")
    embeddings = normalize(embeddings.astype(np.float32), norm="l2")

    return {
        "vectorizer": vectorizer,
        "svd": svd,
        "tfidf_matrix": tfidf_matrix,
        "embeddings": embeddings,
        "corpus": corpus_df.reset_index(drop=True),
    }


def embed_query(index_bundle: dict[str, Any], query: str) -> tuple[Any, np.ndarray]:
    vectorizer: TfidfVectorizer = index_bundle["vectorizer"]
    svd: TruncatedSVD | None = index_bundle["svd"]

    query_matrix = vectorizer.transform([query])
    query_matrix = normalize(query_matrix, norm="l2")
    if svd is not None:
        query_embedding = svd.transform(query_matrix)
    else:
        query_embedding = query_matrix.toarray()

    return query_matrix, normalize(query_embedding.astype(np.float32), norm="l2")[0]


def search_log_index(
    index_bundle: dict[str, Any],
    query: str,
    top_k: int = 5,
    scenario_name: str | None = None,
    fault_family: str | None = None,
    source_type: str | None = None,
) -> pd.DataFrame:
    corpus_df: pd.DataFrame = index_bundle["corpus"]
    tfidf_matrix = index_bundle["tfidf_matrix"]
    embeddings: np.ndarray = index_bundle["embeddings"]

    query_sparse, query_embedding = embed_query(index_bundle, query)
    lexical_scores = (tfidf_matrix @ query_sparse.T).toarray().ravel()
    semantic_scores = embeddings @ query_embedding
    scores = (0.65 * lexical_scores) + (0.35 * semantic_scores)

    query_lower = query.lower()
    kubernetes_terms = {
        "kubernetes",
        "pod",
        "probe",
        "readiness",
        "liveness",
        "node",
        "container",
        "scheduler",
        "restart",
    }
    prefers_kubernetes = any(term in query_lower for term in kubernetes_terms)

    is_kubernetes_event = corpus_df["source_type"].eq("kubernetes_event").to_numpy()
    is_normal_kubernetes_event = is_kubernetes_event & corpus_df["preview_text"].str.startswith("type=Normal").to_numpy()

    scores[is_normal_kubernetes_event] *= 0.5
    if prefers_kubernetes:
        scores[is_kubernetes_event] *= 1.08
    else:
        scores[is_kubernetes_event] *= 0.5

    mask = np.ones(len(corpus_df), dtype=bool)
    if scenario_name:
        mask &= corpus_df["scenario_name"].eq(scenario_name).to_numpy()
    if fault_family:
        mask &= corpus_df["fault_family"].eq(fault_family).to_numpy()
    if source_type:
        mask &= corpus_df["source_type"].eq(source_type).to_numpy()

    filtered_positions = np.flatnonzero(mask)
    if len(filtered_positions) == 0:
        return corpus_df.iloc[0:0].copy()

    filtered_scores = scores[filtered_positions]
    top_k = max(1, min(top_k, len(filtered_positions)))
    ranked_local = np.argsort(-filtered_scores)[:top_k]
    ranked_positions = filtered_positions[ranked_local]

    results_df = corpus_df.iloc[ranked_positions].copy()
    results_df.insert(0, "similarity", scores[ranked_positions])
    return results_df.reset_index(drop=True)


def save_log_search_artifacts(
    corpus_df: pd.DataFrame,
    index_bundle: dict[str, Any],
    corpus_path: Path = LOG_CHUNKS_PATH,
    index_path: Path = LOG_INDEX_PATH,
) -> tuple[Path, Path]:
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_df.to_csv(corpus_path, index=False)
    joblib.dump(index_bundle, index_path, compress=3)
    return corpus_path, index_path


def load_log_search_index(index_path: Path = LOG_INDEX_PATH) -> dict[str, Any]:
    if not index_path.exists():
        raise FileNotFoundError(
            f"Could not find log search index at {index_path}. "
            "Run scripts/build_log_search_index.py first."
        )
    return joblib.load(index_path)
