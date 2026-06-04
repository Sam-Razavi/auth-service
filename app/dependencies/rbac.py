from fastapi import HTTPException, status

# Phase 3 — role-based access control


def require_role(*roles: str):
    def checker():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="RBAC not implemented — Phase 3",
        )
    return checker
