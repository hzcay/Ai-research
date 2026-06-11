from typing import Protocol, Any, Dict
from pathlib import Path

class ParsePort(Protocol):
    def parse_document(self, file_path: Path) -> Dict[str, Any]:
        ...
