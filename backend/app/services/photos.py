"""Adding photographs to reports."""

import logging
import uuid

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, PermissionDeniedError
from app.core.rate_limit import RateLimiter
from app.core.storage import ObjectStorage
from app.models.identity import User
from app.models.issues import IssueMedia, IssueStatus, MediaKind
from app.permissions.council_access import CouncilAccess
from app.repositories.issues import IssueRepository
from app.repositories.operations import OperationsRepository
from app.services.images import process_photo
from app.services.workflow import REPAIR_STATUSES, can_add_repair_photos

logger = logging.getLogger(__name__)


# Reporters may change photos before review, and while the council has asked
# them for more information.
OPEN_FOR_REPORTER = frozenset({IssueStatus.SUBMITTED, IssueStatus.NEEDS_INFORMATION})


class PhotoTooLargeError(AppError):
    status_code = 413
    code = "photo_too_large"


class ReportLockedError(AppError):
    status_code = 409
    code = "report_locked"


class PhotoLimitError(AppError):
    status_code = 409
    code = "photo_limit_reached"


class PhotoService:
    def __init__(
        self, db: Session, settings: Settings, storage: ObjectStorage, limiter: RateLimiter
    ) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage
        self.limiter = limiter
        self.issues = IssueRepository(db)

    def add_photo(self, reporter: User, issue_id: uuid.UUID, data: bytes) -> IssueMedia:
        self._rate_limit_and_size(reporter.id, data)
        issue = self.issues.get(issue_id)
        # Only the reporter may add photos; anyone else learns nothing.
        if issue is None or issue.reporter_id != reporter.id:
            raise NotFoundError("Report not found.")
        if issue.status not in OPEN_FOR_REPORTER:
            raise ReportLockedError(
                "Photos can only be added before review or when the council asks for information."
            )
        return self._store(issue_id, data, reporter.id, MediaKind.REPORT)

    def add_repair_photo(
        self, access: CouncilAccess, issue_id: uuid.UUID, data: bytes
    ) -> IssueMedia:
        """Repair evidence from the staff doing the work (assignee, their manager, or an admin)."""
        self._rate_limit_and_size(access.user.id, data)
        issue = OperationsRepository(self.db).get_issue(access.council.id, issue_id)
        if issue is None:
            raise NotFoundError("Report not found.")
        if not can_add_repair_photos(self.db, access, issue):
            if issue.status not in REPAIR_STATUSES:
                raise ReportLockedError("Repair photos can be added while work is in progress.")
            raise PermissionDeniedError("Only the staff doing this work can add repair photos.")
        return self._store(issue_id, data, access.user.id, MediaKind.REPAIR)

    def remove_photo(self, reporter: User, issue_id: uuid.UUID, photo_id: uuid.UUID) -> None:
        """Remove a photo added by mistake, before the council has started on the report."""
        issue = self.issues.get(issue_id)
        if issue is None or issue.reporter_id != reporter.id:
            raise NotFoundError("Report not found.")
        media = self.db.scalar(
            select(IssueMedia).where(
                IssueMedia.id == photo_id,
                IssueMedia.issue_id == issue_id,
                # Reporters can never remove the council's repair evidence.
                IssueMedia.kind == MediaKind.REPORT,
            )
        )
        if media is None:
            raise NotFoundError("Photo not found.")
        if issue.status not in OPEN_FOR_REPORTER:
            raise ReportLockedError(
                "Photos can only be removed before review or when the council asks for information."
            )
        keys = (media.display_key, media.thumbnail_key)
        self.db.delete(media)
        self.db.commit()
        # Delete the objects only once the row is gone, so no row points at
        # a missing object. A failed object delete leaves a harmless private orphan.
        for key in keys:
            self.storage.delete(key)
        logger.info("photo removed", extra={"issue_id": str(issue_id), "media_id": str(photo_id)})

    def _rate_limit_and_size(self, user_id: uuid.UUID, data: bytes) -> None:
        self.limiter.hit(
            "photo:user",
            str(user_id),
            limit=self.settings.photo_uploads_per_user,
            window_seconds=self.settings.photo_upload_window_seconds,
        )
        if len(data) > self.settings.photo_max_upload_bytes:
            raise self.too_large()

    def _store(
        self, issue_id: uuid.UUID, data: bytes, uploader_id: uuid.UUID, kind: MediaKind
    ) -> IssueMedia:
        self._ensure_room(issue_id, kind)
        processed = process_photo(data, self.settings)
        media_id = uuid.uuid4()
        prefix = f"issues/{issue_id}/{media_id}"
        display_key, thumbnail_key = f"{prefix}/display.jpg", f"{prefix}/thumbnail.jpg"
        self.storage.put(display_key, processed.display, "image/jpeg")
        try:
            self.storage.put(thumbnail_key, processed.thumbnail, "image/jpeg")
            media = IssueMedia(
                id=media_id,
                issue_id=issue_id,
                uploaded_by_user_id=uploader_id,
                display_key=display_key,
                thumbnail_key=thumbnail_key,
                content_type="image/jpeg",
                kind=kind,
                width=processed.width,
                height=processed.height,
                byte_size=len(processed.display),
            )
            self.db.add(media)
            self.db.commit()
        except Exception:
            self.db.rollback()
            # Don't leave unreferenced objects behind.
            self.storage.delete(display_key)
            self.storage.delete(thumbnail_key)
            raise
        logger.info(
            "photo added",
            extra={"issue_id": str(issue_id), "media_id": str(media_id), "kind": kind.value},
        )
        return media

    def _ensure_room(self, issue_id: uuid.UUID, kind: MediaKind) -> None:
        # Serialise uploads to the same report for the rest of this transaction,
        # so two simultaneous uploads cannot both pass the limit. (Row locks
        # would need UPDATE privilege, which the API role does not have.)
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"issue-photos:{issue_id}"},
        )
        count = self.db.scalar(
            select(func.count())
            .select_from(IssueMedia)
            .where(IssueMedia.issue_id == issue_id, IssueMedia.kind == kind)
        )
        if (count or 0) >= self.settings.photos_per_issue:
            what = "repair photos" if kind == MediaKind.REPAIR else "photos"
            raise PhotoLimitError(
                f"A report can have at most {self.settings.photos_per_issue} {what}."
            )

    def too_large(self) -> PhotoTooLargeError:
        megabytes = self.settings.photo_max_upload_bytes // (1024 * 1024)
        return PhotoTooLargeError(f"Photos must be smaller than {megabytes} MB.")
