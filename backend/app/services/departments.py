"""Council departments."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.departments import Department
from app.permissions.council_access import CouncilAccess
from app.permissions.rbac import Permission
from app.repositories.operations import DepartmentRepository
from app.schemas.operations import CreateDepartmentRequest, UpdateDepartmentRequest
from app.services.audit import record_audit


class DepartmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DepartmentRepository(db)

    def list(self, access: CouncilAccess) -> list[Department]:
        access.require(Permission.ISSUES_VIEW)
        return self.repo.list(access.council.id)

    def create(self, access: CouncilAccess, request: CreateDepartmentRequest) -> Department:
        access.require(Permission.DEPARTMENTS_MANAGE)
        if self.repo.name_taken(access.council.id, request.name):
            raise ConflictError("This council already has a department with that name.")
        department = Department(
            council_id=access.council.id, name=request.name, description=request.description
        )
        try:
            self.repo.add(department)
            self._audit(access, "department.created", department, {"name": request.name})
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("This council already has a department with that name.") from exc
        return department

    def update(
        self, access: CouncilAccess, department_id: uuid.UUID, request: UpdateDepartmentRequest
    ) -> Department:
        access.require(Permission.DEPARTMENTS_MANAGE)
        department = self.repo.get(access.council.id, department_id)
        if department is None:
            raise NotFoundError("Department not found.")
        changes = request.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is None:
            changes.pop("name")
        if changes.get("name") and self.repo.name_taken(
            access.council.id, changes["name"], exclude_id=department.id
        ):
            raise ConflictError("This council already has a department with that name.")
        for field, value in changes.items():
            setattr(department, field, value)
        self._audit(access, "department.updated", department, {"changes": changes})
        self.db.commit()
        return department

    def _audit(
        self, access: CouncilAccess, action: str, department: Department, details: dict
    ) -> None:
        record_audit(
            self.db,
            action=action,
            actor_user_id=access.user.id,
            council_id=access.council.id,
            target_type="department",
            target_id=department.id,
            details=details,
        )
