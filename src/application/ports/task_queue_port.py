from typing import Protocol, Any

class TaskQueuePort(Protocol):
    async def enqueue_job(self, function_name: str, *args: Any, **kwargs: Any) -> Any:
        ...
