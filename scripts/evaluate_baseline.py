from typing import List

from src.evaluation.metrics import mean_reciprocal_rank


def main() -> None:
    # Placeholder: fake ranks list
    ranks: List[int] = [1, 2, 0]
    mrr = mean_reciprocal_rank(ranks)
    print(f"Baseline MRR: {mrr:.4f}")


if __name__ == "__main__":
    main()