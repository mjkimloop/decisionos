from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List

from packages.common.config import settings

# Dummy user database
DUMMY_USERS = {
    "user@example.com": {"roles": ["user"]},
    "admin@example.com": {"roles": ["user", "admin"]},
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    if not settings.auth_enabled:
        return {"email": "anonymous", "roles": []}

    # In a real app, you'd decode the token and get the user
    # For this dummy implementation, the token is the user's email
    user = DUMMY_USERS.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"email": token, **user}


class RBAC:
    def __init__(self, required_roles: List[str]):
        self.required_roles = required_roles

    def __call__(self, user: dict = Depends(get_current_user)):
        for role in self.required_roles:
            if role not in user["roles"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required role: {role}",
                )
