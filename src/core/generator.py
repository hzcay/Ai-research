from typing import List
import os
from groq import Groq
from dotenv import load_dotenv

from retriever import retrieve 

load_dotenv()

MODEL_NAME = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_INSTRUCTION = """You are an Expert Academic Research Assistant. 
Your task is to answer questions strictly based on the provided Context.

CONSTRAINTS:
1. Groundedness: If the answer is not in the Context, say: "I do not have enough information based on the provided papers."
2. Citations: Cite paper titles or authors if available in the Context.
3. Tone: Formal, objective, and academic.
4. Structure: Use bullet points for clarity."""

def retrieve_context(query: str, top_k: int = 5) -> str:
    """Retrieve and format context from Qdrant."""
    contexts = retrieve(query, top_k)
    lines: List[str] = []
    
    for i, c in enumerate(contexts, 1):
        payload = c.payload if hasattr(c, 'payload') else c.get("payload", {})
        text = payload.get("text") or payload.get("content") or "No content"
        source = payload.get("metadata", {}).get("source", "Unknown Source")
        
        lines.append(f"--- Document {i} (Source: {source}) ---\n{text}\n")
    
    return "\n".join(lines)

def generate_answer(query: str, top_k: int = 5) -> str:
    """Generate an answer using the LLM with separated System Instruction."""
    context = retrieve_context(query, top_k)
    
    user_prompt = f"""# CONTEXT
                    {context}
                    # USER QUESTION
                    {query}
                    # RESPONSE:"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
    )   
    return response.choices[0].message.content

if __name__ == "__main__":
    query = "What is Hunyuan3D?"
    print(f"--- Querying: {query} ---")
    answer = generate_answer(query)
    print("\nAnswer:")
    print(answer)