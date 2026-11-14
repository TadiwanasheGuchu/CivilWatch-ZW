"""Build report responses, attaching freshly signed photo URLs.

Photo URLs are generated only for reports the caller is already allowed to
see, so a signed URL is never handed to someone without access.
"""

from app.core.storage import ObjectStorage
from app.models.issues import Issue, IssueMedia, IssueStatusHistory
from app.schemas.issues import (
    OwnIssue,
    OwnIssueDetail,
    OwnStatusChange,
    PhotoRead,
    PublicIssue,
    PublicIssueDetail,
    StatusChange,
)


class IssuePresenter:
    def __init__(self, storage: ObjectStorage, ttl_seconds: int) -> None:
        self.storage = storage
        self.ttl = ttl_seconds

    def photo(self, media: IssueMedia) -> PhotoRead:
        return PhotoRead(
            id=media.id,
            url=self.storage.signed_url(media.display_key, self.ttl),
            thumbnail_url=self.storage.signed_url(media.thumbnail_key, self.ttl),
            width=media.width,
            height=media.height,
        )

    def _summary_fields(self, issue: Issue) -> dict:
        photos = issue.report_photos
        return {
            "photo_count": len(photos),
            "cover_thumbnail_url": (
                self.storage.signed_url(photos[0].thumbnail_key, self.ttl) if photos else None
            ),
        }

    def own(self, issue: Issue) -> OwnIssue:
        return OwnIssue.model_validate(issue).model_copy(update=self._summary_fields(issue))

    def public(self, issue: Issue) -> PublicIssue:
        return PublicIssue.model_validate(issue).model_copy(update=self._summary_fields(issue))

    def own_detail(self, issue: Issue, history: list[IssueStatusHistory]) -> OwnIssueDetail:
        return OwnIssueDetail(
            **self.own(issue).model_dump(),
            history=[OwnStatusChange.model_validate(h) for h in history],
            photos=[self.photo(m) for m in issue.report_photos],
            repair_photos=[self.photo(m) for m in issue.repair_photos],
        )

    def public_detail(self, issue: Issue, history: list[IssueStatusHistory]) -> PublicIssueDetail:
        return PublicIssueDetail(
            **self.public(issue).model_dump(),
            history=[StatusChange.model_validate(h) for h in history],
            photos=[self.photo(m) for m in issue.report_photos],
            repair_photos=[self.photo(m) for m in issue.repair_photos],
        )
