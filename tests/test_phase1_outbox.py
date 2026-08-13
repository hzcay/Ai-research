from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.dispatch_outbox import OutboxDispatcher


@pytest.mark.asyncio
async def test_outbox_dispatches_through_registered_domain_event_handler() -> None:
    event = MagicMock()
    event.id = "event-1"
    event.status = "pending"
    event.payload = {}
    session = AsyncMock()
    scalars = MagicMock()
    scalars.all.return_value = [event]
    session.scalars.return_value = scalars
    context = AsyncMock()
    context.__aenter__.return_value = session
    session_factory = MagicMock(return_value=context)
    queue = MagicMock()
    queue.enqueue_job = AsyncMock(return_value="job-1")

    count = await OutboxDispatcher(session_factory, queue).dispatch_pending()

    assert count == 1
    queue.enqueue_job.assert_awaited_once_with(
        "handle_domain_event", "event-1", _job_id="outbox:event-1"
    )
    assert event.status == "delivered"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_outbox_failure_leaves_event_pending() -> None:
    event = MagicMock(id="event-2", status="pending", payload={})
    session = AsyncMock()
    scalars = MagicMock()
    scalars.all.return_value = [event]
    session.scalars.return_value = scalars
    context = AsyncMock()
    context.__aenter__.return_value = session
    session_factory = MagicMock(return_value=context)
    queue = MagicMock()
    queue.enqueue_job = AsyncMock(side_effect=RuntimeError("redis unavailable"))

    count = await OutboxDispatcher(session_factory, queue).dispatch_pending()

    assert count == 0
    assert event.status == "pending"
    assert event.payload["last_error"] == "redis unavailable"
    session.commit.assert_awaited_once()
