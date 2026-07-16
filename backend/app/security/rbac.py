from fastapi import Depends, HTTPException, status
from typing import List
from ..db.models import User
from .auth import get_current_user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {self.allowed_roles}. Current role: {current_user.role}"
            )
        return current_user

# Pre-defined clearance levels
allow_all = RoleChecker(["Administrator", "Emergency Coordinator", "Doctor", "Nurse", "Hospital Manager", "Observer"])
allow_clinical = RoleChecker(["Administrator", "Emergency Coordinator", "Doctor", "Nurse"])
allow_coordinator = RoleChecker(["Administrator", "Emergency Coordinator"])
allow_admin = RoleChecker(["Administrator"])
allow_manager = RoleChecker(["Administrator", "Hospital Manager"])
