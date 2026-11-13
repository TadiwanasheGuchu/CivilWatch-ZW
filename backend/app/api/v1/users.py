"""The signed-in user's own account."""

from fastapi import APIRouter, Response, status

from app.api.deps import AuthServiceDep, CurrentSession, CurrentUser
from app.schemas.auth import ChangePasswordRequest
from app.schemas.users import UpdateProfileRequest, UserRead

router = APIRouter(prefix="/users", tags=["users"])

_ERRORS = {
    401: {"description": "Not signed in or session expired"},
    403: {"description": "CSRF token missing or invalid"},
}


@router.get("/me", response_model=UserRead, summary="Your profile", responses=_ERRORS)
def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead, summary="Update your profile", responses=_ERRORS)
def update_me(
    payload: UpdateProfileRequest, user: CurrentUser, service: AuthServiceDep
) -> UserRead:
    return UserRead.model_validate(service.update_profile(user, full_name=payload.full_name))


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change your password and sign out other sessions",
    responses={
        400: {"description": "Current password incorrect"},
        429: {"description": "Too many attempts"},
        **_ERRORS,
    },
)
def change_password(
    payload: ChangePasswordRequest, session: CurrentSession, service: AuthServiceDep
) -> Response:
    service.change_password(
        session,
        current_password=payload.current_password.get_secret_value(),
        new_password=payload.new_password.get_secret_value(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
