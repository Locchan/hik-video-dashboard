"""Config ACL helpers based on api_user.group vs config.group_read / group_write."""

from __future__ import annotations

from purest.auth.policy import PUR_CAP_ADMIN, ROOT_CAPABILITY


def is_privileged(auth_backend, username: str) -> bool:
    """Root / ALL can see and change every config entry."""
    return auth_backend.check_capability(username, ROOT_CAPABILITY)


def is_admin(auth_backend, username: str) -> bool:
    """PUR_CAP_ADMIN (root/ALL bypass check_capability)."""
    return auth_backend.check_capability(username, PUR_CAP_ADMIN)


def can_read(auth_backend, username: str, entry: dict) -> bool:
    if is_privileged(auth_backend, username):
        return True
    group_id = auth_backend.get_user_group_id(username)
    if group_id is None:
        return False
    return entry["group_read"] == group_id


def can_write(auth_backend, username: str, entry: dict) -> bool:
    if is_privileged(auth_backend, username):
        return True
    group_id = auth_backend.get_user_group_id(username)
    if group_id is None:
        return False
    return entry["group_write"] == group_id
