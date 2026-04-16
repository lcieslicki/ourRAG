from dataclasses import dataclass

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class CurrentUser:
    id: str


def get_current_user(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> CurrentUser:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthenticated", "message": "Missing X-User-Id header."},
        )

    return CurrentUser(id=x_user_id)
