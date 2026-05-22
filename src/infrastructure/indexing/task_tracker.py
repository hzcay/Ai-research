import threading
from typing import Dict, Any, Optional

class TaskTracker:
    """In-memory tracker for document ingestion tasks."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TaskTracker, cls).__new__(cls)
                cls._instance._tasks = {}
        return cls._instance

    def create_task(self, doc_id: str) -> None:
        with self._lock:
            self._tasks[doc_id] = {
                "status": "processing",
                "progress": 0,
                "message": "Initializing processing..."
            }

    def update_task(self, doc_id: str, status: str, progress: int, message: str) -> None:
        with self._lock:
            if doc_id in self._tasks:
                self._tasks[doc_id].update({
                    "status": status,
                    "progress": progress,
                    "message": message
                })
            else:
                self._tasks[doc_id] = {
                    "status": status,
                    "progress": progress,
                    "message": message
                }

    def get_task(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._tasks.get(doc_id)
