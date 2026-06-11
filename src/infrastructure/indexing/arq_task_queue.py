from arq import create_pool
from arq.connections import RedisSettings
from src.application.ports.task_queue_port import TaskQueuePort
from src.infrastructure.config.settings import get_settings

class ArqTaskQueueAdapter(TaskQueuePort):
    def __init__(self):
        self.settings = get_settings()
        self._pool = None

    async def _get_pool(self):
        if not self._pool:
            self._pool = await create_pool(RedisSettings.from_dsn(self.settings.redis_url))
        return self._pool

    async def enqueue_job(self, function_name: str, *args, **kwargs):
        pool = await self._get_pool()
        return await pool.enqueue_job(function_name, *args, **kwargs)
