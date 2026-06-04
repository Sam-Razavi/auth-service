from pydantic import BaseModel


class RoleOut(BaseModel):
    name: str

    model_config = {"from_attributes": True}


class AssignRolesRequest(BaseModel):
    roles: list[str]  # e.g. ["admin", "moderator"]
