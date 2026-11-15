"""The signed-in person's in-app notifications."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbDep
from app.schemas.engagement import NotificationRead, UnreadCount
from app.schemas.pagination import Page, PageParams, page_params
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])
_ERRORS = {401: {"description": "Not signed in"}}


@router.get(
    "",
    response_model=Page[NotificationRead],
    summary="Your notifications, newest first",
    responses=_ERRORS,
)
def list_notifications(
    user: CurrentUser,
    db: DbDep,
    page: Annotated[PageParams, Depends(page_params)],
    unread_only: Annotated[bool, Query()] = False,
) -> Page[NotificationRead]:
    items, total = NotificationService(db).list(
        user, unread_only=unread_only, offset=page.offset, limit=page.page_size
    )
    return Page(
        items=[NotificationRead.model_validate(n) for n in items],
        page=page.page,
        page_size=page.page_size,
        total=total,
    )


@router.get(
    "/unread-count", response_model=UnreadCount, summary="How many are unread", responses=_ERRORS
)
def unread_count(user: CurrentUser, db: DbDep) -> UnreadCount:
    return UnreadCount(unread=NotificationService(db).unread_count(user))


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark one notification as read",
    responses={404: {"description": "Not found"}, **_ERRORS},
)
def mark_read(notification_id: uuid.UUID, user: CurrentUser, db: DbDep) -> NotificationRead:
    return NotificationRead.model_validate(NotificationService(db).mark_read(user, notification_id))


@router.post("/read-all", response_model=UnreadCount, summary="Mark all as read", responses=_ERRORS)
def mark_all_read(user: CurrentUser, db: DbDep) -> UnreadCount:
    NotificationService(db).mark_all_read(user)
    return UnreadCount(unread=0)
