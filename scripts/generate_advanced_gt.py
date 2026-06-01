import os
import sys
import json
import asyncio
import time
import random
from collections import defaultdict
import nest_asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple

nest_asyncio.apply()
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.infrastructure.database.models import Chunk

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class QAPair(BaseModel):
    user_input: str = Field(description="The generated question based on the text.")
    reference: str = Field(description="The expected correct answer based strictly on the text.")

class ReasoningValidation(BaseModel):
    is_reasoning: bool = Field(description="True if the question genuinely requires logical reasoning (Why/How) beyond simple extraction.")
    is_answer_in_context: bool = Field(description="True if the provided answer can be fully deduced from the context alone.")

class AdvancedGTGenerator:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatGroq(
            api_key=self.settings.groq_api_key,
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            max_retries=5,
            temperature=0.1
        )
        self.parser = JsonOutputParser(pydantic_object=QAPair)
        self.val_parser = JsonOutputParser(pydantic_object=ReasoningValidation)
        self.results = []
        self.chunks: List[Chunk] = []
        self.chunks_by_doc = defaultdict(list)
        
    async def load_chunks(self):
        repo = PostgresRepository()
        async with repo.async_session() as session:
            stmt = select(Chunk).order_by(Chunk.doc_id, Chunk.page_start)
            result = await session.execute(stmt)
            self.chunks = result.scalars().all()
            for c in self.chunks:
                self.chunks_by_doc[c.doc_id].append(c)
        print(f"Loaded {len(self.chunks)} chunks across {len(self.chunks_by_doc)} documents.")

    def _call_llm(self, prompt_sys: str, context: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_sys + "\n\n{format_instructions}"),
            ("user", "CONTEXT:\n{context}")
        ])
        chain = prompt | self.llm | self.parser
        
        # Implement 3.5s rate limit delay
        time.sleep(3.5)
        
        res = chain.invoke({
            "context": context,
            "format_instructions": self.parser.get_format_instructions()
        })
        return res

    def generate_single_chunk(self, count=15):
        print(f"Generating {count} Single Chunk (Easy) questions...")
        sys_prompt = "You are an expert academic evaluator. Create 1 easy question that can be directly answered using ONLY the provided text segment. Ensure the question is specific."
        
        valid_chunks = [c for c in self.chunks if len(c.text_content) > 300]
        selected = random.sample(valid_chunks, min(count, len(valid_chunks)))
        
        for i, c in enumerate(selected, 1):
            try:
                res = self._call_llm(sys_prompt, c.text_content)
                self.results.append({
                    "id": f"single_{i}",
                    "user_input": res["user_input"],
                    "reference": res["reference"],
                    "category": "single_chunk",
                    "difficulty": "easy",
                    "expected_chunk_ids": [c.chunk_id],
                    "expected_contexts": [c.text_content]
                })
                print(f"  [Single] Q: {res['user_input']}")
            except Exception as e:
                print(f"  [Error Single] {e}")

    def generate_table_lookup(self, count=10):
        print(f"Generating {count} Table Lookup (Medium) questions...")
        sys_prompt = "You are an expert academic evaluator. Create 1 medium-difficulty question that requires the user to look up specific numbers or data points from the provided table/matrix."
        
        # Heuristics for tables
        table_keywords = ["|---|", "Table", "GQA", "MMB", "Avg.", "POPE", "OCRBench"]
        valid_chunks = [c for c in self.chunks if any(k in c.text_content for k in table_keywords)]
        selected = random.sample(valid_chunks, min(count, len(valid_chunks)))
        
        for i, c in enumerate(selected, 1):
            try:
                res = self._call_llm(sys_prompt, c.text_content)
                self.results.append({
                    "id": f"table_{i}",
                    "user_input": res["user_input"],
                    "reference": res["reference"],
                    "category": "table_lookup",
                    "difficulty": "medium",
                    "expected_chunk_ids": [c.chunk_id],
                    "expected_contexts": [c.text_content]
                })
                print(f"  [Table] Q: {res['user_input']}")
            except Exception as e:
                print(f"  [Error Table] {e}")

    def generate_multi_chunk(self, count=10):
        print(f"Generating {count} Multi-Chunk (Medium) questions...")
        sys_prompt = "You are an expert academic evaluator. Create 1 question that STRICTLY requires combining information from ALL the provided text segments. A single segment should not be enough to answer it fully."
        
        candidates = []
        for doc_id, c_list in self.chunks_by_doc.items():
            for i in range(len(c_list) - 1):
                if len(c_list[i].text_content) > 200 and len(c_list[i+1].text_content) > 200:
                    candidates.append([c_list[i], c_list[i+1]])
        
        selected = random.sample(candidates, min(count, len(candidates)))
        
        for i, pair in enumerate(selected, 1):
            try:
                context = f"--- SEGMENT 1 ---\n{pair[0].text_content}\n\n--- SEGMENT 2 ---\n{pair[1].text_content}"
                res = self._call_llm(sys_prompt, context)
                self.results.append({
                    "id": f"multi_{i}",
                    "user_input": res["user_input"],
                    "reference": res["reference"],
                    "category": "multi_chunk",
                    "difficulty": "medium",
                    "expected_chunk_ids": [c.chunk_id for c in pair],
                    "expected_contexts": [c.text_content for c in pair]
                })
                print(f"  [Multi] Q: {res['user_input']}")
            except Exception as e:
                print(f"  [Error Multi] {e}")

    def generate_comparative(self, count=8):
        print(f"Generating {count} Comparative (Hard) questions...")
        sys_prompt = "You are an expert academic evaluator. Create 1 question that asks to COMPARE (differences, advantages, disadvantages) the concepts discussed in the two segments."
        
        # Keyword overlap strategy
        candidates = []
        for doc_id, c_list in self.chunks_by_doc.items():
            valid = [c for c in c_list if len(c.text_content) > 200]
            for i in range(len(valid)):
                for j in range(i+1, len(valid)):
                    words_i = set(valid[i].text_content.lower().split())
                    words_j = set(valid[j].text_content.lower().split())
                    # Check overlap of words longer than 5 chars (filtering common words)
                    overlap = {w for w in words_i.intersection(words_j) if len(w) > 6}
                    if len(overlap) > 5:
                        candidates.append([valid[i], valid[j]])
                        
        selected = random.sample(candidates, min(count, len(candidates))) if candidates else []
        
        for i, pair in enumerate(selected, 1):
            try:
                context = f"--- SEGMENT 1 ---\n{pair[0].text_content}\n\n--- SEGMENT 2 ---\n{pair[1].text_content}"
                res = self._call_llm(sys_prompt, context)
                self.results.append({
                    "id": f"compare_{i}",
                    "user_input": res["user_input"],
                    "reference": res["reference"],
                    "category": "comparative",
                    "difficulty": "hard",
                    "expected_chunk_ids": [c.chunk_id for c in pair],
                    "expected_contexts": [c.text_content for c in pair]
                })
                print(f"  [Compare] Q: {res['user_input']}")
            except Exception as e:
                print(f"  [Error Compare] {e}")

    def generate_reasoning(self, count=5):
        print(f"Generating {count} Reasoning (Hard) questions...")
        sys_prompt = "You are an expert academic evaluator. Create 1 reasoning question (Why/How) that requires understanding the underlying cause or experimental result, not just copying text."
        
        keywords = ["Result", "Conclusion", "Discussion", "Experiment", "However", "Therefore", "Suggests"]
        valid_chunks = [c for c in self.chunks if any(k in c.text_content for k in keywords) and len(c.text_content) > 300]
        selected = random.sample(valid_chunks, min(count*3, len(valid_chunks))) # Oversample for retries
        
        val_prompt = ChatPromptTemplate.from_messages([
            ("system", "Validate the following Q&A pair based on the context.\n{format_instructions}"),
            ("user", "CONTEXT:\n{context}\n\nQUESTION: {q}\nANSWER: {a}")
        ])
        val_chain = val_prompt | self.llm | self.val_parser
        
        success_count = 0
        for i, c in enumerate(selected, 1):
            if success_count >= count: break
            try:
                # 1. Generate
                res = self._call_llm(sys_prompt, c.text_content)
                
                # 2. Validate
                time.sleep(3.5)
                val = val_chain.invoke({
                    "context": c.text_content,
                    "q": res["user_input"],
                    "a": res["reference"],
                    "format_instructions": self.val_parser.get_format_instructions()
                })
                
                if val["is_reasoning"] and val["is_answer_in_context"]:
                    self.results.append({
                        "id": f"reasoning_{success_count+1}",
                        "user_input": res["user_input"],
                        "reference": res["reference"],
                        "category": "reasoning",
                        "difficulty": "hard",
                        "expected_chunk_ids": [c.chunk_id],
                        "expected_contexts": [c.text_content]
                    })
                    print(f"  [Reasoning] Q: {res['user_input']}")
                    success_count += 1
                else:
                    print(f"  [Reasoning] Validation failed for generated Q: {res['user_input']}")
            except Exception as e:
                print(f"  [Error Reasoning] {e}")

    def generate_multi_hop(self, count=2):
        print(f"Generating {count} Multi-Hop (Very Hard) questions...")
        sys_prompt = "You are an expert academic evaluator. Create 1 macro-level, multi-hop question that requires the reader to synthesize information spanning from the introduction, methodology, experiments, to the conclusion."
        
        candidates = []
        for doc_id, c_list in self.chunks_by_doc.items():
            if len(c_list) > 10:
                # Abstract/Intro (first 10%)
                intro = c_list[:max(1, len(c_list)//10)]
                # Method (middle 30-50%)
                method = c_list[int(len(c_list)*0.3):int(len(c_list)*0.5)]
                # Result (middle 60-80%)
                result = c_list[int(len(c_list)*0.6):int(len(c_list)*0.8)]
                # Conclusion (last 10%)
                concl = c_list[-max(1, len(c_list)//10):]
                
                if intro and method and result and concl:
                    candidates.append([random.choice(intro), random.choice(method), random.choice(result), random.choice(concl)])
                    
        selected = random.sample(candidates, min(count, len(candidates))) if candidates else []
        
        for i, hops in enumerate(selected, 1):
            try:
                context = "\n\n".join([f"--- SEGMENT {idx} ---\n{c.text_content}" for idx, c in enumerate(hops, 1)])
                res = self._call_llm(sys_prompt, context)
                self.results.append({
                    "id": f"multihop_{i}",
                    "user_input": res["user_input"],
                    "reference": res["reference"],
                    "category": "multi_hop",
                    "difficulty": "very_hard",
                    "expected_chunk_ids": [c.chunk_id for c in hops],
                    "expected_contexts": [c.text_content for c in hops]
                })
                print(f"  [MultiHop] Q: {res['user_input']}")
            except Exception as e:
                print(f"  [Error MultiHop] {e}")

    def save(self):
        out_path = Path("data/eval/ragas_ground_truth.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(self.results)} advanced Q&A pairs to {out_path}")

async def main():
    generator = AdvancedGTGenerator()
    await generator.load_chunks()
    
    # Generate structured dataset
    generator.generate_single_chunk(15)
    generator.generate_table_lookup(10)
    generator.generate_multi_chunk(10)
    generator.generate_comparative(8)
    generator.generate_reasoning(5)
    generator.generate_multi_hop(2)
    
    generator.save()

if __name__ == "__main__":
    asyncio.run(main())
