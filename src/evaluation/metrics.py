from typing import List


def mean_reciprocal_rank(ranks: List[int]) -> float:
    if not ranks:
        return 0.0
    return sum(1.0 / r for r in ranks if r > 0) / len(ranks)


def dummy_latency_ms() -> float:
    """
    Placeholder latency metric.
    """
    return 0.0