from pathlib import Path

from src.application.container import get_ingest_pdfs_use_case


def main() -> None:
    raw_dir = Path("data/raw_pdfs")
    pdfs = list(raw_dir.glob("*.pdf"))
    use_case = get_ingest_pdfs_use_case()
    use_case.execute(pdfs)


if __name__ == "__main__":
    main()