from pathlib import Path

from src.core.parser import parse_pdf_batch
from src.core.indexer import index_documents


def main() -> None:
    raw_dir = Path("data/raw_pdfs")
    pdfs = list(raw_dir.glob("*.pdf"))
    docs = parse_pdf_batch(pdfs)
    index_documents(docs)


if __name__ == "__main__":
    main()