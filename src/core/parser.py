from pathlib import Path
from typing import Any, Dict, List
import fitz

def parse_research_paper(path: str | Path) -> Dict[str, Any]:
    pdf_path = Path(path)
    with fitz.open(pdf_path) as doc:
        paper_data: Dict[str, Any] = {
            "metadata": {
                "title": (doc.metadata or {}).get("title", "") if hasattr(doc, "metadata") else "",
                "author": (doc.metadata or {}).get("author", "") if hasattr(doc, "metadata") else "",
                "subject": (doc.metadata or {}).get("subject", "") if hasattr(doc, "metadata") else "",
                "date": (doc.metadata or {}).get("date", "") if hasattr(doc, "metadata") else "",
            },
            "total_pages": doc.page_count,
            "content": [],
        }

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_dict = page.get_text("dict")

            page_text_parts: List[str] = []
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text")
                        if text:
                            page_text_parts.append(text)

            paper_data["content"].append(
                {
                    "page": page_num + 1,
                    "text": " ".join(page_text_parts).strip(),
                }
            )

        return paper_data


if __name__ == "__main__":
    data = parse_research_paper("D:/project/Ai-research/data/raw_pdfs/2501.12202v3.pdf")
    print(f"Parsed {data['total_pages']} pages from: {data['metadata'].get('title', '')}")
    print(data["metadata"])