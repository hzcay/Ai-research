import asyncio
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.application.container import get_ingest_pdfs_use_case


async def amain() -> None:
    raw_dir = Path("data/raw_pdfs")
    pdfs = list(raw_dir.glob("*.pdf"))
    use_case = get_ingest_pdfs_use_case()
    await use_case.execute(pdfs)

def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()