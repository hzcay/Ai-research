from pathlib import Path
from typing import Dict, Any
from src.application.ports.parse_port import ParsePort
from src.infrastructure.parsing.docling_parser import parse_research_paper

class DoclingParseAdapter(ParsePort):
    def parse_document(self, file_path: Path) -> Dict[str, Any]:
        """Wrapper around docling parser to fulfill ParsePort interface."""
        return parse_research_paper(file_path)
