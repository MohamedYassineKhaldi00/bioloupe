from __future__ import annotations

import logging
from app.worker.celery_app import get_task_decorator

logger = logging.getLogger(__name__)
_task = get_task_decorator()


@_task()
async def send_email_notification(notification_service, user_id: str, subject: str, body: str, html: str | None = None):
    try:
        await notification_service.send_email(to=user_id, subject=subject, body=body, html=html)
        return {"status": "sent", "user_id": user_id}
    except Exception as e:
        logger.exception("Failed to send email to %s: %s", user_id, e)
        raise


@_task()
async def send_in_app_notification(notification_service, user_id: str, title: str, message: str, link: str | None = None):
    try:
        await notification_service.create_in_app_notification(user_id=user_id, title=title, message=message, link=link)
        return {"status": "created", "user_id": user_id}
    except Exception as e:
        logger.exception("Failed to create in-app notification for %s: %s", user_id, e)
        raise