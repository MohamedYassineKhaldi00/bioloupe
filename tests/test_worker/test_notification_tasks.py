import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worker.tasks.notification_tasks import send_email_notification, send_in_app_notification


@pytest.mark.asyncio
async def test_send_email_notification():
    ns = MagicMock()
    ns.send_email = AsyncMock(return_value=True)

    res = await send_email_notification(ns, "user@example.com", "subj", "body", None)
    assert res["status"] == "sent"


@pytest.mark.asyncio
async def test_send_in_app_notification():
    ns = MagicMock()
    ns.create_in_app_notification = AsyncMock(return_value=True)

    res = await send_in_app_notification(ns, "user-id", "Title", "Message")
    assert res["status"] == "created"
