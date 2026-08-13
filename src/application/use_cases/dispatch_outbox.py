from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from src.infrastructure.database.models import OutboxEvent


class OutboxDispatcher:
    def __init__(self, session_factory, queue) -> None:
        self._sessions = session_factory
        self._queue = queue

    async def dispatch_pending(self, limit: int = 50) -> int:
        published = 0
        async with self._sessions() as session:
            events = (await session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at)
                .with_for_update(skip_locked=True)
                .limit(limit)
            )).all()
            for event in events:
                try:
                    await self._queue.enqueue_job(
                        "handle_domain_event",
                        event.id,
                        _job_id=f"outbox:{event.id}",
                    )
                    event.status = "delivered"
                    event.delivered_at = datetime.utcnow()
                    published += 1
                except Exception as exc:
                    event.status = "pending"
                    event.payload = {**(event.payload or {}), "last_error": str(exc)[:500]}
            await session.commit()
        return published
