from typing import Dict, List, Set
from dataclasses import dataclass, field

ALL_PERMISSIONS = [
    "github.read",
    "github.write",
    "filesystem.read",
    "filesystem.write",
    "terminal.execute",
    "browser.read",
    "communication.draft",
    "communication.send",
]

DANGEROUS_PERMISSIONS = {"filesystem.write", "communication.send", "github.write"}
DEFAULT_GRANTED = {"github.read", "filesystem.read", "browser.read"}

@dataclass
class PermissionGrant:
    permission: str
    granted_at: str
    granted_by: str = "user"
    automation_id: str = ""

class PermissionRegistry:
    def __init__(self):
        self._granted: Set[str] = set(DEFAULT_GRANTED)
        self._history: List[PermissionGrant] = []

    def is_granted(self, permission: str) -> bool:
        return permission in self._granted

    def are_all_granted(self, permissions: List[str]) -> bool:
        return all(self.is_granted(p) for p in permissions)

    def missing_permissions(self, permissions: List[str]) -> List[str]:
        return [p for p in permissions if not self.is_granted(p)]

    def grant(self, permission: str, automation_id: str = ""):
        if permission not in ALL_PERMISSIONS:
            raise ValueError(f"Unknown permission: {permission}")
        self._granted.add(permission)
        from datetime import datetime
        self._history.append(PermissionGrant(
            permission=permission,
            granted_at=datetime.utcnow().isoformat(),
            automation_id=automation_id,
        ))

    def revoke(self, permission: str):
        self._granted.discard(permission)

    def is_dangerous(self, permission: str) -> bool:
        return permission in DANGEROUS_PERMISSIONS

    def get_granted(self) -> List[str]:
        return sorted(self._granted)

    def get_history(self) -> List[Dict]:
        return [
            {
                "permission": g.permission,
                "granted_at": g.granted_at,
                "granted_by": g.granted_by,
                "automation_id": g.automation_id,
            }
            for g in self._history
        ]

    def get_all_permissions(self) -> List[Dict]:
        return [
            {
                "permission": p,
                "granted": self.is_granted(p),
                "dangerous": self.is_dangerous(p),
            }
            for p in ALL_PERMISSIONS
        ]

_permission_registry: PermissionRegistry = PermissionRegistry()

def get_permission_registry() -> PermissionRegistry:
    return _permission_registry
