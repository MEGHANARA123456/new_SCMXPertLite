from fastapi import HTTPException

def require_role(user, allowed_roles: list):
    role = user.get("role")
    if role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Required role(s): {allowed_roles}"
        )
