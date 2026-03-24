from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

from src.application.container import get_retrieve_context_use_case


def reciprocal_rank(result_ids: List[str], expected_ids: List[str]) -> float:
    expected = set(expected_ids)
    for i, rid in enumerate(result_ids, start=1):
        if rid in expected:
            return 1.0 / i
    return 0.0


def recall_at_k(result_ids: List[str], expected_ids: List[str], k: int) -> float:
    expected = set(expected_ids)
    if not expected:
        return 0.0
    hits = len(set(result_ids[:k]).intersection(expected))
    return hits / len(expected)


def evaluate(dataset_path: Path, k: int) -> Dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    retrieve = get_retrieve_context_use_case()

    mrr_vals: List[float] = []
    recall_vals: List[float] = []
    latencies_ms: List[float] = []
    details: List[Dict[str, Any]] = []

    for row in dataset:
        query = row["query"]
        expected_ids = row.get("expected_ids", [])
        t0 = time.perf_counter()
        chunks = retrieve.execute(query, top_k=k)
        latency = (time.perf_counter() - t0) * 1000
        ids = [c.id for c in chunks]

        rr = reciprocal_rank(ids, expected_ids)
        rec = recall_at_k(ids, expected_ids, k=k)
        mrr_vals.append(rr)
        recall_vals.append(rec)
        latencies_ms.append(latency)
        details.append(
            {
                "query": query,
                "expected_ids": expected_ids,
                "result_ids": ids,
                "rr": rr,
                "recall": rec,
                "latency_ms": round(latency, 2),
            }
        )

    out = {
        "num_queries": len(dataset),
        f"mrr@{k}": round(sum(mrr_vals) / max(1, len(mrr_vals)), 4),
        f"recall@{k}": round(sum(recall_vals) / max(1, len(recall_vals)), 4),
        "latency_p50_ms": round(statistics.median(latencies_ms), 2) if latencies_ms else 0.0,
        "latency_p95_ms": round(_percentile(latencies_ms, 95), 2) if latencies_ms else 0.0,
        "details": details,
    }
    return out


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    idx = int(round((p / 100.0) * (len(vals) - 1)))
    return vals[max(0, min(idx, len(vals) - 1))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality metrics.")
    parser.add_argument("--dataset", type=Path, default=Path("data/eval/queries.json"))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("data/eval/latest_metrics.json"))
    args = parser.parse_args()

    result = evaluate(args.dataset, k=args.k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "details"}, indent=2, ensure_ascii=False))
    print(f"Saved detailed report -> {args.output}")


if __name__ == "__main__":
    main()
