import os
import sys
import json
import asyncio
import time
import nest_asyncio
nest_asyncio.apply()
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from datasets import Dataset

from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from src.application.container import get_generate_answer_use_case
from src.infrastructure.config.settings import get_settings

def load_data(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def main():
    settings = get_settings()
    
    judge_llm = ChatGroq(
        api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        max_retries=5
    )
    
    print("Loading judge embedding model...")
    judge_embeddings = HuggingFaceEmbeddings(model_name=settings.embed_model_name)
    
    use_case = get_generate_answer_use_case()
    
    dataset_path = Path("data/eval/ragas_ground_truth.json")
    ground_truths = load_data(dataset_path)
    
    ragas_data = {
        "user_input": [],
        "response": [],
        "retrieved_contexts": [],
        "reference": [],
        "category": []
    }
    
    print("Generating responses for evaluation...")
    for gt in ground_truths:
        q = gt["user_input"]
        ref = gt["reference"]
        
        
        result = use_case.execute(query=q, top_k=3) 
        
        ragas_data["user_input"].append(q)
        ragas_data["response"].append(result["answer"])
        ragas_data["retrieved_contexts"].append([c["text"] for c in result["citations"]])
        ragas_data["reference"].append(ref)
        ragas_data["category"].append(gt.get("category", "unknown"))
        print(f"Processed query: {q}")
        
        time.sleep(2)

    dataset = Dataset.from_dict(ragas_data)
    
    from ragas.run_config import RunConfig

    run_config = RunConfig(timeout=120, max_retries=10, max_wait=60, max_workers=1)

    print("\nRunning Ragas evaluation with Llama 4 Scout 17B Judge...")
    score = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=judge_embeddings,
        run_config=run_config,
        raise_exceptions=False
    )
    
    out_path = Path("data/eval/ragas_benchmark_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    df = score.to_pandas()
    
    with open(out_path, "w") as f:
        json.dump(df.to_dict(orient="records"), f, indent=2)
        
    print("\n--- RAGAS BENCHMARK OVERALL RESULTS ---")
    print(score)
    
    if "category" in df.columns:
        print("\n--- METRICS BY CATEGORY ---")
        metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        grouped = df.groupby("category")[metrics].mean().round(4) * 100
        
        for metric in metrics:
            print(f"\n# {metric.replace('_', ' ').title()}")
            for cat, val in grouped[metric].items():
                print(f"{cat.replace('_', ' ').title()}: {val:.2f}%")

    print(f"\nDetailed results saved to {out_path}")

if __name__ == "__main__":
    main()
