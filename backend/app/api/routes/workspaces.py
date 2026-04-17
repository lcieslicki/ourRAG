from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.domain.models import Workspace
from app.domain.models.workspace import WorkspaceMembership

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceSummary(BaseModel):
    id: str
    name: str
    role: str


@router.get("", response_model=list[WorkspaceSummary])
def list_workspaces(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[WorkspaceSummary]:
    rows = db.execute(
        select(Workspace, WorkspaceMembership)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == current_user.id)
        .where(Workspace.status == "active")
        .order_by(Workspace.name)
    ).all()
    return [WorkspaceSummary(id=w.id, name=w.name, role=m.role) for w, m in rows]
