import json
import time
from pathlib import Path
from tqdm import tqdm

from src.application.container import get_generate_answer_use_case
from src.infrastructure.config.settings import get_settings

def load_data(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def main():
    settings = get_settings()
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
    for gt in tqdm(ground_truths, desc="Generating Answers"):
        q = gt["user_input"]
        ref = gt["reference"]
    
        result = use_case.execute(query=q, top_k=2) 
        
        ragas_data["user_input"].append(q)
        ragas_data["response"].append(result["answer"])
        ragas_data["retrieved_contexts"].append([c["text"] for c in result["citations"]])
        ragas_data["reference"].append(ref)
        ragas_data["category"].append(gt.get("category", "unknown"))
        
        # Sleep for 8 seconds to respect Gemini Free Tier 15 RPM limit
        time.sleep(8)
        
    out_path = Path("data/eval/ragas_generated.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w") as f:
        json.dump(ragas_data, f, indent=2)
        
    print(f"\nGenerated {len(ground_truths)} responses. Saved to {out_path}.")
    print("Next step: Run 02_evaluate_responses.py to evaluate these responses.")

if __name__ == "__main__":
    main()
