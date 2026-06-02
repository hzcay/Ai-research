import json
from pathlib import Path
from datasets import Dataset
import asyncio
import time
from typing import List, Optional, Any

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.outputs import ChatResult
from langchain_core.messages import BaseMessage
from langchain_community.embeddings import HuggingFaceEmbeddings

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.run_config import RunConfig

from src.infrastructure.config.settings import get_settings
import asyncio
from functools import partial

import threading

_gemini_rate_limit_lock = threading.Lock()
_gemini_last_call = 0.0

class RateLimitedGemini(ChatGoogleGenerativeAI):
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        global _gemini_last_call
        with _gemini_rate_limit_lock:
            now = time.time()
            elapsed = now - _gemini_last_call
            if elapsed < 10.0:
                time.sleep(10.0 - elapsed)
            _gemini_last_call = time.time()
            
        print(f"[Judge API] Gửi 1 request đến Google API... ({len(str(messages))} chars)")
        return super()._generate(messages, stop, run_manager, **kwargs)

    async def _agenerate(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ChatResult:
       
        loop = asyncio.get_running_loop()
        func = partial(self._generate, *args, **kwargs)
        return await loop.run_in_executor(None, func)

_groq_rate_limit_lock = threading.Lock()
_groq_last_call = 0.0

class RateLimitedGroq(ChatGroq):
    """Wrapper sử dụng Threading Lock để ép các request Groq xếp hàng, tránh lỗi Rate Limit của Groq Free Tier (30 RPM)"""
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        global _groq_last_call
        with _groq_rate_limit_lock:
            now = time.time()
            elapsed = now - _groq_last_call
            if elapsed < 2.5: # 2.5s = 24 RPM (an toàn cho giới hạn 30 RPM của Groq)
                time.sleep(2.5 - elapsed)
            _groq_last_call = time.time()
            
        print(f"[Judge API - GROQ] Gửi 1 request đến Groq API... ({len(str(messages))} chars)")
        return super()._generate(messages, stop, run_manager, **kwargs)

    async def _agenerate(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ChatResult:
        loop = asyncio.get_running_loop()
        func = partial(self._generate, *args, **kwargs)
        return await loop.run_in_executor(None, func)

def load_data(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def main():
    settings = get_settings()
    
    if settings.llm_provider.lower() == "gemini":
        judge_llm = RateLimitedGemini(
            model=settings.gemini_judge_model,
            google_api_key=settings.gemini_api_key,
            max_retries=0,
            timeout=30.0
        )
    else:
        judge_llm = RateLimitedGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            max_retries=0, # Tắt retry ngầm
            timeout=30.0
        )
    
    print("Loading judge embedding model...")
    judge_embeddings = HuggingFaceEmbeddings(model_name=settings.embed_model_name)
    
    dataset_path = Path("data/eval/ragas_generated.json")
    if not dataset_path.exists():
        print(f"Error: Could not find generated responses at {dataset_path}.")
        print("Please run scripts/01_generate_responses.py first!")
        return
        
    ragas_data = load_data(dataset_path)
    dataset = Dataset.from_dict(ragas_data)
    
    run_config = RunConfig(timeout=600, max_retries=10, max_wait=60, max_workers=1)

    print("\nRunning Ragas evaluation with Judge...")
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
